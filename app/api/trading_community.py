"""
第三阶段 API：量化交易社区化
- 持仓动态（公开/好友可见）
- 行情异动推送
- 一键跟单
- 策略分享
- 文字频道K线嵌入
- 语音/视频交易直播
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
import asyncio
import json

from app.database import get_db
from app.models_phase3 import (
    PortfolioUpdate, PortfolioUpdateLike, PortfolioUpdateComment,
    PriceAlert, CopyTradeSettings, CopyTradeRecord,
    Strategy, StrategyLike, StrategyComment,
    ChannelKlineEmbed,
    LiveStream, LiveStreamViewer,
    SignalSubscription, ReportShare,
    portfolio_visibility_settings
)
from app.models import User, ChannelMessage, Channel, TradingSignal, BacktestReport
from app.auth import get_current_user

router = APIRouter(prefix="/api/trading-community", tags=["第三阶段：交易社区"])


# ==================== Pydantic Schemas ====================

class PortfolioUpdateCreate(BaseModel):
    symbol: str
    direction: str  # long / short
    entry_price: float
    quantity: float
    notes: str = ""
    tags: str = ""
    visibility: str = "public"  # public / friends / private


class PortfolioUpdateResponse(BaseModel):
    id: int
    user_id: int
    username: str
    avatar: str
    symbol: str
    direction: str
    entry_price: float
    current_price: Optional[float]
    quantity: float
    pnl: float
    pnl_pct: float
    notes: str
    tags: str
    visibility: str
    likes_count: int
    comments_count: int
    is_pinned: bool
    is_liked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class PriceAlertCreate(BaseModel):
    symbol: str
    condition: str  # above / below / change_pct
    threshold: float
    notify_friends: bool = False


class PriceAlertResponse(BaseModel):
    id: int
    symbol: str
    condition: str
    threshold: float
    is_active: bool
    is_triggered: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CopyTradeSettingsCreate(BaseModel):
    leader_id: int
    symbols: str = "all"
    max_positions: int = 5
    stop_loss_pct: Optional[float] = None
    take_profit_pct: Optional[float] = None


class StrategyCreate(BaseModel):
    name: str
    description: str
    strategy_type: str = "manual"
    symbols: str = ""
    timeframe: str = "1h"
    entry_conditions: str = ""
    exit_conditions: str = ""
    risk_management: str = ""
    code_snippet: str = ""
    tags: str = ""


class StrategyResponse(BaseModel):
    id: int
    user_id: int
    username: str
    avatar: str
    name: str
    description: str
    strategy_type: str
    symbols: str
    timeframe: str
    entry_conditions: str
    exit_conditions: str
    risk_management: str
    backtest_report_id: Optional[int]
    likes_count: int
    views_count: int
    tags: str
    is_liked: bool
    created_at: datetime

    class Config:
        from_attributes = True


class LiveStreamCreate(BaseModel):
    room_id: str
    title: str
    stream_type: str = "trading"


class LiveStreamResponse(BaseModel):
    id: int
    room_id: str
    host_id: int
    host_username: str
    title: str
    stream_type: str
    status: str
    current_symbol: Optional[str]
    is_screen_sharing: bool
    viewer_count: int
    started_at: datetime

    class Config:
        from_attributes = True


# ==================== 持仓动态 API ====================

@router.get("/portfolio-updates", response_model=List[PortfolioUpdateResponse])
async def get_portfolio_updates(
    visibility: str = Query("all", description="public/friends/all"),
    symbol: str = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取持仓动态"""
    query = db.query(PortfolioUpdate)
    
    if visibility == "friends":
        # 只显示公开 + 当前用户好友的动态
        friend_ids = [f.id for f in current_user.friends]
        friend_ids.append(current_user.id)
        query = query.filter(
            (PortfolioUpdate.visibility == "public") |
            ((PortfolioUpdate.visibility == "friends") & (PortfolioUpdate.user_id.in_(friend_ids)))
        )
    elif visibility == "public":
        query = query.filter(PortfolioUpdate.visibility == "public")
    
    if symbol:
        query = query.filter(PortfolioUpdate.symbol == symbol)
    
    updates = query.order_by(PortfolioUpdate.is_pinned.desc(), PortfolioUpdate.created_at.desc()).limit(limit).all()
    
    result = []
    for u in updates:
        is_liked = db.query(PortfolioUpdateLike).filter(
            PortfolioUpdateLike.update_id == u.id,
            PortfolioUpdateLike.user_id == current_user.id
        ).first() is not None
        
        result.append(PortfolioUpdateResponse(
            id=u.id,
            user_id=u.user_id,
            username=u.user.username if u.user else "Unknown",
            avatar=u.user.avatar if u.user else "",
            symbol=u.symbol,
            direction=u.direction,
            entry_price=u.entry_price,
            current_price=u.current_price,
            quantity=u.quantity,
            pnl=u.pnl,
            pnl_pct=u.pnl_pct,
            notes=u.notes,
            tags=u.tags,
            visibility=u.visibility,
            likes_count=u.likes_count,
            comments_count=u.comments_count,
            is_pinned=u.is_pinned,
            is_liked=is_liked,
            created_at=u.created_at
        ))
    
    return result


