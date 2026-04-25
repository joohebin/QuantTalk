"""
第四阶段：加密货币钱包和好友转账API
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import uuid
import hashlib

from app.database import get_db
from app.models import User
from app.models_phase4 import (
    UserWallet, WalletBalance, TransferRecord, 
    WalletNotification, WithdrawalRequest, DepositAddress
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/wallet", tags=["第四阶段：钱包和转账"])

# ============================================
# Pydantic Schemas
# ============================================

class WalletBindRequest(BaseModel):
    currency: str  # BTC/ETH/USDT等
    address: str
    label: str = ""
    is_primary: bool = False


class WalletResponse(BaseModel):
    id: int
    currency: str
    address: str
    label: str
    is_primary: bool
    is_verified: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class BalanceResponse(BaseModel):
    currency: str
    available: float
    locked: float
    total: float
    
    class Config:
        from_attributes = True


class TransferRequest(BaseModel):
    receiver_username: str  # 通过用户名查找
    currency: str
    amount: float
    note: str = ""


class TransferResponse(BaseModel):
    id: int
    tx_hash: str
    sender_id: int
    receiver_id: int
    currency: str
    amount: float
    fee: float
    note: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class NotificationResponse(BaseModel):
    id: int
    type: str
    title: str
    content: str
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class DepositAddressResponse(BaseModel):
    currency: str
    address: str
    qr_code: Optional[str]
    
    class Config:
        from_attributes = True


# ============================================
# 辅助函数
# ============================================

def generate_tx_hash(sender_id: int, receiver_id: int, amount: float) -> str:
    """生成模拟交易哈希"""
    raw = f"{sender_id}{receiver_id}{amount}{datetime.now().isoformat()}"
    return hashlib.sha256(raw.encode()).hexdigest()


def calculate_fee(amount: float, currency: str) -> float:
    """计算转账手续费"""
    fee_rates = {
        "USDT": 1.0,   # 1 USDT 固定手续费
        "USDC": 1.0,
        "BTC": 0.0001,
        "ETH": 0.002,
        "BNB": 0.1,
    }
    return fee_rates.get(currency, 0.01)


def ensure_user_balance(user_id: int, currency: str, db: Session, initial_balance: float = 10000.0) -> WalletBalance:
    """确保用户有该币种的余额记录，如无则创建（模拟充值）"""
    balance = db.query(WalletBalance).filter(
        WalletBalance.user_id == user_id,
        WalletBalance.currency == currency
    ).first()
    
    if not balance:
        balance = WalletBalance(
            user_id=user_id,
            currency=currency,
            available_balance=initial_balance,
            total_received=initial_balance
        )
        db.add(balance)
        db.commit()
        db.refresh(balance)
    
    return balance


def create_notification(db: Session, user_id: int, notif_type: str, title: str, content: str, transfer_id: int = None):
    """创建钱包通知"""
    notification = WalletNotification(
        user_id=user_id,
        notification_type=notif_type,
        title=title,
        content=content,
        related_transfer_id=transfer_id
    )
    db.add(notification)
    return notification


# ============================================
# 支持的币种列表
# ============================================

SUPPORTED_CURRENCIES = ["BTC", "ETH", "USDT", "USDC", "BNB"]


@router.get("/currencies", response_model=List[str])
async def get_supported_currencies():
    """获取支持的钱包币种列表"""
    return SUPPORTED_CURRENCIES


# ============================================
# 钱包绑定
# ============================================

@router.get("/wallets", response_model=List[WalletResponse])
async def get_my_wallets(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取我的已绑定钱包列表"""
    wallets = db.query(UserWallet).filter(UserWallet.user_id == current_user.id).all()
    return wallets


