"""
TradeMux MT5 API 对接模块
文档: https://docs.trademux.io/
Base URL: https://mux.skybluefin.tech
API Key 类型: MT5 (不是 OANDA)
"""

import httpx
from typing import Optional, Dict, List, Any
from datetime import datetime
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import asyncio

from app.config import TRADEMUX_BASE_URL, TRADEMUX_API_KEY

router = APIRouter(prefix="/api/trademux", tags=["TradeMux MT5"])

# Pydantic 模型
class TradeRequest(BaseModel):
    symbol: str
    lots: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    comment: Optional[str] = None

class ClosePositionRequest(BaseModel):
    ticket: int


class TradeMuxClient:
    """TradeMux MT5 API 客户端"""

class TradeMuxClient:
    """TradeMux MT5 API 客户端"""
    
    BASE_URL = "https://mux.skybluefin.tech"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    async def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送 HTTP 请求"""
        url = f"{self.BASE_URL}{endpoint}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            if method == "GET":
                response = await client.get(url, headers=self.headers)
            elif method == "POST":
                response = await client.post(url, headers=self.headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            result = response.json()
            if response.status_code != 200:
                raise Exception(f"API Error: {result.get('detail', 'Unknown error')}")
            return result
    
    async def get_server_status(self) -> Dict:
        """
        获取服务器状态
        返回: {"status": "ok"}
        """
        return await self._request("GET", "/")
    
    async def get_account_info(self) -> Dict:
        """
        获取账户信息
        需要 MT EA 连接并发送数据
        返回: {
            "account_number": "61439035",
            "balance": 6117.05,
            "equity": 6117.05,
            "floating_pnl": 0.0,
            "open_positions": 0,
            "open_trades": 0,
            "pending_orders": 0,
            "server": "Pepperstone-Demo",
            "updated_at": 1769321000.12
        }
        """
        return await self._request("GET", "/v1/account")
    
    async def get_balance(self) -> float:
        """获取账户余额"""
        info = await self.get_account_info()
        return info.get("balance", 0.0)
    
    async def get_equity(self) -> float:
        """获取账户净值"""
        info = await self.get_account_info()
        return info.get("equity", 0.0)
    
    async def get_floating_pnl(self) -> float:
        """获取浮动盈亏"""
        info = await self.get_account_info()
        return info.get("floating_pnl", 0.0)
    
    async def is_connected(self) -> bool:
        """检查是否已连接"""
        try:
            status = await self.get_server_status()
            return status.get("status") == "ok"
        except:
            return False
    
    async def get_positions(self) -> List[Dict]:
        """
        获取持仓列表
        需要 MT EA 连接
        """
        return await self._request("GET", "/v1/positions")
    
    async def get_orders(self) -> List[Dict]:
        """
        获取挂单列表
        需要 MT EA 连接
        """
        return await self._request("GET", "/v1/orders")
    
    # ========== 交易接口 ==========
    
    async def buy_market(self, symbol: str, lots: float, 
                        sl: Optional[float] = None,
                        tp: Optional[float] = None,
                        comment: Optional[str] = None) -> Dict:
        """
        市价买入
        需要 MT EA 连接
        """
        data = {
            "symbol": symbol,
            "lots": lots,
            "type": "BUY",
            "comment": comment or "tmux"
        }
        if sl:
            data["sl"] = sl
        if tp:
            data["tp"] = tp
        return await self._request("POST", "/v1/trade", data)
    
    async def sell_market(self, symbol: str, lots: float,
                         sl: Optional[float] = None,
                         tp: Optional[float] = None,
                         comment: Optional[str] = None) -> Dict:
        """
        市价卖出
        需要 MT EA 连接
        """
        data = {
            "symbol": symbol,
            "lots": lots,
            "type": "SELL",
            "comment": comment or "tmux"
        }
        if sl:
            data["sl"] = sl
        if tp:
            data["tp"] = tp
        return await self._request("POST", "/v1/trade", data)
    
    async def close_position(self, ticket: int) -> Dict:
        """
        平仓
        需要 MT EA 连接
        """
        return await self._request("POST", f"/v1/close/{ticket}", {})
    
    async def kill_switch(self) -> Dict:
        """
        关闭所有仓位（风控）
        需要 MT EA 连接
        """
        return await self._request("POST", "/v1/kill_switch", {})


# 同步版本的客户端
class TradeMuxSyncClient:
    """TradeMux MT5 API 同步客户端"""
    
    BASE_URL = "https://mux.skybluefin.tech"
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.headers = {
            "X-API-Key": api_key,
            "Content-Type": "application/json"
        }
    
    def _request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict:
        """发送 HTTP 请求"""
        import httpx
        url = f"{self.BASE_URL}{endpoint}"
        
        if method == "GET":
            response = httpx.get(url, headers=self.headers, timeout=30)
        elif method == "POST":
            response = httpx.post(url, headers=self.headers, json=data, timeout=30)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        result = response.json()
        if response.status_code != 200:
            raise Exception(f"API Error: {result.get('detail', 'Unknown error')}")
        return result
    
    def get_server_status(self) -> Dict:
        """获取服务器状态"""
        return self._request("GET", "/")
    
    def get_account_info(self) -> Dict:
        """获取账户信息"""
        return self._request("GET", "/v1/account")
    
    def is_connected(self) -> bool:
        """检查是否已连接"""
        try:
            status = self.get_server_status()
            return status.get("status") == "ok"
        except:
            return False
    
    def get_balance(self) -> float:
        """获取账户余额"""
        info = self.get_account_info()
        return info.get("balance", 0.0)
    
    def get_equity(self) -> float:
        """获取账户净值"""
        info = self.get_account_info()
        return info.get("equity", 0.0)
    
    def get_floating_pnl(self) -> float:
        """获取浮动盈亏"""
        info = self.get_account_info()
        return info.get("floating_pnl", 0.0)
    
    def get_positions(self) -> List[Dict]:
        """获取持仓列表"""
        return self._request("GET", "/v1/positions")
    
    def get_orders(self) -> List[Dict]:
        """获取挂单列表"""
        return self._request("GET", "/v1/orders")


# 便捷函数
def create_client(api_key: str) -> TradeMuxSyncClient:
    """创建 TradeMux 客户端"""
    return TradeMuxSyncClient(api_key)


# 创建全局客户端实例
_client = None

def get_client() -> TradeMuxSyncClient:
    """获取客户端实例"""
    global _client
    if _client is None:
        _client = TradeMuxSyncClient(TRADEMUX_API_KEY)
    return _client


# ========== FastAPI 路由 ==========

@router.get("/status")
async def get_status():
    """获取 TradeMux 服务器状态"""
    try:
        client = get_client()
        return await asyncio.to_thread(client.get_server_status)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/account")
async def get_account():
    """
    获取 MT5 账户信息
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(client.get_account_info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/positions")
async def get_positions():
    """
    获取持仓列表
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(client.get_positions)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/orders")
async def get_orders():
    """
    获取挂单列表
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(client.get_orders)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/trade")
async def trade(request: TradeRequest):
    """
    执行交易（市价单）
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(
            client.buy_market, 
            request.symbol, 
            request.lots,
            request.sl,
            request.tp,
            request.comment
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/close")
async def close_position(request: ClosePositionRequest):
    """
    平仓
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(client.close_position, request.ticket)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/kill_switch")
async def kill_switch():
    """
    关闭所有仓位（风控）
    需要 MT EA 连接
    """
    try:
        client = get_client()
        return await asyncio.to_thread(client.kill_switch)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "service": "trademux"}


if __name__ == "__main__":
    # 测试代码
    API_KEY = "starter_tmux_yoX0qbnh5pZT9HFOVcOvrUSc"
    client = TradeMuxSyncClient(API_KEY)
    
    print("=== TradeMux API Test ===")
    
    # Test server status
    try:
        status = client.get_server_status()
        print(f"[OK] Server Status: {status}")
    except Exception as e:
        print(f"[FAIL] Server Status: {e}")
    
    # Test account info (requires MT EA connection)
    try:
        account = client.get_account_info()
        print(f"[OK] Account Info: {account}")
    except Exception as e:
        print(f"[INFO] Account Info: {e}")
    
    # Test connection status
    try:
        connected = client.is_connected()
        print(f"[OK] Connected: {'Yes' if connected else 'No'}")
    except Exception as e:
        print(f"[FAIL] Connection Check: {e}")
