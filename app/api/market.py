from fastapi import APIRouter, Query
import httpx
import numpy as np
from datetime import datetime, timedelta
import random
import asyncio
from app.api import mt5  # MetaApi MT5 真实账户客户端

router = APIRouter()

# ============================================
# 交易品种符号定义
# ============================================

# A股 / 港股 / 美股
STOCK_SYMBOLS = {
    # A股指数
    "sh000001": {"name": "上证指数", "market": "A", "type": "index"},
    "sz399001": {"name": "深证成指", "market": "A", "type": "index"},
    "sz399006": {"name": "创业板指", "market": "A", "type": "index"},
    "sh000300": {"name": "沪深300", "market": "A", "type": "index"},
    "sh000016": {"name": "上证50", "market": "A", "type": "index"},
    "sh000688": {"name": "科创50", "market": "A", "type": "index"},
    # 港股
    "hkHSI": {"name": "恒生指数", "market": "HK", "type": "index"},
    "hk00700": {"name": "腾讯控股", "market": "HK", "type": "stock"},
    "hk09988": {"name": "阿里巴巴", "market": "HK", "type": "stock"},
    # 美股
    "usIXIC": {"name": "纳斯达克", "market": "US", "type": "index"},
    "usSPX": {"name": "标普500", "market": "US", "type": "index"},
    "usAAPL": {"name": "苹果", "market": "US", "type": "stock"},
    "usNVDA": {"name": "英伟达", "market": "US", "type": "stock"},
    "usTSLA": {"name": "特斯拉", "market": "US", "type": "stock"},
}

# 加密货币（对接 Binance）
CRYPTO_SYMBOLS = {
    # 主流币
    "btcusdt": {"name": "BTC/USDT", "market": "CRYPTO", "type": "crypto", "binance": "BTCUSDT"},
    "ethusdt": {"name": "ETH/USDT", "market": "CRYPTO", "type": "crypto", "binance": "ETHUSDT"},
    "bnbusdt": {"name": "BNB/USDT", "market": "CRYPTO", "type": "crypto", "binance": "BNBUSDT"},
    "solusdt": {"name": "SOL/USDT", "market": "CRYPTO", "type": "crypto", "binance": "SOLUSDT"},
    "xrpusdt": {"name": "XRP/USDT", "market": "CRYPTO", "type": "crypto", "binance": "XRPUSDT"},
    "adausdt": {"name": "ADA/USDT", "market": "CRYPTO", "type": "crypto", "binance": "ADAUSDT"},
    "dogeusdt": {"name": "DOGE/USDT", "market": "CRYPTO", "type": "crypto", "binance": "DOGEUSDT"},
    "avaxusdt": {"name": "AVAX/USDT", "market": "CRYPTO", "type": "crypto", "binance": "AVAXUSDT"},
    "dotusdt": {"name": "DOT/USDT", "market": "CRYPTO", "type": "crypto", "binance": "DOTUSDT"},
    "linkusdt": {"name": "LINK/USDT", "market": "CRYPTO", "type": "crypto", "binance": "LINKUSDT"},
    "maticusdt": {"name": "MATIC/USDT", "market": "CRYPTO", "type": "crypto", "binance": "MATICUSDT"},
    "ltcusdt": {"name": "LTC/USDT", "market": "CRYPTO", "type": "crypto", "binance": "LTCUSDT"},
    "aptusdt": {"name": "APT/USDT", "market": "CRYPTO", "type": "crypto", "binance": "APTUSDT"},
    "arbusdt": {"name": "ARB/USDT", "market": "CRYPTO", "type": "crypto", "binance": "ARBUSD"},
    "opusdt": {"name": "OP/USDT", "market": "CRYPTO", "type": "crypto", "binance": "OPUSDT"},
    "injusdt": {"name": "INJ/USDT", "market": "CRYPTO", "type": "crypto", "binance": "INJUSDT"},
    "suiusdt": {"name": "SUI/USDT", "market": "CRYPTO", "type": "crypto", "binance": "SUIUSDT"},
    "ftmusdt": {"name": "FTM/USDT", "market": "CRYPTO", "type": "crypto", "binance": "FTMUSDT"},
    "nearusdt": {"name": "NEAR/USDT", "market": "CRYPTO", "type": "crypto", "binance": "NEARUSDT"},
}

