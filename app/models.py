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

# Discord风格服务器成员关系表
guild_members = Table(
    "guild_members", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("guild_id", Integer, ForeignKey("guilds.id"), primary_key=True),
    Column("nickname", String(50), default=""),
    Column("role", String(20), default="member"),  # owner/admin/moderator/member
    Column("joined_at", DateTime, server_default=func.now()),
)

# 语音频道在线成员
voice_members = Table(
    "voice_members", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("voice_channel_id", Integer, ForeignKey("voice_channels.id"), primary_key=True),
    Column("joined_at", DateTime, server_default=func.now()),
)


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    phone = Column(String(20), nullable=True)  # 国际手机号
    email = Column(String(120), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    wallet_address = Column(String(100), nullable=True)  # 钱包地址
    wallet_type = Column(String(20), nullable=True)  # 钱包类型 (MetaMask/Trust/TP/Coinbase)
    avatar = Column(String(500), default="")
    bio = Column(String(500), default="")
    is_online = Column(Boolean, default=False)
    last_seen = Column(DateTime, server_default=func.now())
    is_verified = Column(Boolean, default=False)
    follower_count = Column(Integer, default=0)  # 粉丝数
    following_count = Column(Integer, default=0)  # 关注数
    metaapi_token = Column(String(255), nullable=True)  # MetaApi授权Token
    status = Column(Integer, default=0)  # 在线状态 (0-离线，1-在线，2-忙碌)
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
    guilds = relationship("Guild", secondary=guild_members, back_populates="members")
    
    # 第四阶段：钱包和转账
    wallets = relationship("UserWallet", back_populates="user", cascade="all, delete-orphan")
    wallet_balances = relationship("WalletBalance", back_populates="user", cascade="all, delete-orphan")
    sent_transfers = relationship("TransferRecord", foreign_keys="TransferRecord.sender_id", back_populates="sender")
    received_transfers = relationship("TransferRecord", foreign_keys="TransferRecord.receiver_id", back_populates="receiver")
    wallet_notifications = relationship("WalletNotification", back_populates="user", cascade="all, delete-orphan")
    withdrawal_requests = relationship("WithdrawalRequest", back_populates="user")
    deposit_addresses = relationship("DepositAddress", back_populates="user", cascade="all, delete-orphan")


class VerificationCode(Base):
    """邮箱验证码"""
    __tablename__ = "verification_codes"
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(120), index=True, nullable=False)
    code = Column(String(6), nullable=False)  # 6位验证码
    purpose = Column(String(20), nullable=False)  # register/login/reset_password
    expires_at = Column(DateTime, nullable=False)  # 过期时间
    used = Column(Boolean, default=False)  # 是否已使用
    created_at = Column(DateTime, server_default=func.now())


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
    msg_type = Column(String(20), default="text")  # text, image, file, quote, chart
    media_url = Column(String(500), nullable=True)  # 图片/文件URL
    reply_to = Column(Integer, nullable=True)  # 回复的消息ID
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


class FollowTrade(Base):
    """跟单表 - 按文档新增"""
    __tablename__ = "follow_trades"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 跟单用户
    trader_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 被跟单交易员
    variety = Column(String(50), nullable=False)  # 跟单品种
    follow_amount = Column(Float, nullable=False)  # 跟单金额
    stop_profit = Column(Float)  # 止盈价格
    stop_loss = Column(Float)  # 止损价格
    status = Column(Integer, default=1)  # 跟单状态 (1-跟单中，0-已停止，2-已平仓)
    profit = Column(Float, default=0)  # 跟单收益
    create_time = Column(DateTime, server_default=func.now())
    end_time = Column(DateTime)  # 跟单结束时间

    follower = relationship("User", foreign_keys=[follower_id])
    trader = relationship("User", foreign_keys=[trader_id])


class MetaApiConfig(Base):
    """MetaApi关联表 - 按文档新增"""
    __tablename__ = "metaapi_configs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    metaapi_token = Column(String(255), nullable=False)
    account_id = Column(String(100), nullable=False)
    platform = Column(String(20), nullable=False)  # MT4/MT5
    status = Column(Boolean, default=True)  # 对接状态
    last_sync_time = Column(DateTime)  # 最后同步时间
    create_time = Column(DateTime, server_default=func.now())

    user = relationship("User")


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


class VideoRoom(Base):
    """视频通话房间"""
    __tablename__ = "video_rooms"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(50), unique=True, nullable=False, index=True)
    host_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    host_username = Column(String(50), nullable=False)
    room_type = Column(String(20), default="video")  # video / audio / live
    max_participants = Column(Integer, default=10)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)


class Guild(Base):
    """Discord风格的服务器"""
    __tablename__ = "guilds"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    icon = Column(String(500), default="")
    description = Column(String(500), default="")
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invite_code = Column(String(20), unique=True, nullable=True)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User", foreign_keys=[owner_id])
    members = relationship("User", secondary=guild_members, back_populates="guilds")
    text_channels = relationship("TextChannel", back_populates="guild", cascade="all, delete-orphan")
    voice_channels = relationship("VoiceChannel", back_populates="guild", cascade="all, delete-orphan")


