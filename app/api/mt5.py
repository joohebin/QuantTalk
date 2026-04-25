"""
MetaApi MT5 真实账户客户端
接入 QuantAI Main 账户 (ID: ff982e56-23b0-4e3d-b6f6-7f7b8c40679e)
支持: 账户信息/实时行情/历史K线/持仓数据
"""

import httpx
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from app.config import METAAPI_ACCOUNT_ID, METAAPI_API_KEY, METAAPI_BASE_URL, METAAPI_CACHE_TTL

# ============================================
# 内部缓存
# ============================================
_mt5_cache: Dict[str, tuple] = {}  # key: cache_key, value: (timestamp, data)


def _get_headers() -> dict:
    """生成认证请求头"""
    return {
        "Authorization": f"Bearer {METAAPI_API_KEY}",
        "Content-Type": "application/json",
    }


def _get_cache(key: str, ttl: int) -> Optional[Any]:
    """读取缓存（未过期返回数据，否则返回 None）"""
    if key in _mt5_cache:
        ts, data = _mt5_cache[key]
        if datetime.now().timestamp() - ts < ttl:
            return data
    return None


def _set_cache(key: str, data: Any):
    """写入缓存"""
    _mt5_cache[key] = (datetime.now().timestamp(), data)


# ============================================
# 账户信息
# ============================================
async def get_account_info() -> Optional[Dict[str, Any]]:
    """
    获取 MT5 账户信息
    返回: {balance, equity, margin, ...}
    """
    cache_key = "account_info"
    cached = _get_cache(cache_key, ttl=30)  # 账户信息缓存30秒
    if cached is not None:
        return cached

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/accountInformation"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[MT5] account info error: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[MT5] account info exception: {e}")

    return None


# ============================================
# 持仓信息
# ============================================
async def get_positions() -> Optional[List[Dict[str, Any]]]:
    """获取所有持仓"""
    cache_key = "positions"
    cached = _get_cache(cache_key, ttl=5)
    if cached is not None:
        return cached

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/positions"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
    except Exception as e:
        print(f"[MT5] positions error: {e}")

    return None


# ============================================
# 交易品种
# ============================================
async def get_symbols() -> Optional[List[Dict[str, Any]]]:
    """获取账户支持的所有交易品种"""
    cache_key = "symbols"
    cached = _get_cache(cache_key, ttl=300)  # 品种列表缓存5分钟
    if cached is not None:
        return cached

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/symbols"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
    except Exception as e:
        print(f"[MT5] symbols error: {e}")

    return None


# ============================================
# 实时价格
# ============================================
async def get_symbol_price(symbol: str) -> Optional[Dict[str, Any]]:
    """
    获取单个品种实时报价
    symbol: MT5 品种名，如 "EURUSD", "XAUUSD"
    """
    cache_key = f"price_{symbol}"
    cached = _get_cache(cache_key, ttl=METAAPI_CACHE_TTL)
    if cached is not None:
        return cached

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/symbols/{symbol}/price"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers())
            if resp.status_code == 200:
                data = resp.json()
                _set_cache(cache_key, data)
                return data
            else:
                print(f"[MT5] price error for {symbol}: {resp.status_code}")
    except Exception as e:
        print(f"[MT5] price exception for {symbol}: {e}")

    return None


async def get_prices(symbols: List[str]) -> Dict[str, Optional[Dict[str, Any]]]:
    """批量获取多个品种实时报价"""
    results = {}
    for sym in symbols:
        results[sym] = await get_symbol_price(sym)
    return results


