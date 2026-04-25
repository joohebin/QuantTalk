from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

follows = Table(
    "follows", Base.metadata,
    Column("follower_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("following_id", Integer, ForeignKey("users.id"), primary_key=True),
)

post_likes = Table(
    "post_likes", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("post_id", Integer, ForeignKey("posts.id"), primary_key=True),
)

community_members = Table(
    "community_members", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("community_id", Integer, ForeignKey("communities.id"), primary_key=True),
    Column("role", String(20), default="member"),
)

signal_likes = Table(
    "signal_likes", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("signal_id", Integer, ForeignKey("trading_signals.id"), primary_key=True),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    avatar = Column(String(500), default="")
    bio = Column(String(500), default="")
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, server_default=func.now())
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    posts = relationship("Post", back_populates="author", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="author", cascade="all, delete-orphan")
    notifications = relationship("Notification", foreign_keys="Notification.user_id", back_populates="user", cascade="all, delete-orphan")
    following = relationship("User", secondary=follows, primaryjoin=id == follows.c.follower_id,
                             secondaryjoin=id == follows.c.following_id, backref="followers")
    liked_posts = relationship("Post", secondary=post_likes, back_populates="likes")
    communities = relationship("Community", secondary=community_members, back_populates="members")
    sent_messages = relationship("PrivateMessage", foreign_keys="PrivateMessage.sender_id", back_populates="sender", cascade="all, delete-orphan")
    received_messages = relationship("PrivateMessage", foreign_keys="PrivateMessage.receiver_id", back_populates="receiver", cascade="all, delete-orphan")
    trading_signals = relationship("TradingSignal", back_populates="author", cascade="all, delete-orphan")
    portfolio_positions = relationship("PortfolioPosition", back_populates="user", cascade="all, delete-orphan")


class Post(Base):
    __tablename__ = "posts"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), default="")
    content = Column(Text, nullable=False)
    tags = Column(String(500), default="")
    image_url = Column(String(500), default="")
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    views = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    author = relationship("User", back_populates="posts")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")
    likes = relationship("User", secondary=post_likes, back_populates="liked_posts")


class Comment(Base):
    __tablename__ = "comments"
    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text, nullable=False)
    post_id = Column(Integer, ForeignKey("posts.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    post = relationship("Post", back_populates="comments")
    author = relationship("User", back_populates="comments")


class Notification(Base):
    __tablename__ = "notifications"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    type = Column(String(30), nullable=False)
    content = Column(String(500), nullable=False)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    post_id = Column(Integer, nullable=True)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")


class Community(Base):
    __tablename__ = "communities"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(String(500), default="")
    icon = Column(String(500), default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    channels = relationship("Channel", back_populates="community", cascade="all, delete-orphan")
    members = relationship("User", secondary=community_members, back_populates="communities")


class Channel(Base):
    __tablename__ = "channels"
    id = Column(Integer, primary_key=True, index=True)
    community_id = Column(Integer, ForeignKey("communities.id"), nullable=False)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(20), default="text")
    description = Column(String(300), default="")
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    community = relationship("Community", back_populates="channels")
    messages = relationship("ChannelMessage", back_populates="channel", cascade="all, delete-orphan")


class ChannelMessage(Base):
    __tablename__ = "channel_messages"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    channel = relationship("Channel", back_populates="messages")
    author = relationship("User")


class PrivateMessage(Base):
    """私信模型"""
    __tablename__ = "private_messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])


class TradingSignal(Base):
    """交易信号（QuantAI 交易广场）"""
    __tablename__ = "trading_signals"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # LONG / SHORT
    entry_price = Column(Float, nullable=False)
    stop_loss = Column(Float, nullable=True)
    take_profit = Column(Float, nullable=True)
    signal_type = Column(String(20), default="MANUAL")  # MANUAL / STRATEGY / AUTO / QUANTAI
    strategy_name = Column(String(100), default="")
    timeframe = Column(String(10), default="1h")
    notes = Column(Text, default="")
    tags = Column(String(500), default="")
    status = Column(String(20), default="ACTIVE")  # ACTIVE / CLOSED / CANCELLED
    pnl_pct = Column(Float, nullable=True)
    closed_at = Column(DateTime, nullable=True)
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    is_liked = Column(Boolean, default=False)
    source = Column(String(20), default="quanttalk")  # quanttalk / quantai
    created_at = Column(DateTime, server_default=func.now())

    author = relationship("User", back_populates="trading_signals")
    likes = relationship("User", secondary=signal_likes)
    comments = relationship("SignalComment", back_populates="signal", cascade="all, delete-orphan")


class SignalComment(Base):
    """信号评论"""
    __tablename__ = "signal_comments"
    id = Column(Integer, primary_key=True, index=True)
    signal_id = Column(Integer, ForeignKey("trading_signals.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    signal = relationship("TradingSignal", back_populates="comments")
    author = relationship("User")


class PortfolioPosition(Base):
    """持仓（QuantAI 同步）"""
    __tablename__ = "portfolio_positions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    quantity = Column(Float, nullable=False)
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=False)
    unrealized_pnl = Column(Float, default=0)
    unrealized_pnl_pct = Column(Float, default=0)
    source = Column(String(20), default="manual")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", back_populates="portfolio_positions")


class ExchangeConfig(Base):
    """用户交易所 API 配置"""
    __tablename__ = "exchange_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    exchange = Column(String(30), nullable=False)  # binance, okx, bybit, huobi, etc.
    api_key = Column(String(200), nullable=False)
    api_secret = Column(String(200), nullable=False)
    passphrase = Column(String(100), nullable=True)  # OKX/某些交易所需要
    label = Column(String(50), default="")  # 用户自定义标签
    is_enabled = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)  # 验证连接是否正常
    last_sync = Column(DateTime, nullable=True)  # 最后同步时间
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    user = relationship("User")


# 支持的交易所列表（静态配置）
SUPPORTED_EXCHANGES = {
    "binance": {
        "name": "Binance",
        "icon": "₿",
        "need_passphrase": False,
        "docs_url": "https://www.binance.com/zh-CN/support/faq/how-to-create-api-keys-on-binance-360002502072"
    },
    "okx": {
        "name": "OKX",
        "icon": "○",
        "need_passphrase": True,
        "docs_url": "https://www.okx.com/zh-hans/account/my-api"
    },
    "bybit": {
        "name": "Bybit",
        "icon": "◉",
        "need_passphrase": False,
        "docs_url": "https://www.bybit.com/zh-TW/help-center/bybit-default/my-assets/how-to-create-an-api-key"
    },
    "huobi": {
        "name": "Huobi",
        "icon": "◆",
        "need_passphrase": False,
        "docs_url": "https://www.huobi.com/zh-cn/apikey/"
    },
    "gateio": {
        "name": "Gate.io",
        "icon": "▣",
        "need_passphrase": True,
        "docs_url": "https://www.gate.io/zh-tw/myapikey"
    },
    "kucoin": {
        "name": "KuCoin",
        "icon": "◇",
        "need_passphrase": True,
        "docs_url": "https://www.kucoin.com/zh-CN/account/api"
    },
    "bitget": {
        "name": "Bitget",
        "icon": "◎",
        "need_passphrase": True,
        "docs_url": "https://www.bitget.com/zh-TW/account/demo/api"
    },
    "mexc": {
        "name": "MEXC",
        "icon": "◈",
        "need_passphrase": False,
        "docs_url": "https://www.mexc.com/zh-TW/apikey/"
    }
}