class TextChannel(Base):
    """文字频道"""
    __tablename__ = "text_channels"
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    name = Column(String(100), nullable=False)
    topic = Column(String(300), default="")
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    guild = relationship("Guild", back_populates="text_channels")
    messages = relationship("GuildMessage", back_populates="channel", cascade="all, delete-orphan")


class GuildMessage(Base):
    """服务器消息"""
    __tablename__ = "guild_messages"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("text_channels.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    channel = relationship("TextChannel", back_populates="messages")
    author = relationship("User")


class VoiceChannel(Base):
    """语音/视频频道"""
    __tablename__ = "voice_channels"
    id = Column(Integer, primary_key=True, index=True)
    guild_id = Column(Integer, ForeignKey("guilds.id"), nullable=False)
    name = Column(String(100), nullable=False)
    channel_type = Column(String(20), default="voice")  # voice / video / stage
    bitrate = Column(Integer, default=64000)
    user_limit = Column(Integer, default=0)  # 0表示无限制
    position = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    guild = relationship("Guild", back_populates="voice_channels")
    online_members = relationship("User", secondary=voice_members)


# ========== 群聊系统 ==========

class Group(Base):
    """群组"""
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    avatar = Column(String(500), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    invite_code = Column(String(20), nullable=False, unique=True)
    is_private = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    owner = relationship("User")
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    messages = relationship("GroupMessage", back_populates="group", cascade="all, delete-orphan")


class GroupMember(Base):
    """群组成员"""
    __tablename__ = "group_members"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_owner = Column(Boolean, default=False)
    is_admin = Column(Boolean, default=False)
    is_muted = Column(Boolean, default=False)  # 禁言状态
    muted_until = Column(DateTime, nullable=True)  # 禁言截止时间
    joined_at = Column(DateTime, server_default=func.now())

    group = relationship("Group", back_populates="members")
    user = relationship("User")


class GroupMessage(Base):
    """群消息"""
    __tablename__ = "group_messages"
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    author_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    reply_to = Column(Integer, ForeignKey("group_messages.id"), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    group = relationship("Group", back_populates="messages")
    author = relationship("User")


# ========== 成绩单系统 ==========

class TradeRecord(Base):
    """交易记录"""
    __tablename__ = "trade_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False, index=True)
    direction = Column(String(10), nullable=False)  # long / short
    entry_price = Column(Float, nullable=False)
    exit_price = Column(Float, nullable=True)
    entry_time = Column(DateTime, nullable=False)
    exit_time = Column(DateTime, nullable=True)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)  # 盈亏金额
    pnl_pct = Column(Float, nullable=True)  # 盈亏百分比
    strategy_name = Column(String(100), default="")
    notes = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")


class BacktestReport(Base):
    """回测报告"""
    __tablename__ = "backtest_reports"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200), nullable=False)
    strategy_name = Column(String(100), nullable=False)
    symbol = Column(String(20), nullable=False)
    period = Column(String(10), nullable=False)  # 1m, 5m, 15m, 1h, 4h, 1d
    start_date = Column(String(20), nullable=False)
    end_date = Column(String(20), nullable=False)
    total_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)  # 胜率 %
    profit_factor = Column(Float, default=0)  # 盈亏比
    max_drawdown = Column(Float, default=0)  # 最大回撤 %
    sharpe_ratio = Column(Float, nullable=True)
    total_return = Column(Float, default=0)  # 总收益率 %
    annualized_return = Column(Float, nullable=True)
    equity_curve = Column(Text, nullable=True)  # JSON
    trades_summary = Column(Text, nullable=True)  # JSON
    chart_data = Column(Text, nullable=True)  # JSON
    notes = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
    likes = relationship("User", secondary="backtest_likes")


class BacktestLike(Base):
    """回测报告点赞"""
    __tablename__ = "backtest_likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    report_id = Column(Integer, ForeignKey("backtest_reports.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


# ========== 社交关系系统 ==========

class UserFollow(Base):
    """用户关注关系"""
    __tablename__ = "user_follows"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    following_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    follower = relationship("User", foreign_keys=[follower_id])
    following = relationship("User", foreign_keys=[following_id])


class Favorite(Base):
    """用户收藏"""
    __tablename__ = "favorites"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_type = Column(String(20), nullable=False)  # signal, strategy, post, chart
    item_id = Column(Integer, nullable=False)
    title = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User")


class ShareRecord(Base):
    """分享记录"""
    __tablename__ = "share_records"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    item_type = Column(String(20), nullable=False)  # signal, strategy, post
    item_id = Column(Integer, nullable=False)
    target_type = Column(String(20), nullable=False)  # community, friends
    content = Column(Text, default="")
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User")