# MT4/MT5 外汇 & 贵金属 & 原油 & 指数（模拟）
FOREX_SYMBOLS = {
    # 外汇直盘
    "eurusd": {"name": "EUR/USD", "market": "FX", "type": "forex"},
    "gbpusd": {"name": "GBP/USD", "market": "FX", "type": "forex"},
    "usdjpy": {"name": "USD/JPY", "market": "FX", "type": "forex"},
    "usdchf": {"name": "USD/CHF", "market": "FX", "type": "forex"},
    "audusd": {"name": "AUD/USD", "market": "FX", "type": "forex"},
    "usdcad": {"name": "USD/CAD", "market": "FX", "type": "forex"},
    "nzdusd": {"name": "NZD/USD", "market": "FX", "type": "forex"},
    # 外汇交叉盘
    "eurgbp": {"name": "EUR/GBP", "market": "FX", "type": "forex"},
    "eurjpy": {"name": "EUR/JPY", "market": "FX", "type": "forex"},
    "gbpjpy": {"name": "GBP/JPY", "market": "FX", "type": "forex"},
    "eurchf": {"name": "EUR/CHF", "market": "FX", "type": "forex"},
    "audjpy": {"name": "AUD/JPY", "market": "FX", "type": "forex"},
    "euraud": {"name": "EUR/AUD", "market": "FX", "type": "forex"},
    "gbpaud": {"name": "GBP/AUD", "market": "FX", "type": "forex"},
    # 贵金属
    "xauusd": {"name": "黄金(美元)", "market": "METAL", "type": "metal"},
    "xagusd": {"name": "白银(美元)", "market": "METAL", "type": "metal"},
    "xptusd": {"name": "铂金(美元)", "market": "METAL", "type": "metal"},
    "xpdusd": {"name": "钯金(美元)", "market": "METAL", "type": "metal"},
    # 原油
    "wtiusd": {"name": "WTI原油", "market": "ENERGY", "type": "energy"},
    "brentusd": {"name": "布伦特原油", "market": "ENERGY", "type": "energy"},
    "ngasusd": {"name": "天然气", "market": "ENERGY", "type": "energy"},
    # 指数期货
    "us30": {"name": "道琼斯30", "market": "INDEX", "type": "index"},
    "us100": {"name": "纳斯达克100", "market": "INDEX", "type": "index"},
    "us500": {"name": "标普500", "market": "INDEX", "type": "index"},
    "de40": {"name": "德国DAX40", "market": "INDEX", "type": "index"},
    "hk50": {"name": "恒生指数", "market": "INDEX", "type": "index"},
    "jp225": {"name": "日经225", "market": "INDEX", "type": "index"},
    "au200": {"name": "澳指200", "market": "INDEX", "type": "index"},
}

# 合并所有符号
ALL_SYMBOLS = {**STOCK_SYMBOLS, **CRYPTO_SYMBOLS, **FOREX_SYMBOLS}

