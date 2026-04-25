"""
交易所 API 配置管理
用户端配置自己的交易所 API Key
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import hashlib
import hmac
import time
import httpx

from app.database import get_db
from app.models import ExchangeConfig, SUPPORTED_EXCHANGES, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/exchanges", tags=["交易所配置"])

# ============ Pydantic 模型 ============

class ExchangeConfigCreate(BaseModel):
    exchange: str = Field(..., description="交易所标识: binance, okx, bybit, etc.")
    api_key: str = Field(..., description="API Key")
    api_secret: str = Field(..., description="API Secret")
    passphrase: Optional[str] = Field(None, description="Passphrase (OKX等需要)")
    label: str = Field("", description="自定义标签")


class ExchangeConfigUpdate(BaseModel):
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    passphrase: Optional[str] = None
    label: Optional[str] = None
    is_enabled: Optional[bool] = None


class ExchangeConfigResponse(BaseModel):
    id: int
    exchange: str
    label: str
    api_key_masked: str  # 脱敏显示
    is_enabled: bool
    is_verified: bool
    last_sync: Optional[datetime]
    created_at: datetime
    
    class Config:
        from_attributes = True


class ExchangeInfo(BaseModel):
    id: str
    name: str
    icon: str
    need_passphrase: bool
    docs_url: str


# ============ 交易所验证函数 ============

async def verify_binance(api_key: str, api_secret: str) -> dict:
    """验证 Binance API Key"""
    try:
        timestamp = int(time.time() * 1000)
        params = f"timestamp={timestamp}"
        
        # 生成签名
        signature = hmac.new(
            api_secret.encode('utf-8'),
            params.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        url = f"https://api.binance.com/api/v3/account?timestamp={timestamp}&signature={signature}"
        headers = {"X-MBX-APIKEY": api_key}
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "valid": True,
                    "account_type": "SPOT",
                    "balances": [(b['asset'], float(b['free'])) for b in data.get('balances', []) if float(b['free']) > 0][:10]
                }
            else:
                return {"valid": False, "error": response.json().get('msg', 'Unknown error')}
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def verify_okx(api_key: str, api_secret: str, passphrase: str) -> dict:
    """验证 OKX API Key"""
    try:
        timestamp = time.time()
        message = f"{timestamp}GET/account/balance"
        signature = hmac.new(
            api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "OK-ACCESS-KEY": api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": str(timestamp),
            "OK-ACCESS-PASSPHRASE": passphrase,
            "Content-Type": "application/json"
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://www.okx.com/api/v5/account/balance",
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('code') == '0':
                    return {"valid": True, "account_type": "SPOT"}
                else:
                    return {"valid": False, "error": data.get('msg', 'Unknown error')}
            else:
                return {"valid": False, "error": response.text}
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def verify_bybit(api_key: str, api_secret: str) -> dict:
    """验证 Bybit API Key"""
    try:
        timestamp = str(int(time.time() * 1000))
        param_str = f"api_key={api_key}&timestamp={timestamp}"
        
        signature = hmac.new(
            api_secret.encode('utf-8'),
            param_str.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        headers = {
            "X-BAPI-API-KEY": api_key,
            "X-BAPI-TIMESTAMP": timestamp,
            "X-BAPI-SIGN": signature,
            "X-BAPI-SIGN-TYPE": "2"
        }
        
        async with httpx.AsyncClient(timeout=10) as client:
            response = await client.get(
                "https://api.bybit.com/v5/account/wallet-balance",
                params={"accountType": "UNIFIED"},
                headers=headers
            )
            
            if response.status_code == 200:
                data = response.json()
                if data.get('retCode') == 0:
                    return {"valid": True, "account_type": "UNIFIED"}
                else:
                    return {"valid": False, "error": data.get('retMsg', 'Unknown error')}
            else:
                return {"valid": False, "error": response.text}
    except Exception as e:
        return {"valid": False, "error": str(e)}


async def verify_exchange(exchange: str, api_key: str, api_secret: str, passphrase: str = None) -> dict:
    """验证交易所 API 连接"""
    if exchange == "binance":
        return await verify_binance(api_key, api_secret)
    elif exchange == "okx":
        return await verify_okx(api_key, api_secret, passphrase or "")
    elif exchange == "bybit":
        return await verify_bybit(api_key, api_secret)
    else:
        # 对于其他交易所，暂时标记为未验证
        return {"valid": True, "account_type": "unknown", "note": "Verification not implemented"}


def mask_api_key(api_key: str) -> str:
    """脱敏 API Key 显示"""
    if len(api_key) <= 8:
        return "***"
    return f"{api_key[:4]}...{api_key[-4:]}"


# ============ API 端点 ============

@router.get("/supported", response_model=List[ExchangeInfo])
async def get_supported_exchanges():
    """获取支持的交易所列表"""
    return [
        ExchangeInfo(id=k, **v) for k, v in SUPPORTED_EXCHANGES.items()
    ]


@router.get("/", response_model=List[ExchangeConfigResponse])
async def list_exchange_configs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取用户的所有交易所配置"""
    configs = db.query(ExchangeConfig).filter(
        ExchangeConfig.user_id == current_user.id
    ).order_by(ExchangeConfig.created_at.desc()).all()
    
    return [
        ExchangeConfigResponse(
            id=c.id,
            exchange=c.exchange,
            label=c.label,
            api_key_masked=mask_api_key(c.api_key),
            is_enabled=c.is_enabled,
            is_verified=c.is_verified,
            last_sync=c.last_sync,
            created_at=c.created_at
        )
        for c in configs
    ]


