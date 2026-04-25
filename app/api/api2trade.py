"""
API2Trade MT4/MT5 API 客户端
文档: https://www.api2trade.com
Base URL: https://api.metatraderapi.dev
认证: x-api-key header

支持功能:
- 账户摘要 (AccountSummary)
- 实时行情 (REST + WebSocket)
- 历史K线数据
- 持仓查询
"""

import httpx
import json
import asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List


# ============================================
# 配置
# ============================================
from app.config import API2TRADE_BASE_URL, API2TRADE_API_KEY, API2TRADE_CACHE_TTL

_cache: Dict[str, tuple] = {}  # key: cache_key, value: (timestamp, data)


# ============================================
# 缓存工具
# ============================================
def _get_cache(key: str, ttl: int) -> Optional[Any]:
    """读取缓存（未过期返回数据，否则返回 None）"""
    if key in _cache:
        ts, data = _cache[key]
        if datetime.now().timestamp() - ts < ttl:
            return data
    return None


def _set_cache(key: str, data: Any):
    """写入缓存"""
    _cache[key] = (datetime.now().timestamp(), data)


# ============================================
# 基础请求头
# ============================================
def _get_headers() -> dict:
    """生成认证请求头"""
    return {
        "x-api-key": API2TRADE_API_KEY,
        "Content-Type": "application/json",
    }


# ============================================
# 账户信息
# ============================================
async def get_account_summary(account_uuid: str) -> Optional[Dict[str, Any]]:
    """
    获取 MT4/MT5 账户摘要
    account_uuid: 账户 UUID（在 API2Trade 控制台获取）
    返回: {balance, equity, margin, freeMargin, ...}
    """
    cache_key = f"account_{account_uuid}"
    cached = _get_cache(cache_key, ttl=10)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/AccountSummary"
    params = {"id": account_uuid}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[API2Trade] account error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[API2Trade] account exception: {e}")

    return None


async def get_account_info(account_uuid: str) -> Optional[Dict[str, Any]]:
    """
    获取账户信息（兼容 MetaApi 接口格式）
    """
    summary = await get_account_summary(account_uuid)
    if summary:
        return {
            "balance": summary.get("balance", 0),
            "equity": summary.get("equity", 0),
            "margin": summary.get("margin", 0),
            "marginFree": summary.get("freeMargin", 0),
            "profit": summary.get("profit", 0),
            "marginLevel": summary.get("marginLevel", 0),
            "leverage": summary.get("leverage", 1),
            "currency": summary.get("currency", "USD"),
            "server": summary.get("server", ""),
            "login": summary.get("login", ""),
        }
    return None


# ============================================
# 实时行情 (REST)
# ============================================
async def get_symbol_quote(symbol: str, account_uuid: str) -> Optional[Dict[str, Any]]:
    """
    获取单个品种实时报价
    symbol: 品种名，如 "EURUSD", "XAUUSD"
    account_uuid: 账户 UUID
    """
    cache_key = f"quote_{symbol}_{account_uuid}"
    cached = _get_cache(cache_key, ttl=API2TRADE_CACHE_TTL)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/Quote"
    params = {"id": account_uuid, "symbol": symbol}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[API2Trade] quote error for {symbol}: {resp.status_code}")
    except Exception as e:
        print(f"[API2Trade] quote exception for {symbol}: {e}")

    return None


async def get_bulk_quotes(symbols: List[str], account_uuid: str) -> Optional[List[Dict[str, Any]]]:
    """
    批量获取多个品种实时报价
    """
    cache_key = f"bulk_quotes_{'_'.join(symbols)}_{account_uuid}"
    cached = _get_cache(cache_key, ttl=API2TRADE_CACHE_TTL)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/QuotesBulk"
    params = {"id": account_uuid, "symbols": ",".join(symbols)}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[API2Trade] bulk quotes error: {resp.status_code}")
    except Exception as e:
        print(f"[API2Trade] bulk quotes exception: {e}")

    return None


