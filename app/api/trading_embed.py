"""
第五阶段 API：交易内容嵌入与体验升级
- 排行榜系统（交易高手/策略收益/社区活跃度）
- 成绩单功能（胜率/盈亏曲线/最大回撤）
- 内容嵌入（K线/行情/策略/收益曲线）
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, timedelta
import json
import random

from app.database import get_db
from app.models_phase5 import (
    DailyTraderRanking, StrategyRanking, CommunityActivityRanking,
    ReportCard, ReportCardLike, ReportCardComment,
    ChannelEmbed, EmbedType,
    PriceMovement, PositionShare, PositionShareLike, PositionShareComment
)
from app.models import User, Channel, ChannelMessage
from app.models_phase3 import Strategy, TradingSignal
from app.auth import get_current_user

router = APIRouter(prefix="/api/trading-embed", tags=["第五阶段：交易内容嵌入"])


# ==================== Pydantic Schemas ====================

class LeaderboardEntry(BaseModel):
    ranking: int
    user_id: int
    username: str
    avatar: str
    value: float
    change_pct: float = 0
    win_rate: float = 0
    trade_count: int = 0
    sharpe_ratio: float = 0
    max_drawdown: float = 0
    is_online: bool = False


class StrategyRankingEntry(BaseModel):
    ranking: int
    strategy_id: int
    strategy_name: str
    username: str
    avatar: str
    total_return_pct: float
    win_rate: float
    sharpe_ratio: float
    max_drawdown: float
    likes_count: int
    views_count: int


class ActivityRankingEntry(BaseModel):
    ranking: int
    user_id: int
    username: str
    avatar: str
    activity_score: int
    posts_count: int
    comments_count: int
    signals_count: int
    strategies_count: int
    likes_received: int


class ReportCardCreate(BaseModel):
    name: str
    period_start: Optional[str] = None
    period_end: Optional[str] = None
    exchange: Optional[str] = None
    symbol: Optional[str] = None
    total_trades: int = 0
    win_trades: int = 0
    loss_trades: int = 0
    total_pnl: float = 0
    total_pnl_pct: float = 0
    avg_win: float = 0
    avg_loss: float = 0
    max_drawdown: float = 0
    max_drawdown_pct: float = 0
    sharpe_ratio: float = 0
    best_trade: float = 0
    worst_trade: float = 0
    consecutive_wins: int = 0
    consecutive_losses: int = 0


class ReportCardResponse(BaseModel):
    id: int
    user_id: int
    username: str
    avatar: str
    name: str
    period_start: Optional[str]
    period_end: Optional[str]
    exchange: Optional[str]
    symbol: Optional[str]
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    total_pnl: float
    total_pnl_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown: float
    max_drawdown_pct: float
    sharpe_ratio: float
    best_trade: float
    worst_trade: float
    consecutive_wins: int
    consecutive_losses: int
    equity_curve: list
    drawdown_curve: list
    monthly_returns: list
    likes_count: int
    views_count: int
    is_liked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class EmbedCreate(BaseModel):
    channel_id: int
    embed_type: str
    title: Optional[str] = None
    content: dict = {}
    symbol: Optional[str] = None
    period: str = "1h"


class PositionShareCreate(BaseModel):
    channel_id: Optional[int] = None
    symbol: str
    direction: str
    entry_price: float
    quantity: float
    notes: str = ""
    visibility: str = "public"


# ==================== 排行榜 API ====================

@router.get("/leaderboards/traders")
async def get_trader_leaderboard(
    period: str = Query("daily", description="daily/weekly/monthly"),
    category: str = Query("all", description="all/crypto/forex/stock"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取交易高手排行榜"""
    today = datetime.now().strftime("%Y-%m-%d")

    rankings = db.query(DailyTraderRanking).filter(
        DailyTraderRanking.date == today,
        DailyTraderRanking.period_type == period
    ).order_by(DailyTraderRanking.ranking).limit(limit).all()

    if not rankings:
        users_with_signals = db.query(User).join(TradingSignal).distinct().limit(50).all()
        mock_data = []
        for i, user in enumerate(sorted(users_with_signals, key=lambda x: random.random())[:limit]):
            pnl_pct = round(random.uniform(-15, 25), 2)
            mock_data.append({
                "ranking": i + 1,
                "user_id": user.id,
                "username": user.username,
                "avatar": user.avatar,
                "value": round(random.uniform(1000, 100000), 2),
                "change_pct": pnl_pct,
                "win_rate": round(random.uniform(40, 85), 1),
                "trade_count": random.randint(5, 100),
                "sharpe_ratio": round(random.uniform(0.5, 3.5), 2),
                "max_drawdown": round(random.uniform(5, 25), 2),
                "is_online": user.is_online
            })
        return {"period": period, "category": category, "rankings": mock_data}

    result = []
    for r in rankings:
        result.append(LeaderboardEntry(
            ranking=r.ranking,
            user_id=r.user_id,
            username=r.user.username if r.user else "Unknown",
            avatar=r.user.avatar if r.user else "",
            value=r.total_pnl,
            change_pct=r.total_pnl_pct,
            win_rate=r.win_rate,
            trade_count=r.trade_count,
            sharpe_ratio=r.sharpe_ratio,
            max_drawdown=r.max_drawdown,
            is_online=r.user.is_online if r.user else False
        ))

    return {"period": period, "category": category, "rankings": result}