# K线基准价格（用于模拟生成）
KLINE_BASIS = {
    # A股/港股/美股
    "sh000001": 3250, "sz399001": 10800, "sz399006": 2150,
    "sh000300": 3800, "sh000016": 2650, "sh000688": 750,
    "hkHSI": 18500, "hk00700": 380, "hk09988": 82,
    "usIXIC": 18200, "usSPX": 5200,
    "usAAPL": 190, "usNVDA": 875, "usTSLA": 175,
    # 加密货币
    "btcusdt": 67500, "ethusdt": 3450, "bnbusdt": 580,
    "solusdt": 145, "xrpusdt": 0.62, "adausdt": 0.58,
    "dogeusdt": 0.165, "avaxusdt": 38, "dotusdt": 8.2,
    "linkusdt": 18.5, "maticusdt": 0.95, "ltcusdt": 88,
    "aptusdt": 9.8, "arbusdt": 1.15, "opusdt": 2.8,
    "injusdt": 26, "suiusdt": 1.35, "ftmusdt": 0.78,
    "nearusdt": 5.8,
    # 外汇
    "eurusd": 1.0850, "gbpusd": 1.2650, "usdjpy": 149.50,
    "usdchf": 0.8820, "audusd": 0.6520, "usdcad": 1.3580,
    "nzdusd": 0.6080, "eurgbp": 0.8580, "eurjpy": 162.20,
    "gbpjpy": 189.10, "eurchf": 0.9570, "audjpy": 97.50,
    "euraud": 1.6650, "gbpaud": 1.9420,
    # 贵金属
    "xauusd": 2340, "xagusd": 29.5, "xptusd": 1020, "xpdusd": 980,
    # 原油
    "wtiusd": 83.5, "brentusd": 88.0, "ngasusd": 2.65,
    # 指数
    "us30": 39500, "us100": 18500, "us500": 5250,
    "de40": 18600, "hk50": 18500, "jp225": 38500, "au200": 7850,
}


# ============================================
# Binance API 客户端
# ============================================
BINANCE_BASE = "https://api.binance.com"

# 缓存 Binance 数据（避免频繁请求）
_binance_cache = {}
_cache_ttl = 10  # 秒


async def fetch_binance_kline(symbol: str, interval: str, limit: int = 200):
    """从 Binance 获取 K线数据"""
    cache_key = f"kline_{symbol}_{interval}"
    now = datetime.now().timestamp()

    # 检查缓存
    if cache_key in _binance_cache:
        cached_time, cached_data = _binance_cache[cache_key]
        if now - cached_time < _cache_ttl:
            return cached_data

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{BINANCE_BASE}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                data = resp.json()
                result = [
                    {
                        "time": int(d[0]),
                        "open": float(d[1]),
                        "high": float(d[2]),
                        "low": float(d[3]),
                        "close": float(d[4]),
                        "volume": float(d[5]),
                    }
                    for d in data
                ]
                _binance_cache[cache_key] = (now, result)
                return result
    except Exception as e:
        print(f"Binance kline fetch error for {symbol}: {e}")

    return None


async def fetch_binance_ticker(symbol: str):
    """从 Binance 获取实时行情"""
    cache_key = f"ticker_{symbol}"
    now = datetime.now().timestamp()

    if cache_key in _binance_cache:
        cached_time, cached_data = _binance_cache[cache_key]
        if now - cached_time < 5:  # 5秒缓存
            return cached_data

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{BINANCE_BASE}/api/v3/ticker/24hr"
            params = {"symbol": symbol}
            resp = await client.get(url, params=params)
            if resp.status_code == 200:
                d = resp.json()
                result = {
                    "price": float(d["lastPrice"]),
                    "change": float(d["priceChange"]),
                    "change_pct": float(d["priceChangePercent"]),
                    "volume": float(d["quoteVolume"]),
                    "high": float(d["highPrice"]),
                    "low": float(d["lowPrice"]),
                    "timestamp": int(datetime.now().timestamp() * 1000),
                }
                _binance_cache[cache_key] = (now, result)
                return result
    except Exception as e:
        print(f"Binance ticker fetch error for {symbol}: {e}")

    return None


async def fetch_binance_recent_klines(symbol: str, limit: int = 100):
    """获取最近 K线（用于补充实时数据）"""
    return await fetch_binance_kline(symbol, "1m", limit)


