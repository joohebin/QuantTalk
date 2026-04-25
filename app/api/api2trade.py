"""
API2Trade MT4/MT5 API 客户端
文档: https://www.api2trade.com
Base URL: https://api.metatraderapi.dev
认证: x-api-key header

支持功能:
- 账户摘要 (AccountSummary)
- 实时行情 (GetQuote)
- 持仓查询 (GetPositions)
"""

import httpx
from datetime import datetime
from typing import Optional, Dict, Any, List

# ============================================
# 配置
# ============================================
from app.config import API2TRADE_BASE_URL, API2TRADE_API_KEY, API2TRADE_ACCOUNT_UUID, API2TRADE_CACHE_TTL

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
    """获取账户信息（兼容格式）"""
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
    返回: {"symbol", "bid", "ask", "time"}
    """
    cache_key = f"quote_{symbol}_{account_uuid}"
    cached = _get_cache(cache_key, ttl=API2TRADE_CACHE_TTL)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/GetQuote"
    params = {"id": account_uuid, "symbol": symbol}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            elif resp.status_code == 201:
                # 品种不存在（账户不支持）
                return None
            else:
                print(f"[API2Trade] quote error for {symbol}: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"[API2Trade] quote exception for {symbol}: {e}")

    return None


async def get_bulk_quotes(symbols: List[str], account_uuid: str) -> Dict[str, Optional[Dict[str, Any]]]:
    """批量获取多个品种实时报价"""
    results = {}
    for sym in symbols:
        results[sym] = await get_symbol_quote(sym, account_uuid)
    return results


# ============================================
# 持仓查询
# ============================================
async def get_positions(account_uuid: str) -> Optional[List[Dict[str, Any]]]:
    """获取当前所有持仓"""
    cache_key = f"positions_{account_uuid}"
    cached = _get_cache(cache_key, ttl=5)
    if cached is not None:
        return cached

    url = f"{API2TRADE_BASE_URL}/GetPositions"
    params = {"id": account_uuid}

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[API2Trade] positions error: {resp.status_code} {resp.text[:100]}")
    except Exception as e:
        print(f"[API2Trade] positions exception: {e}")

    return None


# ============================================
# 工具函数：品种名转换
# ============================================
def normalize_symbol(internal_sym: str) -> str:
    """
    将内部品种名映射为 MT4/MT5 品种名
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
        "EURUSD": "eurusd", "GBPUSD": "gbpusd", "USDJPY": "usdjpy",
        "USDCHF": "usdchf", "AUDUSD": "audusd", "USDCAD": "usdcad",
        "NZDUSD": "nzdusd", "EURGBP": "eurgbp", "EURJPY": "eurjpy",
        "GBPJPY": "gbpjpy", "EURCHF": "eurchf", "AUDJPY": "audjpy",
        "EURAUD": "euraud", "GBPAUD": "gbpaud",
        "XAUUSD": "xauusd", "XAGUSD": "xagusd", "XPTUSD": "xptusd", "XPDUSD": "xpdusd",
        "WTI": "wtiusd", "BRENT": "brentusd", "NGAS": "ngasusd",
        "US30": "us30", "US100": "us100", "US500": "us500",
        "DE40": "de40", "HK50": "hk50", "JP225": "jp225", "AU200": "au200",
    }
    return mapping.get(mt_sym.upper(), mt_sym.lower())


# ============================================
# 统一接口：获取实时报价
# ============================================
async def get_symbol_price(symbol: str, account_uuid: str) -> Optional[Dict[str, Any]]:
    """获取单个品种实时报价"""
    mt_sym = normalize_symbol(symbol)
    quote = await get_symbol_quote(mt_sym, account_uuid)
    if quote:
        return quote
    return None


# ============================================
# 历史K线（API2Trade REST API 暂不支持，返回 None）
# 注意: API2Trade 只提供实时报价 WebSocket，历史K线需要自行构建或使用其他数据源
# ============================================
async def get_historical_candles(
    symbol: str,
    account_uuid: str,
    timeframe: str = "1h",
    limit: int = 200
) -> Optional[List[Dict[str, Any]]]:
    """
    获取历史K线数据
    
    注意: API2Trade REST API 暂不支持历史K线接口。
    如需K线数据，可考虑:
    1. 使用 Binance API（加密货币已有完整K线支持）
    2. 使用 MetaApi MT5（备用方案）
    3. 通过 WebSocket 实时报价自行构建K线
    
    此函数返回 None，让调用方使用备选方案。
    """
    # API2Trade REST API 不提供历史K线端点
    # 文档: https://www.api2trade.com
    # 主要接口: AccountSummary, GetQuote, GetPositions
    return None