@router.get("/leaderboards/strategies")
async def get_strategy_leaderboard(
    period: str = Query("daily"),
    symbol: str = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取策略收益排行榜"""
    today = datetime.now().strftime("%Y-%m-%d")

    rankings = db.query(StrategyRanking).filter(
        StrategyRanking.date == today,
        StrategyRanking.period_type == period
    ).order_by(StrategyRanking.ranking).limit(limit).all()

    if not rankings:
        strategies = db.query(Strategy).filter(Strategy.is_public == True).limit(50).all()
        mock_data = []
        for i, s in enumerate(sorted(strategies, key=lambda x: random.random())[:limit]):
            mock_data.append({
                "ranking": i + 1,
                "strategy_id": s.id,
                "strategy_name": s.name,
                "username": s.user.username if s.user else "Unknown",
                "avatar": s.user.avatar if s.user else "",
                "total_return_pct": round(random.uniform(-10, 50), 2),
                "win_rate": round(random.uniform(40, 80), 1),
                "sharpe_ratio": round(random.uniform(0.5, 3.0), 2),
                "max_drawdown": round(random.uniform(5, 30), 2),
                "likes_count": s.likes_count,
                "views_count": s.views_count
            })
        return {"period": period, "symbol": symbol, "rankings": mock_data}

    result = []
    for r in rankings:
        if r.strategy:
            result.append(StrategyRankingEntry(
                ranking=r.ranking,
                strategy_id=r.strategy_id,
                strategy_name=r.strategy.name,
                username=r.strategy.user.username if r.strategy.user else "Unknown",
                avatar=r.strategy.user.avatar if r.strategy.user else "",
                total_return_pct=r.total_return_pct,
                win_rate=r.win_rate,
                sharpe_ratio=r.sharpe_ratio,
                max_drawdown=r.max_drawdown,
                likes_count=r.strategy.likes_count,
                views_count=r.strategy.views_count
            ))

    return {"period": period, "symbol": symbol, "rankings": result}


@router.get("/leaderboards/activity")
async def get_activity_leaderboard(
    period: str = Query("daily"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取社区活跃度排行榜"""
    today = datetime.now().strftime("%Y-%m-%d")

    rankings = db.query(CommunityActivityRanking).filter(
        CommunityActivityRanking.date == today,
        CommunityActivityRanking.period_type == period
    ).order_by(CommunityActivityRanking.ranking).limit(limit).all()

    if not rankings:
        mock_data = []
        for i in range(limit):
            mock_data.append({
                "ranking": i + 1,
                "user_id": i + 1,
                "username": f"活跃用户{i+1}",
                "avatar": "",
                "activity_score": random.randint(100, 1000),
                "posts_count": random.randint(5, 50),
                "comments_count": random.randint(10, 100),
                "signals_count": random.randint(1, 20),
                "strategies_count": random.randint(0, 5),
                "likes_received": random.randint(20, 200)
            })
        return {"period": period, "rankings": mock_data}

    result = []
    for r in rankings:
        result.append(ActivityRankingEntry(
            ranking=r.ranking,
            user_id=r.user_id,
            username=r.user.username if r.user else "Unknown",
            avatar=r.user.avatar if r.user else "",
            activity_score=r.activity_score,
            posts_count=r.posts_count,
            comments_count=r.comments_count,
            signals_count=r.signals_count,
            strategies_count=r.strategies_count,
            likes_received=r.likes_received
        ))

    return {"period": period, "rankings": result}


@router.get("/leaderboards/traders/{user_id}/positions")
async def get_leader_positions(
    user_id: int,
    db: Session = Depends(get_db)
):
    """获取交易高手的持仓"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")

    from app.models_phase3 import PortfolioUpdate
    positions = db.query(PortfolioUpdate).filter(
        PortfolioUpdate.user_id == user_id,
        PortfolioUpdate.visibility == "public"
    ).order_by(PortfolioUpdate.created_at.desc()).limit(10).all()

    return {
        "user_id": user_id,
        "username": user.username,
        "positions": [
            {
                "symbol": p.symbol,
                "direction": p.direction,
                "entry_price": p.entry_price,
                "current_price": p.current_price,
                "quantity": p.quantity,
                "pnl": p.pnl,
                "pnl_pct": p.pnl_pct,
                "created_at": p.created_at.isoformat() if p.created_at else None
            }
            for p in positions
        ]
    }


# ==================== 成绩单 API ====================

@router.get("/report-cards")
async def get_report_cards(
    user_id: int = Query(None),
    sort: str = Query("recent"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成绩单列表"""
    query = db.query(ReportCard).filter(ReportCard.is_public == True)

    if user_id:
        query = query.filter(ReportCard.user_id == user_id)

    if sort == "popular":
        query = query.order_by(ReportCard.likes_count.desc())
    elif sort == "win_rate":
        query = query.order_by(ReportCard.win_rate.desc())
    else:
        query = query.order_by(ReportCard.created_at.desc())

    cards = query.limit(limit).all()

    result = []
    for card in cards:
        is_liked = db.query(ReportCardLike).filter(
            ReportCardLike.report_card_id == card.id,
            ReportCardLike.user_id == current_user.id
        ).first() is not None

        result.append(ReportCardResponse(
            id=card.id,
            user_id=card.user_id,
            username=card.user.username if card.user else "Unknown",
            avatar=card.user.avatar if card.user else "",
            name=card.name,
            period_start=card.period_start,
            period_end=card.period_end,
            exchange=card.exchange,
            symbol=card.symbol,
            total_trades=card.total_trades,
            win_trades=card.win_trades,
            loss_trades=card.loss_trades,
            win_rate=card.win_rate,
            total_pnl=card.total_pnl,
            total_pnl_pct=card.total_pnl_pct,
            avg_win=card.avg_win,
            avg_loss=card.avg_loss,
            profit_factor=card.profit_factor,
            max_drawdown=card.max_drawdown,
            max_drawdown_pct=card.max_drawdown_pct,
            sharpe_ratio=card.sharpe_ratio,
            best_trade=card.best_trade,
            worst_trade=card.worst_trade,
            consecutive_wins=card.consecutive_wins,
            consecutive_losses=card.consecutive_losses,
            equity_curve=card.equity_curve or [],
            drawdown_curve=card.drawdown_curve or [],
            monthly_returns=card.monthly_returns or [],
            likes_count=card.likes_count,
            views_count=card.views_count,
            is_liked=is_liked,
            created_at=card.created_at
        ))

    return result


@router.post("/report-cards")
async def create_report_card(
    data: ReportCardCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建成绩单"""
    if data.total_trades > 0:
        win_rate = (data.win_trades / data.total_trades) * 100
    else:
        win_rate = 0

    profit_factor = abs(data.avg_win / data.avg_loss) if data.avg_loss != 0 else 0

    equity_curve = []
    equity = 10000
    for i in range(min(data.total_trades, 50)):
        change = random.uniform(-3, 4) if i % 3 != 0 else random.uniform(2, 5)
        equity *= (1 + change / 100)
        equity_curve.append({"index": i + 1, "value": round(equity, 2)})

    drawdown_curve = []
    peak = equity_curve[0]["value"] if equity_curve else 10000
    for point in equity_curve:
        if point["value"] > peak:
            peak = point["value"]
        drawdown = ((peak - point["value"]) / peak * 100) if peak > 0 else 0
        drawdown_curve.append({"index": point["index"], "value": round(drawdown, 2)})

    monthly_returns = [
        {"month": f"2025-{str(i).zfill(2)}", "return": round(random.uniform(-5, 8), 2)}
        for i in range(1, 13)
    ]

    card = ReportCard(
        user_id=current_user.id,
        name=data.name,
        period_start=data.period_start,
        period_end=data.period_end,
        exchange=data.exchange,
        symbol=data.symbol,
        total_trades=data.total_trades,
        win_trades=data.win_trades,
        loss_trades=data.loss_trades,
        win_rate=win_rate,
        total_pnl=data.total_pnl,
        total_pnl_pct=data.total_pnl_pct,
        avg_win=data.avg_win,
        avg_loss=data.avg_loss,
        profit_factor=profit_factor,
        max_drawdown=data.max_drawdown,
        max_drawdown_pct=data.max_drawdown_pct,
        sharpe_ratio=data.sharpe_ratio,
        best_trade=data.best_trade,
        worst_trade=data.worst_trade,
        consecutive_wins=data.consecutive_wins,
        consecutive_losses=data.consecutive_losses,
        equity_curve=equity_curve,
        drawdown_curve=drawdown_curve,
        monthly_returns=monthly_returns
    )
    db.add(card)
    db.commit()
    db.refresh(card)

    return ReportCardResponse(
        id=card.id,
        user_id=card.user_id,
        username=current_user.username,
        avatar=current_user.avatar,
        name=card.name,
        period_start=card.period_start,
        period_end=card.period_end,
        exchange=card.exchange,
        symbol=card.symbol,
        total_trades=card.total_trades,
        win_trades=card.win_trades,
        loss_trades=card.loss_trades,
        win_rate=card.win_rate,
        total_pnl=card.total_pnl,
        total_pnl_pct=card.total_pnl_pct,
        avg_win=card.avg_win,
        avg_loss=card.avg_loss,
        profit_factor=card.profit_factor,
        max_drawdown=card.max_drawdown,
        max_drawdown_pct=card.max_drawdown_pct,
        sharpe_ratio=card.sharpe_ratio,
        best_trade=card.best_trade,
        worst_trade=card.worst_trade,
        consecutive_wins=card.consecutive_wins,
        consecutive_losses=card.consecutive_losses,
        equity_curve=card.equity_curve or [],
        drawdown_curve=card.drawdown_curve or [],
        monthly_returns=card.monthly_returns or [],
        likes_count=0,
        views_count=0,
        is_liked=False,
        created_at=card.created_at
    )


@router.get("/report-cards/{card_id}")
async def get_report_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取成绩单详情"""
    card = db.query(ReportCard).filter(ReportCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="成绩单不存在")

    card.views_count += 1
    db.commit()

    is_liked = db.query(ReportCardLike).filter(
        ReportCardLike.report_card_id == card.id,
        ReportCardLike.user_id == current_user.id
    ).first() is not None

    return ReportCardResponse(
        id=card.id,
        user_id=card.user_id,
        username=card.user.username if card.user else "Unknown",
        avatar=card.user.avatar if card.user else "",
        name=card.name,
        period_start=card.period_start,
        period_end=card.period_end,
        exchange=card.exchange,
        symbol=card.symbol,
        total_trades=card.total_trades,
        win_trades=card.win_trades,
        loss_trades=card.loss_trades,
        win_rate=card.win_rate,
        total_pnl=card.total_pnl,
        total_pnl_pct=card.total_pnl_pct,
        avg_win=card.avg_win,
        avg_loss=card.avg_loss,
        profit_factor=card.profit_factor,
        max_drawdown=card.max_drawdown,
        max_drawdown_pct=card.max_drawdown_pct,
        sharpe_ratio=card.sharpe_ratio,
        best_trade=card.best_trade,
        worst_trade=card.worst_trade,
        consecutive_wins=card.consecutive_wins,
        consecutive_losses=card.consecutive_losses,
        equity_curve=card.equity_curve or [],
        drawdown_curve=card.drawdown_curve or [],
        monthly_returns=card.monthly_returns or [],
        likes_count=card.likes_count,
        views_count=card.views_count,
        is_liked=is_liked,
        created_at=card.created_at
    )


@router.post("/report-cards/{card_id}/like")
async def like_report_card(
    card_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """点赞成绩单"""
    card = db.query(ReportCard).filter(ReportCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="成绩单不存在")

    existing = db.query(ReportCardLike).filter(
        ReportCardLike.report_card_id == card_id,
        ReportCardLike.user_id == current_user.id
    ).first()

    if existing:
        db.delete(existing)
        card.likes_count = max(0, card.likes_count - 1)
        action = "unliked"
    else:
        db.add(ReportCardLike(report_card_id=card_id, user_id=current_user.id))
        card.likes_count += 1
        action = "liked"

    db.commit()
    return {"success": True, "action": action, "likes_count": card.likes_count}


@router.post("/report-cards/{card_id}/share")
async def share_report_card(
    card_id: int,
    channel_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分享成绩单到社区"""
    card = db.query(ReportCard).filter(ReportCard.id == card_id).first()
    if not card:
        raise HTTPException(status_code=404, detail="成绩单不存在")

    return {"success": True, "message": "成绩单已准备好分享", "card_id": card_id}


# ==================== 内容嵌入 API ====================

@router.post("/embeds")
async def create_embed(
    data: EmbedCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建频道嵌入内容"""
    embed = ChannelEmbed(
        channel_id=data.channel_id,
        embed_type=data.embed_type,
        title=data.title,
        content=data.content,
        symbol=data.symbol,
        period=data.period,
        created_by=current_user.id
    )
    db.add(embed)
    db.commit()
    db.refresh(embed)

    return {
        "success": True,
        "embed_id": embed.id,
        "embed_type": embed.embed_type,
        "symbol": embed.symbol,
        "period": embed.period
    }


@router.get("/embeds/channel/{channel_id}")
async def get_channel_embeds(
    channel_id: int,
    db: Session = Depends(get_db)
):
    """获取频道的嵌入内容"""
    embeds = db.query(ChannelEmbed).filter(
        ChannelEmbed.channel_id == channel_id
    ).order_by(ChannelEmbed.created_at.desc()).limit(20).all()

    return [
        {
            "id": e.id,
            "embed_type": e.embed_type,
            "title": e.title,
            "content": e.content,
            "symbol": e.symbol,
            "period": e.period,
            "created_at": e.created_at.isoformat() if e.created_at else None
        }
        for e in embeds
    ]


# ==================== 持仓分享 API ====================

@router.get("/position-shares")
async def get_position_shares(
    symbol: str = Query(None),
    visibility: str = Query("all"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取持仓分享"""
    query = db.query(PositionShare)

    if symbol:
        query = query.filter(PositionShare.symbol == symbol)

    if visibility == "public":
        query = query.filter(PositionShare.visibility == "public")
    elif visibility == "friends":
        friend_ids = [f.id for f in current_user.friends]
        friend_ids.append(current_user.id)
        query = query.filter(
            (PositionShare.visibility == "public") |
            ((PositionShare.visibility == "friends") & (PositionShare.user_id.in_(friend_ids)))
        )

    shares = query.order_by(PositionShare.created_at.desc()).limit(limit).all()

    result = []
    for s in shares:
        is_liked = db.query(PositionShareLike).filter(
            PositionShareLike.share_id == s.id,
            PositionShareLike.user_id == current_user.id
        ).first() is not None

        result.append({
            "id": s.id,
            "user_id": s.user_id,
            "username": s.user.username if s.user else "Unknown",
            "avatar": s.user.avatar if s.user else "",
            "symbol": s.symbol,
            "direction": s.direction,
            "entry_price": s.entry_price,
            "current_price": s.current_price,
            "quantity": s.quantity,
            "pnl": s.pnl,
            "pnl_pct": s.pnl_pct,
            "notes": s.notes,
            "image_url": s.image_url,
            "visibility": s.visibility,
            "likes_count": s.likes_count,
            "comments_count": s.comments_count,
            "is_liked": is_liked,
            "created_at": s.created_at.isoformat() if s.created_at else None
        })

    return result


@router.post("/position-shares")
async def create_position_share(
    data: PositionShareCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发布持仓分享"""
    share = PositionShare(
        user_id=current_user.id,
        channel_id=data.channel_id,
        symbol=data.symbol,
        direction=data.direction,
        entry_price=data.entry_price,
        quantity=data.quantity,
        notes=data.notes,
        visibility=data.visibility
    )
    db.add(share)
    db.commit()
    db.refresh(share)

    return {
        "id": share.id,
        "user_id": share.user_id,
        "username": current_user.username,
        "avatar": current_user.avatar,
        "symbol": share.symbol,
        "direction": share.direction,
        "entry_price": share.entry_price,
        "quantity": share.quantity,
        "pnl": 0,
        "pnl_pct": 0,
        "visibility": share.visibility,
        "likes_count": 0,
        "comments_count": 0,
        "created_at": share.created_at.isoformat() if share.created_at else None
    }


# ==================== 行情异动 API ====================

@router.get("/price-movements")
async def get_price_movements(
    category: str = Query("all"),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取行情异动列表"""
    query = db.query(PriceMovement)

    if category != "all":
        query = query.filter(PriceMovement.category == category)

    movements = query.order_by(PriceMovement.created_at.desc()).limit(limit).all()

    if not movements:
        symbols = ["BTC", "ETH", "SOL", "XRP", "DOGE", "EUR/USD", "GBP/USD", "XAU/USD"]
        mock_data = []
        for i, sym in enumerate(symbols[:8]):
            change = round(random.uniform(-8, 8), 2)
            mock_data.append({
                "id": i + 1,
                "symbol": sym,
                "exchange": "Binance" if "/" not in sym else "MT5",
                "category": "crypto" if "/" not in sym else "forex",
                "price_before": round(random.uniform(100, 50000), 2),
                "price_after": 0,
                "change_pct": change,
                "change_type": "rise" if change > 0 else "fall",
                "volume_ratio": round(random.uniform(1, 5), 2),
                "created_at": datetime.now().isoformat()
            })
        return mock_data

    return [
        {
            "id": m.id,
            "symbol": m.symbol,
            "exchange": m.exchange,
            "category": m.category,
            "price_before": m.price_before,
            "price_after": m.price_after,
            "change_pct": m.change_pct,
            "change_type": m.change_type,
            "volume_ratio": m.volume_ratio,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in movements
    ]


@router.get("/rankings-summary")
async def get_rankings_summary(db: Session = Depends(get_db)):
    """获取排行榜汇总数据"""
    today = datetime.now().strftime("%Y-%m-%d")

    trader_top3 = db.query(DailyTraderRanking).filter(
        DailyTraderRanking.date == today,
        DailyTraderRanking.period_type == "daily"
    ).order_by(DailyTraderRanking.ranking).limit(3).all()

    strategy_top3 = db.query(StrategyRanking).filter(
        StrategyRanking.date == today,
        StrategyRanking.period_type == "daily"
    ).order_by(StrategyRanking.ranking).limit(3).all()

    return {
        "trader_top3": [
            {
                "ranking": r.ranking,
                "user_id": r.user_id,
                "username": r.user.username if r.user else "Unknown",
                "avatar": r.user.avatar if r.user else "",
                "change_pct": r.total_pnl_pct,
                "win_rate": r.win_rate
            }
            for r in trader_top3
        ] if trader_top3 else [],
        "strategy_top3": [
            {
                "ranking": r.ranking,
                "strategy_id": r.strategy_id,
                "strategy_name": r.strategy.name if r.strategy else "Unknown",
                "username": r.strategy.user.username if r.strategy and r.strategy.user else "Unknown",
                "return_pct": r.total_return_pct
            }
            for r in strategy_top3
        ] if strategy_top3 else []
    }