@router.post("/", response_model=ExchangeConfigResponse)
async def create_exchange_config(
    config: ExchangeConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建交易所配置"""
    # 检查交易所是否支持
    if config.exchange not in SUPPORTED_EXCHANGES:
        raise HTTPException(status_code=400, detail=f"不支持的交易所: {config.exchange}")
    
    # 检查是否已存在相同交易所配置
    existing = db.query(ExchangeConfig).filter(
        ExchangeConfig.user_id == current_user.id,
        ExchangeConfig.exchange == config.exchange
    ).first()
    
    if existing:
        raise HTTPException(status_code=400, detail=f"已存在 {SUPPORTED_EXCHANGES[config.exchange]['name']} 配置，请先删除再创建")
    
    # 创建配置
    db_config = ExchangeConfig(
        user_id=current_user.id,
        exchange=config.exchange,
        api_key=config.api_key,
        api_secret=config.api_secret,
        passphrase=config.passphrase,
        label=config.label
    )
    
    db.add(db_config)
    db.commit()
    db.refresh(db_config)
    
    # 异步验证连接
    verification = await verify_exchange(
        config.exchange,
        config.api_key,
        config.api_secret,
        config.passphrase
    )
    
    db_config.is_verified = verification.get("valid", False)
    db_config.last_sync = datetime.now()
    db.commit()
    db.refresh(db_config)
    
    return ExchangeConfigResponse(
        id=db_config.id,
        exchange=db_config.exchange,
        label=db_config.label,
        api_key_masked=mask_api_key(db_config.api_key),
        is_enabled=db_config.is_enabled,
        is_verified=db_config.is_verified,
        last_sync=db_config.last_sync,
        created_at=db_config.created_at
    )


@router.get("/{exchange_id}", response_model=ExchangeConfigResponse)
async def get_exchange_config(
    exchange_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取单个交易所配置"""
    config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == exchange_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    return ExchangeConfigResponse(
        id=config.id,
        exchange=config.exchange,
        label=config.label,
        api_key_masked=mask_api_key(config.api_key),
        is_enabled=config.is_enabled,
        is_verified=config.is_verified,
        last_sync=config.last_sync,
        created_at=config.created_at
    )


@router.put("/{exchange_id}", response_model=ExchangeConfigResponse)
async def update_exchange_config(
    exchange_id: int,
    config: ExchangeConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新交易所配置"""
    db_config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == exchange_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    # 更新字段
    if config.api_key is not None:
        db_config.api_key = config.api_key
    if config.api_secret is not None:
        db_config.api_secret = config.api_secret
    if config.passphrase is not None:
        db_config.passphrase = config.passphrase
    if config.label is not None:
        db_config.label = config.label
    if config.is_enabled is not None:
        db_config.is_enabled = config.is_enabled
    
    db_config.updated_at = datetime.now()
    db.commit()
    db.refresh(db_config)
    
    # 如果更新了密钥，重新验证
    if config.api_key or config.api_secret or config.passphrase:
        verification = await verify_exchange(
            db_config.exchange,
            db_config.api_key,
            db_config.api_secret,
            db_config.passphrase
        )
        db_config.is_verified = verification.get("valid", False)
        db_config.last_sync = datetime.now()
        db.commit()
        db.refresh(db_config)
    
    return ExchangeConfigResponse(
        id=db_config.id,
        exchange=db_config.exchange,
        label=db_config.label,
        api_key_masked=mask_api_key(db_config.api_key),
        is_enabled=db_config.is_enabled,
        is_verified=db_config.is_verified,
        last_sync=db_config.last_sync,
        created_at=db_config.created_at
    )


@router.delete("/{exchange_id}")
async def delete_exchange_config(
    exchange_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除交易所配置"""
    db_config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == exchange_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    db.delete(db_config)
    db.commit()
    
    return {"message": "删除成功"}


@router.post("/{exchange_id}/verify")
async def verify_exchange_config(
    exchange_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """重新验证交易所连接"""
    db_config = db.query(ExchangeConfig).filter(
        ExchangeConfig.id == exchange_id,
        ExchangeConfig.user_id == current_user.id
    ).first()
    
    if not db_config:
        raise HTTPException(status_code=404, detail="配置不存在")
    
    verification = await verify_exchange(
        db_config.exchange,
        db_config.api_key,
        db_config.api_secret,
        db_config.passphrase
    )
    
    db_config.is_verified = verification.get("valid", False)
    db_config.last_sync = datetime.now()
    db.commit()
    
    return {
        "verified": verification.get("valid", False),
        "message": "验证成功" if verification.get("valid") else verification.get("error", "验证失败")
    }
