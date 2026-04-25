"""
第四阶段：加密货币钱包和好友转账功能
包含：钱包绑定、余额管理、转账交易
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base
import enum


# ============================================
# 加密货币枚举
# ============================================
class CryptoCurrency(str, enum.Enum):
    BTC = "BTC"
    ETH = "ETH"
    USDT = "USDT"
    USDC = "USDC"
    BNB = "BNB"


# ============================================
# 用户钱包表
# ============================================
class UserWallet(Base):
    """用户绑定的加密货币钱包"""
    __tablename__ = "user_wallets"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)  # BTC/ETH/USDT等
    address = Column(String(255), nullable=False)  # 钱包地址（仅存储公开地址）
    label = Column(String(100), default="")  # 钱包标签，如"主钱包"、"冷钱包"
    is_primary = Column(Boolean, default=False)  # 是否为主钱包
    is_verified = Column(Boolean, default=False)  # 是否已验证（小额验证）
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="wallets")
    withdrawal_requests = relationship("WithdrawalRequest", back_populates="wallet")

    def __repr__(self):
        return f"<UserWallet {self.currency}:{self.address[:10]}...>"


# ============================================
# 钱包余额表（模拟余额）
# ============================================
class WalletBalance(Base):
    """用户的模拟钱包余额"""
    __tablename__ = "wallet_balances"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    available_balance = Column(Float, default=0.0)  # 可用余额
    locked_balance = Column(Float, default=0.0)  # 锁定余额（挂单/转账中）
    total_received = Column(Float, default=0.0)  # 历史总收入
    total_sent = Column(Float, default=0.0)  # 历史总发送
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User", back_populates="wallet_balances")

    def __repr__(self):
        return f"<WalletBalance {self.currency}: {self.available_balance}>"


# ============================================
# 转账记录表
# ============================================
class TransferRecord(Base):
    """好友/用户间转账记录"""
    __tablename__ = "transfer_records"

    id = Column(Integer, primary_key=True, index=True)
    tx_hash = Column(String(128), unique=True, index=True)  # 交易哈希（模拟）
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)  # 手续费
    note = Column(Text, default="")  # 转账备注
    status = Column(String(20), default="pending")  # pending/confirmed/failed
    created_at = Column(DateTime, server_default=func.now())
    confirmed_at = Column(DateTime, nullable=True)

    sender = relationship("User", foreign_keys=[sender_id], back_populates="sent_transfers")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="received_transfers")
    notifications = relationship("WalletNotification", back_populates="transfer")

    def __repr__(self):
        return f"<Transfer {self.currency} {self.amount} {self.status}>"


# ============================================
# 钱包通知表
# ============================================
class WalletNotification(Base):
    """钱包相关通知（到账提醒等）"""
    __tablename__ = "wallet_notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)  # transfer_received/transfer_sent/confirmation
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    related_transfer_id = Column(Integer, ForeignKey("transfer_records.id"), nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="wallet_notifications")
    transfer = relationship("TransferRecord", back_populates="notifications")

    def __repr__(self):
        return f"<WalletNotification {self.notification_type}: {self.title}>"


# ============================================
# 提现请求表
# ============================================
class WithdrawalRequest(Base):
    """提现到外部钱包请求"""
    __tablename__ = "withdrawal_requests"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    wallet_id = Column(Integer, ForeignKey("user_wallets.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Float, nullable=False)
    fee = Column(Float, default=0.0)
    net_amount = Column(Float, nullable=False)  # 到账金额
    status = Column(String(20), default="pending")  # pending/processing/completed/failed
    tx_hash = Column(String(128), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    processed_at = Column(DateTime, nullable=True)

    user = relationship("User", back_populates="withdrawal_requests")
    wallet = relationship("UserWallet")

    def __repr__(self):
        return f"<Withdrawal {self.currency} {self.amount} {self.status}>"


# ============================================
# 充值地址表（平台生成）
# ============================================
class DepositAddress(Base):
    """用户充值地址（平台为用户生成的地址）"""
    __tablename__ = "deposit_addresses"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    currency = Column(String(10), nullable=False)
    address = Column(String(255), nullable=False, unique=True)
    qr_code = Column(Text, nullable=True)  # Base64 QR码
    is_used = Column(Boolean, default=False)
    total_deposited = Column(Float, default=0.0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="deposit_addresses")

    def __repr__(self):
        return f"<DepositAddress {self.currency}: {self.address[:10]}...>"


# ============================================
# 关联关系 - User模型需要添加这些
# ============================================
def add_user_relationships():
    """需要在User模型中添加的关联"""
    return [
        "wallets = relationship('UserWallet', back_populates='user', cascade='all, delete-orphan')",
        "wallet_balances = relationship('WalletBalance', back_populates='user', cascade='all, delete-orphan')",
        "sent_transfers = relationship('TransferRecord', foreign_keys='TransferRecord.sender_id', back_populates='sender')",
        "received_transfers = relationship('TransferRecord', foreign_keys='TransferRecord.receiver_id', back_populates='receiver')",
        "wallet_notifications = relationship('WalletNotification', back_populates='user', cascade='all, delete-orphan')",
        "withdrawal_requests = relationship('WithdrawalRequest', back_populates='user')",
        "deposit_addresses = relationship('DepositAddress', back_populates='user', cascade='all, delete-orphan')",
    ]