# ============================================
# 历史K线
# ============================================
async def get_historical_candles(
    symbol: str,
    account_uuid: str,
    timeframe: str = "1h",
    limit: int = 200
) -> Optional[List[Dict[str, Any]]]:
    """
    获取历史K线数据
    symbol: 品种名
    account_uuid: 账户 UUID
    timeframe: 周期 "1m","5m","15m","30m","1h","4h","1d","1w"
    limit: 数据条数
    """
    cache_key = f"candles_{symbol}_{timeframe}_{limit}_{account_uuid}"
    cached = _get_cache(cache_key, ttl=60)  # K线缓存60秒
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/CandlesHistory"
    params = {
        "id": account_uuid,
        "symbol": symbol,
        "timeframe": timeframe,
        "limit": limit,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and isinstance(data, list) and len(data) > 0:
                    _set_cache(cache_key, data)
                    return data
            else:
                print(f"[API2Trade] candles error for {symbol}: {resp.status_code}")
    except Exception as e:
        print(f"[API2Trade] candles exception for {symbol}: {e}")

    return None


# ============================================
# 持仓查询
# ============================================
async def get_positions(account_uuid: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取当前所有持仓
    """
    cache_key = f"positions_{account_uuid}"
    cached = _get_cache(cache_key, ttl=5)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/Positions"
    params = {"id": account_uuid}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data is not None:
                    _set_cache(cache_key, data)
                    return data
            else:
                print(f"[API2Trade] positions error: {resp.status_code}")
    except Exception as e:
        print(f"[API2Trade] positions exception: {e}")

    return None


async def get_symbol_positions(symbol: str, account_uuid: str) -> Optional[List[Dict[str, Any]]]:
    """
    获取指定品种的持仓
    """
    all_positions = await get_positions(account_uuid)
    if all_positions:
        return [p for p in all_positions if p.get("symbol", "").upper() == symbol.upper()]
    return None


# ============================================
# WebSocket 实时行情
# ============================================
class API2TradeWebSocket:
    """
    API2Trade WebSocket 客户端
    连接: wss://api.metatraderapi.dev/stream
    支持: 实时行情流、订单更新流、净值流
    """

    def __init__(self, account_uuid: str):
        self.account_uuid = account_uuid
        self.ws = None
        self._running = False
        self._handlers: Dict[str, callable] = {}
        self._task = None

    async def connect(self):
        """建立 WebSocket 连接"""
        try:
            self.ws = await httpx_ws_connect(
                API2TRADE_WS_URL,
                headers={"x-api-key": API2TRADE_API_KEY}
            )
            self._running = True
            # 发送订阅消息
            await self._send_subscribe()
            return True
        except Exception as e:
            print(f"[API2Trade WS] connect error: {e}")
            return False

    async def _send_subscribe(self):
        """发送订阅请求"""
        if self.ws:
            msg = {
                "action": "subscribe",
                "id": self.account_uuid,
                "streams": ["quotes", "equity", "orders"]
            }
            try:
                await self.ws.send_text(json.dumps(msg))
            except Exception as e:
                print(f"[API2Trade WS] subscribe error: {e}")

    async def listen(self):
        """监听消息"""
        if not self.ws:
            return

        try:
            async for msg in self.ws:
                if not self._running:
                    break
                data = json.loads(msg.text)
                stream = data.get("stream", "")
                if stream in self._handlers:
                    self._handlers[stream](data.get("data", {}))
        except Exception as e:
            print(f"[API2Trade WS] listen error: {e}")

    def on_quote(self, handler: callable):
        """注册行情回调"""
        self._handlers["quotes"] = handler

    def on_equity(self, handler: callable):
        """注册净值回调"""
        self._handlers["equity"] = handler

    def on_order(self, handler: callable):
        """注册订单回调"""
        self._handlers["orders"] = handler

    async def close(self):
        """关闭连接"""
        self._running = False
        if self.ws:
            await self.ws.aclose()


# 避免导入 httpx_ws（可能不存在），使用标准 websockets
def httpx_ws_connect(url: str, headers: dict = None):
    """WebSocket 连接（兼容写法）"""
    import websockets
    import asyncio
    return websockets.connect(url, additional_headers=headers)


# ============================================
# 工具函数：品种名转换
# ============================================
def normalize_symbol(internal_sym: str) -> str:
    """
    将内部品种名映射为 MT4/MT5 品种名
    internal_sym: e.g. "eurusd" -> "EURUSD"
    """
    mapping = {
        # 外汇
        "eurusd": "EURUSD", "gbpusd": "GBPUSD", "usdjpy": "USDJPY",
        "usdchf": "USDCHF", "audusd": "AUDUSD", "usdcad": "USDCAD",
        "nzdusd": "NZDUSD", "eurgbp": "EURGBP", "eurjpy": "EURJPY",
        "gbpjpy": "GBPJPY", "eurchf": "EURCHF", "audjpy": "AUDJPY",
        "euraud": "EURAUD", "gbpaud": "GBPAUD",
        # 贵金属
        "xauusd": "XAUUSD", "xagusd": "XAGUSD", "xptusd": "XPTUSD", "xpdusd": "XPDUSD",
        # 原油
        "wtiusd": "WTI", "brentusd": "BRENT", "ngasusd": "NGAS",
        # 指数
        "us30": "US30", "us100": "US100", "us500": "US500",
        "de40": "DE40", "hk50": "HK50", "jp225": "JP225", "au200": "AU200",
    }
    return mapping.get(internal_sym.lower(), internal_sym.upper())


def mt_to_internal(mt_sym: str) -> str:
    """将 MT4/MT5 品种名反向映射为内部品种名"""
    mapping = {
        # 外汇
        "EURUSD": "eurusd", "GBPUSD": "gbpusd", "USDJPY": "usdjpy",
        "USDCHF": "usdchf", "AUDUSD": "audusd", "USDCAD": "usdcad",
        "NZDUSD": "nzdusd", "EURGBP": "eurgbp", "EURJPY": "eurjpy",
        "GBPJPY": "gbpjpy", "EURCHF": "eurchf", "AUDJPY": "audjpy",
        "EURAUD": "euraud", "GBPAUD": "gbpaud",
        # 贵金属
        "XAUUSD": "xauusd", "XAGUSD": "xagusd", "XPTUSD": "xptusd", "XPDUSD": "xpdusd",
        # 原油
        "WTI": "wtiusd", "BRENT": "brentusd", "NGAS": "ngasusd",
        # 指数
        "US30": "us30", "US100": "us100", "US500": "us500",
        "DE40": "de40", "HK50": "hk50", "JP225": "jp225", "AU200": "au200",
    }
    return mapping.get(mt_sym.upper(), mt_sym.lower())


# ============================================
# 统一接口：获取实时报价（兼容 market.py）
# ============================================
async def get_symbol_price(symbol: str, account_uuid: str) -> Optional[Dict[str, Any]]:
    """
    获取单个品种实时报价（兼容 MetaApi 接口格式）
    返回: {bid, ask, last, time, brokerTime, ...}
    """
    mt_sym = normalize_symbol(symbol)
    quote = await get_symbol_quote(mt_sym, account_uuid)
    if quote:
        return quote
    return None
