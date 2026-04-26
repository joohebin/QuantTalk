"""
第五阶段：交易内容嵌入与体验升级
- 排行榜系统（交易高手/策略收益/社区活跃度）
- 成绩单功能（胜率/盈亏曲线/最大回撤）
- 内容嵌入（K线/行情/策略/收益曲线）
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from app.database import Base


# ========== 第五阶段新增表格 ==========

# 交易高手排行（每日快照）
class DailyTraderRanking(Base):
    """每日交易高手排行榜"""
    __tablename__ = "daily_trader_rankings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)  # YYYY-MM-DD
    period_type = Column(String(10), default="daily")  # daily / weekly / monthly
    total_pnl = Column(Float, default=0)  # 总盈亏
    total_pnl_pct = Column(Float, default=0)  # 总盈亏百分比
    win_rate = Column(Float, default=0)  # 胜率
    trade_count = Column(Integer, default=0)  # 交易次数
    sharpe_ratio = Column(Float, default=0)  # 夏普比率
    max_drawdown = Column(Float, default=0)  # 最大回撤
    ranking = Column(Integer, default=0)  # 当日排名
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


# 策略收益排行榜
class StrategyRanking(Base):
    """策略收益排行榜"""
    __tablename__ = "strategy_rankings"
    id = Column(Integer, primary_key=True, index=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=False)
    date = Column(String(10), nullable=False)
    period_type = Column(String(10), default="daily")
    total_return = Column(Float, default=0)  # 总收益
    total_return_pct = Column(Float, default=0)  # 收益百分比
    win_rate = Column(Float, default=0)
    sharpe_ratio = Column(Float, default=0)
    max_drawdown = Column(Float, default=0)
    ranking = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    strategy = relationship("Strategy")


# 社区活跃度排行榜
class CommunityActivityRanking(Base):
    """社区活跃度排行榜"""
    __tablename__ = "community_activity_rankings"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(String(10), nullable=False)
    period_type = Column(String(10), default="daily")
    activity_score = Column(Integer, default=0)  # 活跃度得分
    posts_count = Column(Integer, default=0)  # 发帖数
    comments_count = Column(Integer, default=0)  # 评论数
    signals_count = Column(Integer, default=0)  # 信号发布数
    strategies_count = Column(Integer, default=0)  # 策略发布数
    likes_received = Column(Integer, default=0)  # 获赞数
    ranking = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])


# 成绩单（交易记录生成的报告）
class ReportCard(Base):
    """交易成绩单"""
    __tablename__ = "report_cards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    period_start = Column(String(20), nullable=True)  # 报告周期开始
    period_end = Column(String(20), nullable=True)  # 报告周期结束
    exchange = Column(String(50), nullable=True)  # 交易所
    symbol = Column(String(20), nullable=True)  # 交易品种

    # 核心指标
    total_trades = Column(Integer, default=0)
    win_trades = Column(Integer, default=0)
    loss_trades = Column(Integer, default=0)
    win_rate = Column(Float, default=0)

    total_pnl = Column(Float, default=0)  # 总盈亏
    total_pnl_pct = Column(Float, default=0)  # 总盈亏百分比
    avg_win = Column(Float, default=0)  # 平均盈利
    avg_loss = Column(Float, default=0)  # 平均亏损
    profit_factor = Column(Float, default=0)  # 盈亏比

    max_drawdown = Column(Float, default=0)  # 最大回撤
    max_drawdown_pct = Column(Float, default=0)
    sharpe_ratio = Column(Float, default=0)  # 夏普比率

    # 图表数据（JSON格式存储）
    equity_curve = Column(JSON, default=list)  # 权益曲线数据
    drawdown_curve = Column(JSON, default=list)  # 回撤曲线数据
    monthly_returns = Column(JSON, default=list)  # 月度收益

    # 统计
    best_trade = Column(Float, default=0)  # 单笔最大盈利
    worst_trade = Column(Float, default=0)  # 单笔最大亏损
    consecutive_wins = Column(Integer, default=0)  # 最大连胜
    consecutive_losses = Column(Integer, default=0)  # 最大连亏

    is_public = Column(Boolean, default=True)
    likes_count = Column(Integer, default=0)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    likes = relationship("User", secondary="report_card_likes")


class ReportCardLike(Base):
    """成绩单点赞"""
    __tablename__ = "report_card_likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    report_card_id = Column(Integer, ForeignKey("report_cards.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class ReportCardComment(Base):
    """成绩单评论"""
    __tablename__ = "report_card_comments"
    id = Column(Integer, primary_key=True, index=True)
    report_card_id = Column(Integer, ForeignKey("report_cards.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")


# 频道嵌入内容类型
class EmbedType:
    KLINE = "kline"  # K线图表
    QUOTE = "quote"  # 实时行情
    STRATEGY = "strategy"  # 策略信息
    REPORT = "report"  # 回测报告
    REPORT_CARD = "report_card"  # 成绩单
    PROFIT_CURVE = "profit_curve"  # 收益曲线
    POSITION = "position"  # 持仓展示
    ALERT = "alert"  # 行情提醒
    SIGNAL = "signal"  # 交易信号


# 频道嵌入消息
class ChannelEmbed(Base):
    """频道嵌入内容"""
    __tablename__ = "channel_embeds"
    id = Column(Integer, primary_key=True, index=True)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=False)
    message_id = Column(Integer, ForeignKey("channel_messages.id"), nullable=True)
    embed_type = Column(String(20), nullable=False)  # kline/quote/strategy/report/profit_curve
    title = Column(String(200), nullable=True)  # 嵌入标题
    content = Column(JSON, default=dict)  # 嵌入内容（JSON格式）
    symbol = Column(String(20), nullable=True)  # 关联的品种
    period = Column(String(10), default="1h")  # K线周期
    created_at = Column(DateTime, server_default=func.now())
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    channel = relationship("Channel")
    creator = relationship("User", foreign_keys=[created_by])


# 行情异动记录（用于推送）
class PriceMovement(Base):
    """行情异动记录"""
    __tablename__ = "price_movements"
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(20), nullable=False)
    exchange = Column(String(50), nullable=False)
    category = Column(String(20), default="crypto")  # crypto/stock/forex
    price_before = Column(Float, nullable=False)
    price_after = Column(Float, nullable=False)
    change_pct = Column(Float, nullable=False)  # 涨跌幅
    change_type = Column(String(10), nullable=False)  # rise/fall
    volume_ratio = Column(Float, default=0)  # 量比
    is_notified = Column(Boolean, default=False)
    created_at = Column(DateTime, server_default=func.now())

    class ChangeType:
        RISE = "rise"
        FALL = "fall"
        VOLUME = "volume"  # 异常放量


# 持仓展示分享
class PositionShare(Base):
    """持仓展示分享"""
    __tablename__ = "position_shares"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    channel_id = Column(Integer, ForeignKey("channels.id"), nullable=True)
    symbol = Column(String(20), nullable=False)
    direction = Column(String(10), nullable=False)  # long/short
    entry_price = Column(Float, nullable=False)
    current_price = Column(Float, nullable=True)
    quantity = Column(Float, nullable=False)
    pnl = Column(Float, default=0)
    pnl_pct = Column(Float, default=0)
    notes = Column(Text, default="")
    image_url = Column(String(500), nullable=True)  # 持仓截图URL
    visibility = Column(String(20), default="public")  # public/friends/private
    likes_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User", foreign_keys=[user_id])
    channel = relationship("Channel")
    likes = relationship("User", secondary="position_share_likes")


class PositionShareLike(Base):
    """持仓分享点赞"""
    __tablename__ = "position_share_likes"
    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    share_id = Column(Integer, ForeignKey("position_shares.id"), primary_key=True)
    created_at = Column(DateTime, server_default=func.now())


class PositionShareComment(Base):
    """持仓分享评论"""
    __tablename__ = "position_share_comments"
    id = Column(Integer, primary_key=True, index=True)
    share_id = Column(Integer, ForeignKey("position_shares.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    user = relationship("User")