# ============================================
# K线数据生成（模拟 + Binance 真实）
# ============================================
def generate_realistic_kline(base_price: float, count: int, interval_minutes: int) -> list:
    """生成模拟但合理的K线数据"""
    data = []
    current_price = base_price
    now = datetime.now()

    for i in range(count):
        timestamp = int((now - timedelta(minutes=interval_minutes * i)).timestamp() * 1000)

        volatility = 0.002 + random.random() * 0.008
        trend = random.choice([-1, 1]) * random.random() * 0.002

        open_price = current_price
        change_pct = (volatility + trend) * random.choice([-1, 1, 1, 1])
        close_price = open_price * (1 + change_pct)

        high_price = max(open_price, close_price) * (1 + random.random() * volatility)
        low_price = min(open_price, close_price) * (1 - random.random() * volatility)

        volume = int(1000000 + random.random() * 5000000)

        data.append({
            "time": timestamp,
            "open": round(open_price, 4 if base_price < 10 else 2),
            "high": round(high_price, 4 if base_price < 10 else 2),
            "low": round(low_price, 4 if base_price < 10 else 2),
            "close": round(close_price, 4 if base_price < 10 else 2),
            "volume": volume
        })

        current_price = close_price

    return list(reversed(data))


async def get_realtime_quote(symbol: str, fallback_price: float):
    """获取实时行情（优先 Binance/MT5 真实数据，备选模拟）"""
    symbol_upper = symbol.upper()

    # 加密货币：从 Binance 获取
    if symbol in CRYPTO_SYMBOLS:
        binance_sym = CRYPTO_SYMBOLS[symbol]["binance"]
        ticker = await fetch_binance_ticker(binance_sym)
        if ticker:
            return ticker

    # 外汇/贵金属/原油/指数：从 MetaApi MT5 真实账户获取
    if symbol in FOREX_SYMBOLS:
        mt5_sym = mt5.normalize_symbol(symbol)
        mt5_price = await mt5.get_symbol_price(mt5_sym)
        if mt5_price:
            # MetaApi 返回格式: {bid, ask, brokerTime, ...}
            # 需要计算 last price 和 change
            bid = mt5_price.get("bid", 0)
            ask = mt5_price.get("ask", 0)
            if bid and ask:
                current_price = (bid + ask) / 2
                base_price = KLINE_BASIS.get(symbol, fallback_price)
                change = current_price - base_price
                change_pct = (change / base_price * 100) if base_price else 0
                return {
                    "price": round(current_price, 5 if current_price < 0.01 else 4),
                    "bid": round(bid, 5 if bid < 0.01 else 4),
                    "ask": round(ask, 5 if ask < 0.01 else 4),
                    "change": round(change, 5 if abs(change) < 0.01 else 4),
                    "change_pct": round(change_pct, 2),
                    "volume": mt5_price.get("volume", 0) or 0,
                    "timestamp": mt5_price.get("time", int(datetime.now().timestamp() * 1000)),
                    "source": "mt5",
                }

    # 模拟实时波动（回退方案）
    base_price = KLINE_BASIS.get(symbol, fallback_price)
    change_pct = (random.random() - 0.5) * 0.005  # 外汇波动更小
    current_price = base_price * (1 + change_pct)
    change = current_price - base_price

    return {
        "price": round(current_price, 4 if base_price < 10 else 2),
        "change": round(change, 4 if base_price < 10 else 2),
        "change_pct": round(change_pct * 100, 2),
        "volume": int(50000000 + random.random() * 200000000),
        "timestamp": int(datetime.now().timestamp() * 1000),
        "source": "simulation",
    }


# ============================================
# API 路由
# ============================================
@router.get("/symbols")
async def get_symbols():
    """获取所有支持的交易品种"""
    # 分类返回
    return {
        "symbols": [
            {"symbol": k, **v} for k, v in STOCK_SYMBOLS.items()
        ],
        "crypto": [
            {"symbol": k, **v} for k, v in CRYPTO_SYMBOLS.items()
        ],
        "forex": [
            {"symbol": k, **v} for k, v in FOREX_SYMBOLS.items()
        ],
        "all": [
            {"symbol": k, **v} for k, v in ALL_SYMBOLS.items()
        ]
    }