# ============================================
# 历史K线
# ============================================
async def get_historical_candles(
    symbol: str,
    timeframe: str = "1h",
    limit: int = 200
) -> Optional[List[Dict[str, Any]]]:
    """
    获取历史K线数据
    symbol: MT5 品种名
    timeframe: 周期 "1m","5m","15m","30m","1h","4h","1d","1w","1M"
    limit: 数据条数
    """
    # 时间框架映射
    tf_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
        "1M": "1mn",  # MT5 用 1mn 表示月线
    }
    mt5_tf = tf_map.get(timeframe, "1h")

    # 计算时间范围
    now = datetime.utcnow()
    time_map = {
        "1m": timedelta(minutes=limit),
        "5m": timedelta(minutes=limit * 5),
        "15m": timedelta(minutes=limit * 15),
        "30m": timedelta(minutes=limit * 30),
        "1h": timedelta(hours=limit),
        "4h": timedelta(hours=limit * 4),
        "1d": timedelta(days=limit),
        "1w": timedelta(weeks=limit),
        "1M": timedelta(days=limit * 30),
    }
    start_time = (now - time_map.get(timeframe, timedelta(hours=limit))).isoformat() + "Z"

    cache_key = f"candles_{symbol}_{mt5_tf}_{limit}"
    cached = _get_cache(cache_key, ttl=METAAPI_CACHE_TTL)
    if cached is not None:
        return cached

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/historical-candles"
    params = {
        "symbol": symbol,
        "timeframe": mt5_tf,
        "limit": limit,
        "startTime": start_time,
    }

    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and "candles" in data:
                    result = data["candles"]
                    _set_cache(cache_key, result)
                    return result
            else:
                print(f"[MT5] candles error for {symbol}: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"[MT5] candles exception for {symbol}: {e}")

    return None


# ============================================
# 当前K线 (实时)
# ============================================
async def get_current_candle(symbol: str, timeframe: str = "1h") -> Optional[Dict[str, Any]]:
    """
    获取当前K线（最新一根，实时更新）
    """
    tf_map = {
        "1m": "1m", "5m": "5m", "15m": "15m", "30m": "30m",
        "1h": "1h", "4h": "4h", "1d": "1d", "1w": "1w",
    }
    mt5_tf = tf_map.get(timeframe, "1h")

    url = f"{METAAPI_BASE_URL}/users/current/accounts/{METAAPI_ACCOUNT_ID}/symbols/{symbol}/candles"
    params = {"timeframe": mt5_tf}

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, headers=_get_headers(), params=params)
            if resp.status_code == 200:
                data = resp.json()
                if data and len(data) > 0:
                    return data[0]
    except Exception as e:
        print(f"[MT5] current candle error for {symbol}: {e}")

    return None


# ============================================
# 工具函数：品种名转换
# ============================================
def normalize_symbol(internal_sym: str) -> str:
    """
    将内部品种名映射为 MT5 品种名
    internal_sym: e.g. "eurusd" -> "EURUSD"
    """
    mapping = {
        "eurusd": "EURUSD", "gbpusd": "GBPUSD", "usdjpy": "USDJPY",
        "usdchf": "USDCHF", "audusd": "AUDUSD", "usdcad": "USDCAD",
        "nzdusd": "NZDUSD", "eurgbp": "EURGBP", "eurjpy": "EURJPY",
        "gbpjpy": "GBPJPY", "eurchf": "EURCHF", "audjpy": "AUDJPY",
        "euraud": "EURAUD", "gbpaud": "GBPAUD",
        "xauusd": "XAUUSD", "xagusd": "XAGUSD", "xptusd": "XPTUSD", "xpdusd": "XPDUSD",
        "wtiusd": "WTI", "brentusd": "BRENT", "ngasusd": "NGAS",
        "us30": "US30", "us100": "US100", "us500": "US500",
        "de40": "DE40", "hk50": "HK50", "jp225": "JP225", "au200": "AU200",
    }
    return mapping.get(internal_sym.lower(), internal_sym.upper())


def mt5_to_internal(mt5_sym: str) -> str:
    """将 MT5 品种名反向映射为内部品种名"""
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
    return mapping.get(mt5_sym.upper(), mt5_sym.lower())