@router.post("/wallets", response_model=WalletResponse)
async def bind_wallet(
    request: WalletBindRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """绑定新的加密货币钱包地址"""
    currency = request.currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"不支持的币种: {currency}")
    
    # 验证地址格式（简化版）
    if len(request.address) < 20:
        raise HTTPException(status_code=400, detail="钱包地址格式无效")
    
    # 检查是否已存在相同的地址
    existing = db.query(UserWallet).filter(UserWallet.address == request.address).first()
    if existing:
        raise HTTPException(status_code=400, detail="该钱包地址已被其他用户绑定")
    
    # 如果设置为主钱包，取消其他主钱包
    if request.is_primary:
        db.query(UserWallet).filter(
            UserWallet.user_id == current_user.id,
            UserWallet.currency == currency
        ).update({"is_primary": False})
    
    wallet = UserWallet(
        user_id=current_user.id,
        currency=currency,
        address=request.address,
        label=request.label,
        is_primary=request.is_primary,
        is_verified=False  # 简化：跳过小额验证
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    
    return wallet


@router.delete("/wallets/{wallet_id}")
async def unbind_wallet(
    wallet_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """解绑钱包"""
    wallet = db.query(UserWallet).filter(
        UserWallet.id == wallet_id,
        UserWallet.user_id == current_user.id
    ).first()
    
    if not wallet:
        raise HTTPException(status_code=404, detail="钱包不存在")
    
    db.delete(wallet)
    db.commit()
    
    return {"message": "钱包已解绑"}


# ============================================
# 余额管理
# ============================================

@router.get("/balances", response_model=List[BalanceResponse])
async def get_balances(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取我的所有余额"""
    balances = db.query(WalletBalance).filter(WalletBalance.user_id == current_user.id).all()
    
    # 如果没有任何余额，给所有支持币种创建初始余额
    if not balances:
        for currency in SUPPORTED_CURRENCIES:
            balance = WalletBalance(
                user_id=current_user.id,
                currency=currency,
                available_balance=10000.0 if currency == "USDT" else 0.0
            )
            db.add(balance)
        db.commit()
        balances = db.query(WalletBalance).filter(WalletBalance.user_id == current_user.id).all()
    
    return [
        BalanceResponse(
            currency=b.currency,
            available=b.available_balance,
            locked=b.locked_balance,
            total=b.available_balance + b.locked_balance
        )
        for b in balances
    ]


@router.get("/balances/{currency}", response_model=BalanceResponse)
async def get_balance(
    currency: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定币种余额"""
    currency = currency.upper()
    balance = db.query(WalletBalance).filter(
        WalletBalance.user_id == current_user.id,
        WalletBalance.currency == currency
    ).first()
    
    if not balance:
        # 自动创建
        balance = ensure_user_balance(current_user.id, currency, db)
    
    return BalanceResponse(
        currency=balance.currency,
        available=balance.available_balance,
        locked=balance.locked_balance,
        total=balance.available_balance + balance.locked_balance
    )


# ============================================
# 好友转账
# ============================================

@router.post("/transfer", response_model=TransferResponse)
async def transfer_to_friend(
    request: TransferRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """向好友转账（模拟加密货币转账）"""
    currency = request.currency.upper()
    
    # 查找接收者
    receiver = db.query(User).filter(User.username == request.receiver_username).first()
    if not receiver:
        raise HTTPException(status_code=404, detail=f"用户 {request.receiver_username} 不存在")
    
    if receiver.id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己转账")
    
    # 检查是否已是好友
    is_friend = db.query(User).filter(
        User.id == current_user.id,
        User.friends.contains(receiver)
    ).first()
    if not is_friend:
        raise HTTPException(status_code=403, detail="只能向好友转账")
    
    # 获取余额
    balance = db.query(WalletBalance).filter(
        WalletBalance.user_id == current_user.id,
        WalletBalance.currency == currency
    ).first()
    
    if not balance:
        raise HTTPException(status_code=400, detail=f"您还没有 {currency} 余额，请先充值")
    
    # 计算手续费
    fee = calculate_fee(request.amount, currency)
    total = request.amount + fee
    
    if balance.available_balance < total:
        raise HTTPException(status_code=400, detail=f"余额不足 (需要 {total} {currency}, 可用 {balance.available_balance} {currency})")
    
    # 扣除余额
    balance.available_balance -= total
    balance.total_sent += request.amount
    
    # 生成交易哈希
    tx_hash = generate_tx_hash(current_user.id, receiver.id, request.amount)
    
    # 创建转账记录
    transfer = TransferRecord(
        tx_hash=tx_hash,
        sender_id=current_user.id,
        receiver_id=receiver.id,
        currency=currency,
        amount=request.amount,
        fee=fee,
        note=request.note,
        status="confirmed"  # 模拟：立即确认
    )
    db.add(transfer)
    db.flush()  # 获取transfer.id
    
    # 增加接收者余额
    recv_balance = db.query(WalletBalance).filter(
        WalletBalance.user_id == receiver.id,
        WalletBalance.currency == currency
    ).first()
    
    if recv_balance:
        recv_balance.available_balance += request.amount
        recv_balance.total_received += request.amount
    else:
        recv_balance = WalletBalance(
            user_id=receiver.id,
            currency=currency,
            available_balance=request.amount,
            total_received=request.amount
        )
        db.add(recv_balance)
    
    # 创建通知 - 发送者
    create_notification(
        db, current_user.id, "transfer_sent",
        f"转账成功",
        f"已向 {receiver.username} 转账 {request.amount} {currency}",
        transfer.id
    )
    
    # 创建通知 - 接收者
    create_notification(
        db, receiver.id, "transfer_received",
        f"收到转账",
        f"收到 {current_user.username} 转账 {request.amount} {currency}" + (f" - {request.note}" if request.note else ""),
        transfer.id
    )
    
    db.commit()
    db.refresh(transfer)
    
    return transfer


@router.get("/transfers", response_model=List[TransferResponse])
async def get_my_transfers(
    type: str = Query("all", regex="^(all|sent|received)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取我的转账记录"""
    query = db.query(TransferRecord).filter(
        or_(
            TransferRecord.sender_id == current_user.id,
            TransferRecord.receiver_id == current_user.id
        )
    )
    
    if type == "sent":
        query = query.filter(TransferRecord.sender_id == current_user.id)
    elif type == "received":
        query = query.filter(TransferRecord.receiver_id == current_user.id)
    
    transfers = query.order_by(TransferRecord.created_at.desc()).limit(50).all()
    return transfers


@router.get("/transfers/{transfer_id}", response_model=TransferResponse)
async def get_transfer_detail(
    transfer_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取转账详情"""
    transfer = db.query(TransferRecord).filter(TransferRecord.id == transfer_id).first()
    
    if not transfer:
        raise HTTPException(status_code=404, detail="转账记录不存在")
    
    if transfer.sender_id != current_user.id and transfer.receiver_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权限查看此记录")
    
    return transfer


# ============================================
# 钱包通知
# ============================================

@router.get("/notifications", response_model=List[NotificationResponse])
async def get_wallet_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取钱包通知（到账提醒等）"""
    query = db.query(WalletNotification).filter(
        WalletNotification.user_id == current_user.id
    )
    
    if unread_only:
        query = query.filter(WalletNotification.is_read == False)
    
    notifications = query.order_by(WalletNotification.created_at.desc()).limit(50).all()
    return notifications


@router.post("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """标记通知为已读"""
    notification = db.query(WalletNotification).filter(
        WalletNotification.id == notification_id,
        WalletNotification.user_id == current_user.id
    ).first()
    
    if not notification:
        raise HTTPException(status_code=404, detail="通知不存在")
    
    notification.is_read = True
    db.commit()
    
    return {"message": "已标记为已读"}


@router.get("/notifications/unread-count")
async def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取未读通知数量"""
    count = db.query(WalletNotification).filter(
        WalletNotification.user_id == current_user.id,
        WalletNotification.is_read == False
    ).count()
    
    return {"unread_count": count}


# ============================================
# 充值地址（模拟）
# ============================================

@router.get("/deposit-address/{currency}", response_model=DepositAddressResponse)
async def get_deposit_address(
    currency: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取充值地址（平台生成模拟地址）"""
    currency = currency.upper()
    
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"不支持的币种: {currency}")
    
    # 查找或创建充值地址
    deposit = db.query(DepositAddress).filter(
        DepositAddress.user_id == current_user.id,
        DepositAddress.currency == currency
    ).first()
    
    if not deposit:
        # 生成模拟地址
        raw = f"{current_user.id}{currency}{datetime.now().isoformat()}"
        address = "0x" + hashlib.sha256(raw.encode()).hexdigest()[:40]
        
        deposit = DepositAddress(
            user_id=current_user.id,
            currency=currency,
            address=address,
            qr_code=None  # 简化：可后续添加QR码生成
        )
        db.add(deposit)
        db.commit()
        db.refresh(deposit)
    
    return DepositAddressResponse(
        currency=deposit.currency,
        address=deposit.address,
        qr_code=deposit.qr_code
    )


# ============================================
# 提现（模拟）
# ============================================

class WithdrawalRequestModel(BaseModel):
    currency: str
    amount: float
    to_address: str


@router.post("/withdraw")
async def withdraw_to_external(
    request: WithdrawalRequestModel,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """提现到外部钱包（模拟）"""
    currency = request.currency.upper()
    
    if currency not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=400, detail=f"不支持的币种: {currency}")
    
    # 获取余额
    balance = db.query(WalletBalance).filter(
        WalletBalance.user_id == current_user.id,
        WalletBalance.currency == currency
    ).first()
    
    if not balance or balance.available_balance < request.amount:
        raise HTTPException(status_code=400, detail="余额不足")
    
    # 检查是否有绑定该币种钱包
    wallet = db.query(UserWallet).filter(
        UserWallet.user_id == current_user.id,
        UserWallet.currency == currency
    ).first()
    
    if not wallet:
        raise HTTPException(status_code=400, detail=f"请先绑定 {currency} 钱包地址")
    
    fee = calculate_fee(request.amount, currency)
    net_amount = request.amount - fee
    
    # 扣除余额
    balance.available_balance -= request.amount
    
    # 创建提现记录
    withdrawal = WithdrawalRequest(
        user_id=current_user.id,
        wallet_id=wallet.id,
        currency=currency,
        amount=request.amount,
        fee=fee,
        net_amount=net_amount,
        status="completed"  # 模拟：立即完成
    )
    db.add(withdrawal)
    db.commit()
    db.refresh(withdrawal)
    
    return {
        "message": "提现成功",
        "tx_hash": generate_tx_hash(current_user.id, 0, request.amount),
        "amount": request.amount,
        "fee": fee,
        "net_amount": net_amount
    }


# ============================================
# 好友钱包快捷转账
# ============================================

@router.get("/friends", response_model=List[dict])
async def get_friends_with_balances(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取好友列表（带余额信息，方便快捷转账）"""
    friends = current_user.friends
    
    result = []
    for friend in friends:
        # 获取该好友的主要余额
        balance = db.query(WalletBalance).filter(
            WalletBalance.user_id == friend.id
        ).order_by(WalletBalance.id.desc()).first()
        
        result.append({
            "id": friend.id,
            "username": friend.username,
            "avatar": friend.avatar,
            "is_online": friend.is_online,
            "primary_balance": balance.currency if balance else None,
            "primary_amount": balance.available_balance if balance else 0
        })
    
    return result
