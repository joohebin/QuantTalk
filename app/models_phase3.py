from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base

# ... 现有表格保持不变 ...

# ========== 第三阶段新增表格 ==========

# 持仓动态可见性设置
portfolio_visibility_settings = Table(
    "portfolio_visibility_settings", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("visibility", String(20), default="friends"),  # public / friends / private
)

# 持仓动态（第三阶段扩展）
class PortfolioUpdate(Base):
    """持仓动态 - 用于社区分享"""
    __tablename__ = "portfolio_updates"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # long / short
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, default=0)
    pnl_pct = Column(Float, default=0)
    notes = Column(Text, default="")
    tags = Column(String(200), default="")
    visibility = Column(String(20), default="public")  # public / friends / private
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    is_pinned = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User", foreign_keys=[user_id])
    likes = relationship("User", secondary="portfolio_update_likes")


class PortfolioUpdateLike(Base):
    """持仓动态点赞"""
    __tablename__ = "portfolio_update_likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    update_id = Column(Integer, ForeignKey("portfolio_updates.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class PortfolioUpdateComment(Base):
    """持仓动态评论"""
    __tablename__ = "portfolio_update_comments"
    id = Column(Integer, primary_key=True, index=True)
    update_id = Column(Integer, ForeignKey("portfolio_updates.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User")


# 行情异动提醒
class PriceAlert(Base):
    """行情异动提醒设置"""
    __tablename__ = "price_alerts"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    condition = Column(String(10), nullable=False)  # above / below / change_pct
    threshold = Column(Float, nullable=False)  # 触发阈值
    is_active = Column(Boolean, default=True)
    is_triggered = Column(Boolean, default=False)
    last_checked_price = Column(Float, nullable=True)
    notify_friends = Column(Boolean, default=False)  # 是否通知好友
    created_at = Column(DateTime, server_default=func.now())
    triggered_at = Column(DateTime, nullable=True)
    
    user = relationship("User", foreign_keys=[user_id])


# 跟单设置
class CopyTradeSettings(Base):
    """跟单设置 - 一键跟单"""
    __tablename__ = "copy_trade_settings"
    id = Column(Integer, primary_key=True, index=True)
    follower_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 跟单人
    leader_id = Column(Integer, ForeignKey("users.id"), nullable=False)  # 被跟单人
    symbols = Column(String(500), default="all")  # all 或逗号分隔的品种
    max_positions = Column(Integer, default=5)
    stop_loss_pct = Column(Float, nullable=True)  # 止损百分比
    take_profit_pct = Column(Float, nullable=True)  # 止盈百分比
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    follower = relationship("User", foreign_keys=[follower_id])
    leader = relationship("User", foreign_keys=[leader_id])


class CopyTradeRecord(Base):
    """跟单记录"""
    __tablename__ = "copy_trade_records"
    id = Column(Integer, primary_key=True, index=True)
    settings_id = Column(Integer, ForeignKey("copy_trade_settings.id"), nullable=False)
    leader_trade_id = Column(String(100), nullable=True)  # 关联的交易ID
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)
    leader_price = Column(Float, nullable=False)
    follower_price = Column(Float, nullable=False)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, nullable=True)
    pnl_pct = Column(Float, nullable=True)
    status = Column(String(20), default="pending")  # pending / filled / closed
    created_at = Column(DateTime, server_default=func.now())
    closed_at = Column(DateTime, nullable=True)
    
    settings = relationship("CopyTradeSettings")


# 策略分享
class Strategy(Base):
    """策略分享"""
    __tablename__ = "strategies"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    strategy_type = Column(String(50), default="manual")  # manual / automated / signal
    symbols = Column(String(200), default="")  # 逗号分隔
    timeframe = Column(String(20), default="1h")
    entry_conditions = Column(Text, default="")
    exit_conditions = Column(Text, default="")
    risk_management = Column(Text, default="")
    backtest_report_id = Column(Integer, ForeignKey("backtest_reports.id"), nullable=True)
    code_snippet = Column(Text, default="")  # 策略代码片段
    is_public = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    tags = Column(String(200), default="")
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    user = relationship("User")
    backtest_report = relationship("BacktestReport")
    likes = relationship("User", secondary="strategy_likes")


class StrategyLike(Base):
    """策略点赞"""
    __tablename__ = "strategy_likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class StrategyComment(Base):
    """策略评论"""
    __tablename__ = "strategy_comments"
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    
    user = relationship("User")


# 文字频道嵌入的K线消息
class ChannelKlineEmbed(Base):
    """频道K线嵌入"""
    __tablename__ = "channel_kline_embeds"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("channel_messages.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    period = Column(String(10), default="1h")
    created_at = Column(DateTime, server_default=func.now())


# 语音/视频频道交易直播
class LiveStream(Base):
    """交易直播"""
    __tablename__ = "live_streams"
    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(String(50), unique=True, nullable=False)
    host_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    host_username = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    stream_type = Column(String(20), default="trading")  # trading / analysis / review
    status = Column(String(20), default="live")  # live / ended
    current_symbol = Column(String(20), nullable=True)
    is_screen_sharing = Column(Boolean, default=False)
    screen_sharing_url = Column(String(500), nullable=True)
    viewer_count = Column(Integer, default=0)
    started_at = Column(DateTime, server_default=func.now())
    ended_at = Column(DateTime, nullable=True)
    
    host = relationship("User", foreign_keys=[host_id])


class LiveStreamViewer(Base):
    """直播观众"""
    __tablename__ = "live_stream_viewers"
    id = Column(Integer, primary_key=True, index=True)
    stream_id = Column(Integer, ForeignKey("live_streams.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    joined_at = Column(DateTime, server_default=func.now())
    
    stream = relationship("LiveStream")
    user = relationship("User")


# 信号订阅（订阅某人的信号推送）
class SignalSubscription(Base):
    """信号订阅"""
    __tablename__ = "signal_subscriptions"
    id = Column(Integer, primary_key=True, index=True)
    subscriber_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    publisher_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    symbols = Column(String(200), default="all")  # all 或逗号分隔的品种
    notify_immediately = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, server_default=func.now())
    
    subscriber = relationship("User", foreign_keys=[subscriber_id])
    publisher = relationship("User", foreign_keys=[publisher_id])


# 回测报告分享到社区
class ReportShare(Base):
    """回测报告分享"""
    __tablename__ = "report_shares"
    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("backtest_reports.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)  # 分享到的频道
    shared_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    message_id = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())
    
    report = relationship("BacktestReport")
    channel = relationship("Channel")
    sharer = relationship("User")
