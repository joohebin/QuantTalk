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

friendships = Table(
    "friendships", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("friend_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("created_at", DateTime, server_default=func.now()),
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
    
    # 聊天样式设置
    bubble_bg_self = Column(String(20), default="#2d4a6f")      # 自己的气泡背景
    bubble_bg_other = Column(String(20), default="#21262d")    # 对方气泡背景
    bubble_text_color = Column(String(20), default="#e6edf3")  # 气泡字体颜色
    font_size = Column(String(10), default="medium")            # 字体大小: small/medium/large

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
    friends = relationship("User", secondary=friendships, primaryjoin=id == friendships.c.user_id,
                          secondaryjoin=id == friendships.c.friend_id, backref="friends_of")
    sent_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.from_user_id", cascade="all, delete-orphan")
    received_friend_requests = relationship("FriendRequest", foreign_keys="FriendRequest.to_user_id", cascade="all, delete-orphan")


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


class FriendRequest(Base):
    """好友申请表"""
    __tablename__ = "friend_requests"
    id = Column(Integer, primary_key=True, index=True)
    from_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    to_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    message = Column(String(500), default="")  # 申请附言
    status = Column(String(20), default="PENDING")  # PENDING / ACCEPTED / REJECTED
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    from_user = relationship("User", foreign_keys=[from_user_id])
    to_user = relationship("User", foreign_keys=[to_user_id])


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


# 支持的交易所列表（按地区分类）
# 地区: japan=日本, korea=韩国, hongkong=香港, singapore=新加坡, taiwan=台湾, 
#       seasia=东南亚, middleeast=中东, africa=非洲, euroamerica=欧美, oceania=大洋洲

SUPPORTED_EXCHANGES = {
    # ============ 欧美 (Europe & America) ============
    "coinbase": {
        "name": "Coinbase",
        "region": "euroamerica",
        "region_name": "欧美",
        "icon": "💰",
        "need_passphrase": False,
        "docs_url": "https://help.coinbase.com/en/exchange/managing-account/crypto-exchange-user-settings/api"
    },
    "kraken": {
        "name": "Kraken",
        "region": "euroamerica",
        "region_name": "欧美",
        "icon": "🦑",
        "need_passphrase": False,
        "docs_url": "https://www.kraken.com/features/api"
    },
    "gemini": {
        "name": "Gemini",
        "region": "euroamerica",
        "region_name": "欧美",
        "icon": "👯",
        "need_passphrase": False,
        "docs_url": "https://support.gemini.com/hc/en-us/articles/360031020532-API-Keys"
    },
    "etoro": {
        "name": "eToro",
        "region": "euroamerica",
        "region_name": "欧美",
        "icon": "📊",
        "need_passphrase": False,
        "docs_url": "https://www.etoro.com/customer-service/creator-terms/"
    },
    "bitstamp": {
        "name": "Bitstamp",
        "region": "euroamerica",
        "region_name": "欧美",
        "icon": "🏦",
        "need_passphrase": False,
        "docs_url": "https://www.bitstamp.net/api/"
    },
    "kucoin": {
        "name": "KuCoin",
        "region": "seasia",
        "region_name": "东南亚",
        "icon": "◇",
        "need_passphrase": True,
        "docs_url": "https://www.kucoin.com/zh-CN/account/api"
    },
    
    # ============ 亚洲 (Asia Pacific) ============
    "binance": {
        "name": "Binance",
        "region": "singapore",
        "region_name": "新加坡",
        "icon": "₿",
        "need_passphrase": False,
        "docs_url": "https://www.binance.com/zh-CN/support/faq/how-to-create-api-keys-on-binance-360002502072"
    },
    "okx": {
        "name": "OKX",
        "region": "singapore",
        "region_name": "新加坡",
        "icon": "○",
        "need_passphrase": True,
        "docs_url": "https://www.okx.com/zh-hans/account/my-api"
    },
    "bybit": {
        "name": "Bybit",
        "region": "singapore",
        "region_name": "新加坡",
        "icon": "◉",
        "need_passphrase": False,
        "docs_url": "https://www.bybit.com/zh-TW/help-center/bybit-default/my-assets/how-to-create-an-api-key"
    },
    "bitget": {
        "name": "Bitget",
        "region": "singapore",
        "region_name": "新加坡",
        "icon": "◎",
        "need_passphrase": True,
        "docs_url": "https://www.bitget.com/zh-TW/account/demo/api"
    },
    "gateio": {
        "name": "Gate.io",
        "region": "hongkong",
        "region_name": "香港",
        "icon": "▣",
        "need_passphrase": True,
        "docs_url": "https://www.gate.io/zh-tw/myapikey"
    },
    "htx": {
        "name": "HTX (火币)",
        "region": "hongkong",
        "region_name": "香港",
        "icon": "🔥",
        "need_passphrase": False,
        "docs_url": "https://www.htx.com/en-us/topApikey/"
    },
    "bitfinex": {
        "name": "Bitfinex",
        "region": "hongkong",
        "region_name": "香港",
        "icon": "⚡",
        "need_passphrase": False,
        "docs_url": "https://www.bitfinex.com/api"
    },
    
    # ============ 日本 (Japan) ============
    "bitflyer": {
        "name": "bitFlyer",
        "region": "japan",
        "region_name": "日本",
        "icon": "🦊",
        "need_passphrase": False,
        "docs_url": "https://bitflyer.com/en/apikey"
    },
    "coincheck": {
        "name": "Coincheck",
        "region": "japan",
        "region_name": "日本",
        "icon": "💴",
        "need_passphrase": False,
        "docs_url": "https://coincheck.com/zh_CN/api"
    },
    "liquid": {
        "name": "Liquid",
        "region": "japan",
        "region_name": "日本",
        "icon": "💧",
        "need_passphrase": False,
        "docs_url": "https://docs.liquid.com/"
    },
    "gmo": {
        "name": "GMO Coin",
        "region": "japan",
        "region_name": "日本",
        "icon": "🌐",
        "need_passphrase": False,
        "docs_url": "https://coin.z.com/jp/corporate/api/"
    },
    
    # ============ 韩国 (Korea) ============
    "upbit": {
        "name": "Upbit",
        "region": "korea",
        "region_name": "韩国",
        "icon": "🔺",
        "need_passphrase": False,
        "docs_url": "https://www.upbit.com/service-center/api_guide"
    },
    "bithumb": {
        "name": "Bithumb",
        "region": "korea",
        "region_name": "韩国",
        "icon": "💎",
        "need_passphrase": False,
        "docs_url": "https://www.bithumb.com/publicinfo/open-api/guide"
    },
    "korbit": {
        "name": "Korbit",
        "region": "korea",
        "region_name": "韩国",
        "icon": "🐻",
        "need_passphrase": False,
        "docs_url": "https://apidocs.korbit.co.kr/"
    },
    "coinone": {
        "name": "Coinone",
        "region": "korea",
        "region_name": "韩国",
        "icon": "🪙",
        "need_passphrase": False,
        "docs_url": "https://coinone.co.kr/open-api/"
    },
    
    # ============ 台湾 (Taiwan) ============
    "maicoin": {
        "name": "MaiCoin",
        "region": "taiwan",
        "region_name": "台湾",
        "icon": "🏮",
        "need_passphrase": False,
        "docs_url": "https://www.maicoin.com/zh-TW/api-docs"
    },
    "bitoex": {
        "name": "BitoEX 币托",
        "region": "taiwan",
        "region_name": "台湾",
        "icon": "🐷",
        "need_passphrase": False,
        "docs_url": "https://www.bitoex.com/cpage/api"
    },
    "ace": {
        "name": "ACE",
        "region": "taiwan",
        "region_name": "台湾",
        "icon": "⭐",
        "need_passphrase": False,
        "docs_url": "https://www.ace.io/"
    },
    
    # ============ 东南亚 (Southeast Asia) ============
    "mexc": {
        "name": "MEXC",
        "region": "seasia",
        "region_name": "东南亚",
        "icon": "◈",
        "need_passphrase": False,
        "docs_url": "https://www.mexc.com/zh-TW/apikey/"
    },
    "zipmex": {
        "name": "Zipmex",
        "region": "seasia",
        "region_name": "东南亚",
        "icon": "⚡",
        "need_passphrase": False,
        "docs_url": "https://api.zipmex.com/"
    },
    "tokocrypto": {
        "name": "Tokocrypto",
        "region": "seasia",
        "region_name": "东南亚",
        "icon": "🔮",
        "need_passphrase": False,
        "docs_url": "https://www.tokocrypto.com/en/support/sections/200550268-API"
    },
    
    # ============ 香港持牌 (Hong Kong Licensed) ============
    "hashkey": {
        "name": "HashKey",
        "region": "hongkong",
        "region_name": "香港",
        "icon": "🔑",
        "need_passphrase": False,
        "docs_url": "https://www.hashkey.com/api"
    },
    "osl": {
        "name": "OSL",
        "region": "hongkong",
        "region_name": "香港",
        "icon": "🏛️",
        "need_passphrase": False,
        "docs_url": "https://www.osl.com/api"
    },
    
    # ============ 中东 (Middle East) ============
    "rainoasis": {
        "name": "Rain",
        "region": "middleeast",
        "region_name": "中东",
        "icon": "🌧️",
        "need_passphrase": False,
        "docs_url": "https://raininfoapi.docs.apiary.io/"
    },
    "bitoasis": {
        "name": "BitOasis",
        "region": "middleeast",
        "region_name": "中东",
        "icon": "🌴",
        "need_passphrase": False,
        "docs_url": "https://docs.bitoasis.com/"
    },
    
    # ============ 非洲 (Africa) ============
    "luno": {
        "name": "Luno",
        "region": "africa",
        "region_name": "非洲",
        "icon": "🌙",
        "need_passphrase": False,
        "docs_url": "https://www.luno.com/en/api"
    },
    "yellowcard": {
        "name": "Yellow Card",
        "region": "africa",
        "region_name": "非洲",
        "icon": "🟡",
        "need_passphrase": False,
        "docs_url": "https://yellowcard.io/api"
    },
    
    # ============ 大洋洲 (Oceania) ============
    "cryptocom": {
        "name": "Crypto.com",
        "region": "oceania",
        "region_name": "大洋洲",
        "icon": "💳",
        "need_passphrase": False,
        "docs_url": "https://crypto.com/exchange/node_api"
    },
    "coinspot": {
        "name": "CoinSpot",
        "region": "oceania",
        "region_name": "大洋洲",
        "icon": "🥇",
        "need_passphrase": False,
        "docs_url": "https://www.coinspot.com.au/v2/api"
    },
    "easycrypto": {
        "name": "Easy Crypto",
        "region": "oceania",
        "region_name": "大洋洲",
        "icon": "🔄",
        "need_passphrase": False,
        "docs_url": "https://www.easycrypto.ai/api"
    },
    "btcmarkets": {
        "name": "BTC Markets",
        "region": "oceania",
        "region_name": "大洋洲",
        "icon": "🎯",
        "need_passphrase": False,
        "docs_url": "https://docs.btcmarkets.net/"
    },
}
