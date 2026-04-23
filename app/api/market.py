from fastapi import APIRouter
import httpx

router = APIRouter()


@router.get("/indices")
async def get_market_indices():
    """获取主要市场指数概览（模拟数据）"""
    return {
        "indices": [
            {"name": "上证指数", "code": "SH000001", "price": 3256.78, "change": 1.23, "change_pct": 0.038},
            {"name": "深证成指", "code": "SZ399001", "price": 10892.34, "change": -45.67, "change_pct": -0.42},
            {"name": "创业板指", "code": "SZ399006", "price": 2178.90, "change": 23.45, "change_pct": 1.09},
            {"name": "恒生指数", "code": "HSI", "price": 18567.23, "change": 312.56, "change_pct": 1.71},
            {"name": "纳斯达克", "code": "IXIC", "price": 18234.56, "change": -89.12, "change_pct": -0.49},
            {"name": "标普500", "code": "SPX", "price": 5234.78, "change": 34.67, "change_pct": 0.67},
        ]
    }


@router.get("/hot-stocks")
async def get_hot_stocks():
    """热门股票（模拟数据）"""
    return {
        "stocks": [
            {"name": "贵州茅台", "code": "600519", "price": 1688.00, "change_pct": 2.35},
            {"name": "宁德时代", "code": "300750", "price": 218.50, "change_pct": -1.28},
            {"name": "比亚迪", "code": "002594", "price": 267.80, "change_pct": 3.67},
            {"name": "中国平安", "code": "601318", "price": 45.60, "change_pct": 0.88},
            {"name": "招商银行", "code": "600036", "price": 35.20, "change_pct": -0.56},
            {"name": "腾讯控股", "code": "00700", "price": 378.40, "change_pct": 1.95},
            {"name": "阿里巴巴", "code": "09988", "price": 82.35, "change_pct": 4.12},
            {"name": "苹果", "code": "AAPL", "price": 189.50, "change_pct": -0.32},
            {"name": "英伟达", "code": "NVDA", "price": 875.30, "change_pct": 2.89},
            {"name": "特斯拉", "code": "TSLA", "price": 178.90, "change_pct": -2.15},
        ]
    }


@router.get("/trending-tags")
async def get_trending_tags():
    """热门标签"""
    return {
        "tags": [
            {"name": "量化策略", "count": 1256},
            {"name": "A股", "count": 983},
            {"name": "港股", "count": 756},
            {"name": "美股", "count": 645},
            {"name": "机器学习", "count": 534},
            {"name": "趋势跟踪", "count": 423},
            {"name": "网格交易", "count": 389},
            {"name": "期权", "count": 312},
            {"name": "加密货币", "count": 298},
            {"name": "技术分析", "count": 267},
        ]
    }