@router.get("/kline/{symbol}")
async def get_kline(
    symbol: str,
    period: str = Query("1d", description="周期: 1m,5m,15m,30m,1h,4h,1d,1w"),
    limit: int = Query(100, ge=10, le=500)
):
    """
    获取K线数据（支持股票/加密货币/外汇/贵金属/原油/指数）
    加密货币使用 Binance 真实数据
    外汇/贵金属/原油/指数使用 MetaApi MT5 真实账户数据
    """
    symbol = symbol.lower()

    # 周期映射
    period_map = {
        "1m": ("1m", 1), "5m": ("5m", 5), "15m": ("15m", 15),
        "30m": ("30m", 30), "1h": ("1h", 60), "4h": ("4h", 240),
        "1d": ("1d", 1440), "1w": ("1w", 10080)
    }

    interval_str, interval_minutes = period_map.get(period, ("1d", 1440))

    # 获取品种信息
    stock_info = ALL_SYMBOLS.get(symbol, {
        "name": symbol.upper(),
        "market": "UNKNOWN",
        "type": "unknown"
    })

    base_price = KLINE_BASIS.get(symbol, 100)
    source = "simulation"

    # 加密货币：从 Binance 获取真实 K线
    if symbol in CRYPTO_SYMBOLS:
        binance_sym = CRYPTO_SYMBOLS[symbol]["binance"]
        real_data = await fetch_binance_kline(binance_sym, interval_str, limit)
        if real_data:
            ticker = await fetch_binance_ticker(binance_sym)
            return {
                "symbol": symbol,
                "name": stock_info["name"],
                "market": stock_info["market"],
                "type": stock_info["type"],
                "period": period,
                "base_price": base_price,
                "source": "binance",
                "latest": ticker or {},
                "data": real_data
            }
        data = generate_realistic_kline(base_price, limit, interval_minutes)

    # 外汇/贵金属/原油/指数：从 MetaApi MT5 获取真实 K线
    elif symbol in FOREX_SYMBOLS:
        mt5_sym = mt5.normalize_symbol(symbol)
        real_data = await mt5.get_historical_candles(mt5_sym, interval_str, limit)
        if real_data:
            data = [
                {
                    "time": int(c.get("time", 0) / 1000),  # MetaApi 毫秒时间戳 -> 秒
                    "open": float(c.get("open", 0)),
                    "high": float(c.get("high", 0)),
                    "low": float(c.get("low", 0)),
                    "close": float(c.get("close", 0)),
                    "volume": float(c.get("tickVolume", 0)),
                }
                for c in real_data
            ]
            source = "mt5"
        else:
            data = generate_realistic_kline(base_price, limit, interval_minutes)
    else:
        # 股票：使用模拟数据
        data = generate_realistic_kline(base_price, limit, interval_minutes)

    latest = await get_realtime_quote(symbol, base_price)

    return {
        "symbol": symbol,
        "name": stock_info["name"],
        "market": stock_info["market"],
        "type": stock_info["type"],
        "period": period,
        "base_price": base_price,
        "source": source,
        "latest": latest,
        "data": data
    }


@router.get("/realtime/{symbol}")
async def get_realtime(symbol: str):
    """获取单个标的实时行情"""
    symbol = symbol.lower()
    stock_info = ALL_SYMBOLS.get(symbol, {"name": symbol.upper()})
    base_price = KLINE_BASIS.get(symbol, 100)
    return await get_realtime_quote(symbol, base_price)