@router.post("/portfolio-updates", response_model=PortfolioUpdateResponse)
async def create_portfolio_update(
    data: PortfolioUpdateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发布持仓动态"""
    update = PortfolioUpdate(
        user_id=current_user.id,
        symbol=data.symbol,
        direction=data.direction,
        entry_price=data.entry_price,
        quantity=data.quantity,
        notes=data.notes,
        tags=data.tags,
        visibility=data.visibility
    )
    db.add(update)
    db.commit()
    db.refresh(update)
    
    return PortfolioUpdateResponse(
        id=update.id,
        user_id=update.user_id,
        username=current_user.username,
        avatar=current_user.avatar,
        symbol=update.symbol,
        direction=update.direction,
        entry_price=update.entry_price,
        current_price=update.current_price,
        quantity=update.quantity,
        pnl=update.pnl,
        pnl_pct=update.pnl_pct,
        notes=update.notes,
        tags=update.tags,
        visibility=update.visibility,
        likes_count=0,
        comments_count=0,
        is_pinned=False,
        is_liked=False,
        created_at=update.created_at
    )


@router.post("/portfolio-updates/{update_id}/like")
async def like_portfolio_update(
    update_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """点赞持仓动态"""
    update = db.query(PortfolioUpdate).filter(PortfolioUpdate.id == update_id).first()
    if not update:
        raise HTTPException(status_code=404, detail="动态不存在")
    
    existing = db.query(PortfolioUpdateLike).filter(
        PortfolioUpdateLike.update_id == update_id,
        PortfolioUpdateLike.user_id == current_user.id
    ).first()
    
    if existing:
        db.delete(existing)
        update.likes_count = max(0, update.likes_count - 1)
        action = "unliked"
    else:
        db.add(PortfolioUpdateLike(update_id=update_id, user_id=current_user.id))
        update.likes_count += 1
        action = "liked"
    
    db.commit()
    return {"success": True, "action": action, "likes_count": update.likes_count}


@router.get("/portfolio-updates/{update_id}/comments")
async def get_portfolio_update_comments(
    update_id: int,
    db: Session = Depends(get_db)
):
    """获取持仓动态评论"""
    comments = db.query(PortfolioUpdateComment).filter(
        PortfolioUpdateComment.update_id == update_id
    ).order_by(PortfolioUpdateComment.created_at).all()
    
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "username": c.user.username if c.user else "Unknown",
            "avatar": c.user.avatar if c.user else "",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in comments
    ]


@router.post("/portfolio-updates/{update_id}/comments")
async def add_portfolio_update_comment(
    update_id: int,
    content: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """评论持仓动态"""
    update = db.query(PortfolioUpdate).filter(PortfolioUpdate.id == update_id).first()
    if not update:
        raise HTTPException(status_code=404, detail="动态不存在")
    
    comment = PortfolioUpdateComment(
        update_id=update_id,
        user_id=current_user.id,
        content=content
    )
    db.add(comment)
    update.comments_count += 1
    db.commit()
    db.refresh(comment)
    
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "username": current_user.username,
        "avatar": current_user.avatar,
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None
    }


# ==================== 行情异动推送 API ====================

@router.get("/price-alerts", response_model=List[PriceAlertResponse])
async def get_price_alerts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的行情提醒"""
    alerts = db.query(PriceAlert).filter(
        PriceAlert.user_id == current_user.id
    ).order_by(PriceAlert.created_at.desc()).all()
    return alerts


@router.post("/price-alerts", response_model=PriceAlertResponse)
async def create_price_alert(
    data: PriceAlertCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建行情异动提醒"""
    alert = PriceAlert(
        user_id=current_user.id,
        symbol=data.symbol,
        condition=data.condition,
        threshold=data.threshold,
        notify_friends=data.notify_friends
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert


@router.delete("/price-alerts/{alert_id}")
async def delete_price_alert(
    alert_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除行情提醒"""
    alert = db.query(PriceAlert).filter(
        PriceAlert.id == alert_id,
        PriceAlert.user_id == current_user.id
    ).first()
    if not alert:
        raise HTTPException(status_code=404, detail="提醒不存在")
    
    db.delete(alert)
    db.commit()
    return {"success": True}


@router.get("/price-alerts/check")
async def check_price_alerts(
    db: Session = Depends(get_db)
):
    """检查并触发行情提醒（由定时任务调用）"""
    from app.api.market import get_realtime_quote, ALL_SYMBOLS
    
    triggered = []
    alerts = db.query(PriceAlert).filter(
        PriceAlert.is_active == True,
        PriceAlert.is_triggered == False
    ).all()
    
    for alert in alerts:
        try:
            base_price = 100  # 默认价格
            quote = await get_realtime_quote(alert.symbol, base_price)
            current_price = quote.get("price", 0)
            
            if not current_price:
                continue
            
            # 检查是否触发
            should_trigger = False
            if alert.condition == "above" and current_price >= alert.threshold:
                should_trigger = True
            elif alert.condition == "below" and current_price <= alert.threshold:
                should_trigger = True
            elif alert.condition == "change_pct":
                if alert.last_checked_price:
                    change_pct = abs((current_price - alert.last_checked_price) / alert.last_checked_price * 100)
                    if change_pct >= alert.threshold:
                        should_trigger = True
            
            if should_trigger:
                alert.is_triggered = True
                alert.triggered_at = datetime.now()
                db.commit()
                
                # 如果需要通知好友
                if alert.notify_friends:
                    # 创建通知给所有好友
                    for friend in alert.user.friends:
                        notification = {
                            "type": "price_alert",
                            "symbol": alert.symbol,
                            "condition": alert.condition,
                            "threshold": alert.threshold,
                            "current_price": current_price,
                            "from_user": alert.user.username
                        }
                        # 这里可以推送到WebSocket
                
                triggered.append({
                    "alert_id": alert.id,
                    "symbol": alert.symbol,
                    "condition": alert.condition,
                    "threshold": alert.threshold,
                    "current_price": current_price,
                    "user_id": alert.user_id
                })
            else:
                alert.last_checked_price = current_price
                db.commit()
                
        except Exception as e:
            print(f"Check alert error: {e}")
    
    return {"checked": len(alerts), "triggered": triggered}


# ==================== 一键跟单 API ====================

@router.get("/copy-trade/settings")
async def get_copy_trade_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的跟单设置"""
    settings = db.query(CopyTradeSettings).filter(
        CopyTradeSettings.follower_id == current_user.id
    ).all()
    
    return [
        {
            "id": s.id,
            "leader_id": s.leader_id,
            "leader_username": s.leader.username if s.leader else "Unknown",
            "leader_avatar": s.leader.avatar if s.leader else "",
            "symbols": s.symbols,
            "max_positions": s.max_positions,
            "stop_loss_pct": s.stop_loss_pct,
            "take_profit_pct": s.take_profit_pct,
            "is_active": s.is_active,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in settings
    ]


@router.post("/copy-trade/settings")
async def create_copy_trade_settings(
    data: CopyTradeSettingsCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建跟单设置"""
    # 检查是否已存在
    existing = db.query(CopyTradeSettings).filter(
        CopyTradeSettings.follower_id == current_user.id,
        CopyTradeSettings.leader_id == data.leader_id
    ).first()
    
    if existing:
        existing.symbols = data.symbols
        existing.max_positions = data.max_positions
        existing.stop_loss_pct = data.stop_loss_pct
        existing.take_profit_pct = data.take_profit_pct
        existing.is_active = True
        db.commit()
        return {"success": True, "message": "跟单设置已更新", "id": existing.id}
    
    settings = CopyTradeSettings(
        follower_id=current_user.id,
        leader_id=data.leader_id,
        symbols=data.symbols,
        max_positions=data.max_positions,
        stop_loss_pct=data.stop_loss_pct,
        take_profit_pct=data.take_profit_pct
    )
    db.add(settings)
    db.commit()
    db.refresh(settings)
    
    return {"success": True, "message": "跟单设置已创建", "id": settings.id}


@router.delete("/copy-trade/settings/{settings_id}")
async def delete_copy_trade_settings(
    settings_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """删除跟单设置"""
    settings = db.query(CopyTradeSettings).filter(
        CopyTradeSettings.id == settings_id,
        CopyTradeSettings.follower_id == current_user.id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="跟单设置不存在")
    
    db.delete(settings)
    db.commit()
    return {"success": True}


@router.post("/copy-trade/settings/{settings_id}/toggle")
async def toggle_copy_trade(
    settings_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """开关跟单"""
    settings = db.query(CopyTradeSettings).filter(
        CopyTradeSettings.id == settings_id,
        CopyTradeSettings.follower_id == current_user.id
    ).first()
    
    if not settings:
        raise HTTPException(status_code=404, detail="跟单设置不存在")
    
    settings.is_active = not settings.is_active
    db.commit()
    return {"success": True, "is_active": settings.is_active}


@router.get("/copy-trade/leaders")
async def get_trade_leaders(
    symbol: str = Query(None),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取可跟单的交易高手"""
    # 获取有活跃交易信号的用户
    query = db.query(User).join(TradingSignal).filter(
        TradingSignal.status == "ACTIVE"
    ).distinct()
    
    if symbol:
        query = query.filter(TradingSignal.symbol == symbol)
    
    leaders = query.limit(limit).all()
    
    result = []
    for leader in leaders:
        # 计算该用户的信号统计
        signals = db.query(TradingSignal).filter(
            TradingSignal.user_id == leader.id,
            TradingSignal.status == "CLOSED"
        ).all()
        
        total_signals = len(signals)
        win_signals = len([s for s in signals if s.pnl_pct and s.pnl_pct > 0])
        win_rate = (win_signals / total_signals * 100) if total_signals > 0 else 0
        avg_pnl = sum([s.pnl_pct or 0 for s in signals]) / total_signals if total_signals > 0 else 0
        
        # 跟单人数
        follower_count = db.query(CopyTradeSettings).filter(
            CopyTradeSettings.leader_id == leader.id,
            CopyTradeSettings.is_active == True
        ).count()
        
        result.append({
            "user_id": leader.id,
            "username": leader.username,
            "avatar": leader.avatar,
            "bio": leader.bio,
            "total_signals": total_signals,
            "win_rate": round(win_rate, 1),
            "avg_pnl": round(avg_pnl, 2),
            "follower_count": follower_count,
            "is_online": leader.is_online
        })
    
    # 按胜率排序
    result.sort(key=lambda x: x["win_rate"], reverse=True)
    return result


@router.get("/copy-trade/records")
async def get_copy_trade_records(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我的跟单记录"""
    # 获取用户的所有跟单设置
    settings_ids = [s.id for s in db.query(CopyTradeSettings).filter(
        CopyTradeSettings.follower_id == current_user.id
    ).all()]
    
    records = db.query(CopyTradeRecord).filter(
        CopyTradeRecord.settings_id.in_(settings_ids)
    ).order_by(CopyTradeRecord.created_at.desc()).limit(50).all()
    
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "direction": r.direction,
            "leader_price": r.leader_price,
            "follower_price": r.follower_price,
            "quantity": r.quantity,
            "pnl": r.pnl,
            "pnl_pct": r.pnl_pct,
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "closed_at": r.closed_at.isoformat() if r.closed_at else None
        }
        for r in records
    ]


# ==================== 策略分享 API ====================

@router.get("/strategies", response_model=List[StrategyResponse])
async def get_strategies(
    symbol: str = Query(None),
    strategy_type: str = Query(None),
    sort: str = Query("recent"),  # recent / popular
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取策略列表"""
    query = db.query(Strategy)
    
    if symbol:
        query = query.filter(Strategy.symbols.contains(symbol))
    if strategy_type:
        query = query.filter(Strategy.strategy_type == strategy_type)
    
    if sort == "popular":
        query = query.order_by(Strategy.likes_count.desc())
    else:
        query = query.order_by(Strategy.created_at.desc())
    
    strategies = query.limit(limit).all()
    
    result = []
    for s in strategies:
        is_liked = db.query(StrategyLike).filter(
            StrategyLike.strategy_id == s.id,
            StrategyLike.user_id == current_user.id
        ).first() is not None
        
        result.append(StrategyResponse(
            id=s.id,
            user_id=s.user_id,
            username=s.user.username if s.user else "Unknown",
            avatar=s.user.avatar if s.user else "",
            name=s.name,
            description=s.description,
            strategy_type=s.strategy_type,
            symbols=s.symbols,
            timeframe=s.timeframe,
            entry_conditions=s.entry_conditions,
            exit_conditions=s.exit_conditions,
            risk_management=s.risk_management,
            backtest_report_id=s.backtest_report_id,
            likes_count=s.likes_count,
            views_count=s.views_count,
            tags=s.tags,
            is_liked=is_liked,
            created_at=s.created_at
        ))
    
    return result


@router.post("/strategies", response_model=StrategyResponse)
async def create_strategy(
    data: StrategyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """发布策略"""
    strategy = Strategy(
        user_id=current_user.id,
        name=data.name,
        description=data.description,
        strategy_type=data.strategy_type,
        symbols=data.symbols,
        timeframe=data.timeframe,
        entry_conditions=data.entry_conditions,
        exit_conditions=data.exit_conditions,
        risk_management=data.risk_management,
        code_snippet=data.code_snippet,
        tags=data.tags
    )
    db.add(strategy)
    db.commit()
    db.refresh(strategy)
    
    return StrategyResponse(
        id=strategy.id,
        user_id=strategy.user_id,
        username=current_user.username,
        avatar=current_user.avatar,
        name=strategy.name,
        description=strategy.description,
        strategy_type=strategy.strategy_type,
        symbols=strategy.symbols,
        timeframe=strategy.timeframe,
        entry_conditions=strategy.entry_conditions,
        exit_conditions=strategy.exit_conditions,
        risk_management=strategy.risk_management,
        backtest_report_id=strategy.backtest_report_id,
        likes_count=0,
        views_count=0,
        tags=strategy.tags,
        is_liked=False,
        created_at=strategy.created_at
    )


@router.get("/strategies/{strategy_id}")
async def get_strategy_detail(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取策略详情"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    # 增加浏览数
    strategy.views_count += 1
    db.commit()
    
    is_liked = db.query(StrategyLike).filter(
        StrategyLike.strategy_id == strategy.id,
        StrategyLike.user_id == current_user.id
    ).first() is not None
    
    # 获取关联的回测报告
    backtest_report = None
    if strategy.backtest_report_id:
        report = db.query(BacktestReport).filter(
            BacktestReport.id == strategy.backtest_report_id
        ).first()
        if report:
            backtest_report = {
                "id": report.id,
                "name": report.name,
                "win_rate": report.win_rate,
                "profit_factor": report.profit_factor,
                "max_drawdown": report.max_drawdown,
                "total_return": report.total_return
            }
    
    return {
        "id": strategy.id,
        "user_id": strategy.user_id,
        "username": strategy.user.username if strategy.user else "Unknown",
        "avatar": strategy.user.avatar if strategy.user else "",
        "name": strategy.name,
        "description": strategy.description,
        "strategy_type": strategy.strategy_type,
        "symbols": strategy.symbols,
        "timeframe": strategy.timeframe,
        "entry_conditions": strategy.entry_conditions,
        "exit_conditions": strategy.exit_conditions,
        "risk_management": strategy.risk_management,
        "code_snippet": strategy.code_snippet,
        "backtest_report": backtest_report,
        "likes_count": strategy.likes_count,
        "views_count": strategy.views_count,
        "tags": strategy.tags,
        "is_liked": is_liked,
        "created_at": strategy.created_at.isoformat() if strategy.created_at else None
    }


@router.post("/strategies/{strategy_id}/like")
async def like_strategy(
    strategy_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """点赞策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    existing = db.query(StrategyLike).filter(
        StrategyLike.strategy_id == strategy_id,
        StrategyLike.user_id == current_user.id
    ).first()
    
    if existing:
        db.delete(existing)
        strategy.likes_count = max(0, strategy.likes_count - 1)
        action = "unliked"
    else:
        db.add(StrategyLike(strategy_id=strategy_id, user_id=current_user.id))
        strategy.likes_count += 1
        action = "liked"
    
    db.commit()
    return {"success": True, "action": action, "likes_count": strategy.likes_count}


@router.get("/strategies/{strategy_id}/comments")
async def get_strategy_comments(
    strategy_id: int,
    db: Session = Depends(get_db)
):
    """获取策略评论"""
    comments = db.query(StrategyComment).filter(
        StrategyComment.strategy_id == strategy_id
    ).order_by(StrategyComment.created_at).all()
    
    return [
        {
            "id": c.id,
            "user_id": c.user_id,
            "username": c.user.username if c.user else "Unknown",
            "avatar": c.user.avatar if c.user else "",
            "content": c.content,
            "created_at": c.created_at.isoformat() if c.created_at else None
        }
        for c in comments
    ]


@router.post("/strategies/{strategy_id}/comments")
async def add_strategy_comment(
    strategy_id: int,
    content: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """评论策略"""
    strategy = db.query(Strategy).filter(Strategy.id == strategy_id).first()
    if not strategy:
        raise HTTPException(status_code=404, detail="策略不存在")
    
    comment = StrategyComment(
        strategy_id=strategy_id,
        user_id=current_user.id,
        content=content
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    
    return {
        "id": comment.id,
        "user_id": comment.user_id,
        "username": current_user.username,
        "avatar": current_user.avatar,
        "content": comment.content,
        "created_at": comment.created_at.isoformat() if comment.created_at else None
    }


# ==================== 交易直播 API ====================

@router.get("/live-streams")
async def get_live_streams(
    db: Session = Depends(get_db)
):
    """获取正在进行的交易直播"""
    streams = db.query(LiveStream).filter(
        LiveStream.status == "live"
    ).order_by(LiveStream.started_at.desc()).all()
    
    return [
        {
            "id": s.id,
            "room_id": s.room_id,
            "host_id": s.host_id,
            "host_username": s.host_username,
            "title": s.title,
            "stream_type": s.stream_type,
            "status": s.status,
            "current_symbol": s.current_symbol,
            "is_screen_sharing": s.is_screen_sharing,
            "viewer_count": s.viewer_count,
            "started_at": s.started_at.isoformat() if s.started_at else None
        }
        for s in streams
    ]


@router.post("/live-streams")
async def create_live_stream(
    data: LiveStreamCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """创建交易直播"""
    stream = LiveStream(
        room_id=data.room_id,
        host_id=current_user.id,
        host_username=current_user.username,
        title=data.title,
        stream_type=data.stream_type
    )
    db.add(stream)
    db.commit()
    db.refresh(stream)
    
    return {
        "id": stream.id,
        "room_id": stream.room_id,
        "host_id": stream.host_id,
        "host_username": stream.host_username,
        "title": stream.title,
        "stream_type": stream.stream_type,
        "status": stream.status,
        "viewer_count": 0
    }


@router.put("/live-streams/{stream_id}/screen-share")
async def toggle_screen_share(
    stream_id: int,
    is_sharing: bool = Query(...),
    screen_url: str = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """开关屏幕共享"""
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="直播不存在")
    
    if stream.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有主播可以控制屏幕共享")
    
    stream.is_screen_sharing = is_sharing
    stream.screen_sharing_url = screen_url
    db.commit()
    
    return {"success": True, "is_screen_sharing": stream.is_screen_sharing}


@router.put("/live-streams/{stream_id}/symbol")
async def update_stream_symbol(
    stream_id: int,
    symbol: str = Query(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """更新直播当前品种"""
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="直播不存在")
    
    if stream.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有主播可以更新品种")
    
    stream.current_symbol = symbol
    db.commit()
    
    return {"success": True, "current_symbol": symbol}


@router.post("/live-streams/{stream_id}/join")
async def join_live_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """加入直播"""
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="直播不存在")
    
    # 检查是否已在观众列表
    existing = db.query(LiveStreamViewer).filter(
        LiveStreamViewer.stream_id == stream_id,
        LiveStreamViewer.user_id == current_user.id
    ).first()
    
    if not existing:
        viewer = LiveStreamViewer(
            stream_id=stream_id,
            user_id=current_user.id
        )
        db.add(viewer)
        stream.viewer_count += 1
        db.commit()
    
    return {"success": True, "viewer_count": stream.viewer_count}


@router.post("/live-streams/{stream_id}/end")
async def end_live_stream(
    stream_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """结束直播"""
    stream = db.query(LiveStream).filter(LiveStream.id == stream_id).first()
    if not stream:
        raise HTTPException(status_code=404, detail="直播不存在")
    
    if stream.host_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有主播可以结束直播")
    
    stream.status = "ended"
    stream.ended_at = datetime.now()
    db.commit()
    
    return {"success": True}


# ==================== 信号订阅 API ====================

@router.get("/signal-subscriptions")
async def get_signal_subscriptions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """获取我订阅的信号"""
    subs = db.query(SignalSubscription).filter(
        SignalSubscription.subscriber_id == current_user.id,
        SignalSubscription.is_active == True
    ).all()
    
    return [
        {
            "id": s.id,
            "publisher_id": s.publisher_id,
            "publisher_username": s.publisher.username if s.publisher else "Unknown",
            "publisher_avatar": s.publisher.avatar if s.publisher else "",
            "symbols": s.symbols,
            "notify_immediately": s.notify_immediately,
            "created_at": s.created_at.isoformat() if s.created_at else None
        }
        for s in subs
    ]


@router.post("/signal-subscriptions")
async def subscribe_signals(
    publisher_id: int = Query(...),
    symbols: str = Query("all"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """订阅某人的交易信号"""
    if publisher_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能订阅自己的信号")
    
    existing = db.query(SignalSubscription).filter(
        SignalSubscription.subscriber_id == current_user.id,
        SignalSubscription.publisher_id == publisher_id
    ).first()
    
    if existing:
        existing.is_active = True
        existing.symbols = symbols
        db.commit()
        return {"success": True, "message": "订阅已更新", "id": existing.id}
    
    sub = SignalSubscription(
        subscriber_id=current_user.id,
        publisher_id=publisher_id,
        symbols=symbols
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    
    return {"success": True, "message": "订阅成功", "id": sub.id}


@router.delete("/signal-subscriptions/{sub_id}")
async def unsubscribe_signals(
    sub_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """取消信号订阅"""
    sub = db.query(SignalSubscription).filter(
        SignalSubscription.id == sub_id,
        SignalSubscription.subscriber_id == current_user.id
    ).first()
    
    if not sub:
        raise HTTPException(status_code=404, detail="订阅不存在")
    
    sub.is_active = False
    db.commit()
    return {"success": True}


# ==================== 回测报告分享 API ====================

@router.get("/reports/shared")
async def get_shared_reports(
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db)
):
    """获取社区分享的回测报告"""
    reports = db.query(BacktestReport).filter(
        BacktestReport.is_public == True
    ).order_by(BacktestReport.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": r.id,
            "name": r.name,
            "strategy_name": r.strategy_name,
            "symbol": r.symbol,
            "period": r.period,
            "win_rate": r.win_rate,
            "profit_factor": r.profit_factor,
            "max_drawdown": r.max_drawdown,
            "total_return": r.total_return,
            "likes_count": r.likes_count,
            "views_count": r.views_count,
            "user_id": r.user_id,
            "username": r.user.username if r.user else "Unknown",
            "avatar": r.user.avatar if r.user else "",
            "created_at": r.created_at.isoformat() if r.created_at else None
        }
        for r in reports
    ]


@router.post("/reports/{report_id}/share")
async def share_report(
    report_id: int,
    channel_id: int = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """分享回测报告到社区"""
    report = db.query(BacktestReport).filter(BacktestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    if report.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能分享自己的报告")
    
    share = ReportShare(
        report_id=report_id,
        channel_id=channel_id,
        shared_by=current_user.id
    )
    db.add(share)
    
    # 增加报告的浏览数
    report.views_count += 1
    db.commit()
    db.refresh(share)
    
    return {"success": True, "share_id": share.id}