@router.get("/indices")
async def get_market_indices():
    """获取主要市场指数概览"""
    indices_data = [
        {"symbol": "sh000001", "name": "上证指数", "code": "SH000001"},
        {"symbol": "sz399001", "name": "深证成指", "code": "SZ399001"},
        {"symbol": "sz399006", "name": "创业板指", "code": "SZ399006"},
        {"symbol": "hkHSI", "name": "恒生指数", "code": "HSI"},
        {"symbol": "usIXIC", "name": "纳斯达克", "code": "IXIC"},
        {"symbol": "usSPX", "name": "标普500", "code": "SPX"},
    ]
    indices = []
    for idx in indices_data:
        quote = await get_realtime_quote(idx["symbol"], KLINE_BASIS.get(idx["symbol"], 3000))
        indices.append({**idx, **quote})
    return {"indices": indices}


@router.get("/hot-stocks")
async def get_hot_stocks():
    """热门股票"""
    stocks_list = [
        {"symbol": "usAAPL", "name": "苹果", "code": "AAPL"},
        {"symbol": "usNVDA", "name": "英伟达", "code": "NVDA"},
        {"symbol": "usTSLA", "name": "特斯拉", "code": "TSLA"},
        {"symbol": "hk00700", "name": "腾讯控股", "code": "00700"},
        {"symbol": "hk09988", "name": "阿里巴巴", "code": "09988"},
    ]
    stocks = []
    for s in stocks_list:
        quote = await get_realtime_quote(s["symbol"], KLINE_BASIS.get(s["symbol"], 200))
        stocks.append({**s, **quote})
    return {"stocks": stocks}


@router.get("/crypto")
async def get_crypto_market():
    """获取加密货币市场概览（实时 Binance 数据）"""
    crypto_list = [
        {"symbol": "btcusdt", "name": "BTC/USDT", "binance": "BTCUSDT"},
        {"symbol": "ethusdt", "name": "ETH/USDT", "binance": "ETHUSDT"},
        {"symbol": "bnbusdt", "name": "BNB/USDT", "binance": "BNBUSDT"},
        {"symbol": "solusdt", "name": "SOL/USDT", "binance": "SOLUSDT"},
        {"symbol": "xrpusdt", "name": "XRP/USDT", "binance": "XRPUSDT"},
        {"symbol": "adausdt", "name": "ADA/USDT", "binance": "ADAUSDT"},
        {"symbol": "dogeusdt", "name": "DOGE/USDT", "binance": "DOGEUSDT"},
        {"symbol": "avaxusdt", "name": "AVAX/USDT", "binance": "AVAXUSDT"},
        {"symbol": "dotusdt", "name": "DOT/USDT", "binance": "DOTUSDT"},
        {"symbol": "linkusdt", "name": "LINK/USDT", "binance": "LINKUSDT"},
    ]

    cryptos = []
    for c in crypto_list:
        ticker = await fetch_binance_ticker(c["binance"])
        if ticker:
            cryptos.append({**c, **ticker})
        else:
            quote = await get_realtime_quote(c["symbol"], KLINE_BASIS.get(c["symbol"], 100))
            cryptos.append({**c, **quote})

    return {"crypto": cryptos}


@router.get("/forex")
async def get_forex_market():
    """获取外汇/贵金属/原油/指数市场概览（MetaApi MT5 真实数据）"""
    forex_list = [
        # 外汇
        {"symbol": "eurusd", "name": "EUR/USD"},
        {"symbol": "gbpusd", "name": "GBP/USD"},
        {"symbol": "usdjpy", "name": "USD/JPY"},
        {"symbol": "audusd", "name": "AUD/USD"},
        {"symbol": "usdcad", "name": "USD/CAD"},
        # 贵金属
        {"symbol": "xauusd", "name": "黄金"},
        {"symbol": "xagusd", "name": "白银"},
        # 原油
        {"symbol": "wtiusd", "name": "WTI原油"},
        {"symbol": "brentusd", "name": "布伦特原油"},
    ]

    items = []
    for f in forex_list:
        quote = await get_realtime_quote(f["symbol"], KLINE_BASIS.get(f["symbol"], 100))
        items.append({**f, **quote})

    # 判断数据源
    has_mt5 = any(item.get("source") == "mt5" for item in items)
    return {
        "forex": items,
        "dataSource": "mt5" if has_mt5 else "simulation",
        "account": "QuantAI Main (MT5 Real)",
    }


@router.get("/trending-tags")
async def get_trending_tags():
    """热门标签"""
    return {
        "tags": [
            {"name": "量化策略", "count": 1256},
            {"name": "BTC", "count": 1100},
            {"name": "ETH", "count": 980},
            {"name": "A股", "count": 950},
            {"name": "港股", "count": 756},
            {"name": "美股", "count": 645},
            {"name": "黄金", "count": 580},
            {"name": "原油", "count": 534},
            {"name": "EUR/USD", "count": 490},
            {"name": "机器学习", "count": 480},
            {"name": "趋势跟踪", "count": 423},
            {"name": "网格交易", "count": 389},
            {"name": "期权", "count": 312},
            {"name": "技术分析", "count": 267},
            {"name": "DeFi", "count": 245},
            {"name": " Solana", "count": 220},
        ]
    }


# ============================================
# MetaApi MT5 真实账户端点
# ============================================
@router.get("/mt5/account")
async def get_mt5_account():
    """
    获取 MT5 真实账户信息
    账户: QuantAI Main (87954362)
    """
    info = await mt5.get_account_info()
    if info:
        return {
            "success": True,
            "account": "QuantAI Main",
            "accountId": info.get("login") or info.get("accountId"),
            "balance": info.get("balance"),
            "equity": info.get("equity"),
            "margin": info.get("margin"),
            "freeMargin": info.get("marginFree"),
            "profit": info.get("profit"),
            "marginLevel": info.get("marginLevel"),
            "leverage": info.get("leverage"),
            "currency": info.get("currency"),
            "server": info.get("server"),
            "connected": True,
        }
    return {
        "success": False,
        "message": "无法连接 MT5 真实账户，请检查 MetaApi 配置",
        "connected": False,
    }


@router.get("/mt5/positions")
async def get_mt5_positions():
    """获取 MT5 真实账户当前持仓"""
    positions = await mt5.get_positions()
    if positions is not None:
        return {
            "success": True,
            "positions": [
                {
                    "symbol": mt5.mt5_to_internal(p.get("symbol", "")),
                    "mt5Symbol": p.get("symbol"),
                    "type": p.get("type"),
                    "volume": p.get("volume"),
                    "openPrice": p.get("openPrice"),
                    "currentPrice": p.get("currentPrice"),
                    "profit": p.get("profit"),
                    "swap": p.get("swap"),
                    "openTime": p.get("openTime"),
                }
                for p in positions
            ]
        }
    return {"success": False, "positions": [], "message": "无法获取持仓数据"}


@router.get("/mt5/symbols")
async def get_mt5_symbols():
    """获取 MT5 账户支持的交易品种列表"""
    symbols = await mt5.get_symbols()
    if symbols:
        return {"success": True, "count": len(symbols), "symbols": symbols}
    return {"success": False, "symbols": [], "message": "无法获取品种列表"}


@router.get("/mt5/quote/{symbol}")
async def get_mt5_single_quote(symbol: str):
    """获取单个 MT5 品种的实时报价"""
    mt5_sym = mt5.normalize_symbol(symbol)
    price = await mt5.get_symbol_price(mt5_sym)
    if price:
        return {
            "success": True,
            "symbol": symbol,
            "mt5Symbol": mt5_sym,
            "bid": price.get("bid"),
            "ask": price.get("ask"),
            "last": price.get("last"),
            "time": price.get("time"),
            "brokerTime": price.get("brokerTime"),
        }
    return {"success": False, "symbol": symbol, "message": "无法获取报价"}
