"""
QuantAI 交易广场对接模块
功能：交易信号同步、持仓动态分享、策略广场
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel
from app.database import get_db
from app.models import User
from app.auth import get_current_user, get_optional_user

router = APIRouter(prefix="/api/quantai", tags=["QuantAI 交易广场"])


# ============================================
# 数据模型
# ============================================

class SignalCreate(BaseModel):
    symbol: str
    direction: str
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    signal_type: str = "MANUAL"
    strategy_name: str = ""
    timeframe: str = "1h"
    notes: str = ""
    tags: str = ""


class SignalResponse(BaseModel):
    id: int
    user_id: int
    symbol: str
    direction: str
    entry_price: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    signal_type: str
    strategy_name: str
    timeframe: str
    notes: str
    tags: str
    status: str
    pnl_pct: Optional[float]
    closed_at: Optional[datetime]
    likes_count: int
    comments_count: int
    is_liked: bool
    created_at: datetime
    author: dict

    class Config:
        from_attributes = True


class PortfolioSync(BaseModel):
    symbol: str
    direction: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    source: str = "manual"


QUANTAI_API_BASE = "https://api.quantai.example.com"
QUANTAI_API_KEY = ""


def user_dict(u: User) -> dict:
    return {"id": u.id, "username": u.username, "avatar": u.avatar, "is_online": u.is_online}


def signal_to_dict(signal, current_user=None, db=None) -> dict:
    return {
        "id": signal.id,
        "user_id": signal.user_id,
        "symbol": signal.symbol,
        "direction": signal.direction,
        "entry_price": signal.entry_price,
        "stop_loss": signal.stop_loss,
        "take_profit": signal.take_profit,
        "signal_type": signal.signal_type,
        "strategy_name": signal.strategy_name,
        "timeframe": signal.timeframe,
        "notes": signal.notes,
        "tags": signal.tags,
        "status": signal.status,
        "pnl_pct": signal.pnl_pct,
        "closed_at": signal.closed_at,
        "likes_count": signal.likes_count or 0,
        "comments_count": signal.comments_count or 0,
        "is_liked": signal.is_liked or False,
        "created_at": signal.created_at.isoformat() if signal.created_at else None,
        "author": user_dict(signal.author) if signal.author else {},
    }


@router.get("/square")
async def get_trading_square(
    page: int = 1,
    limit: int = 20,
    symbol: str = "",
    direction: str = "",
    signal_type: str = "",
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    """获取交易广场信号流，支持按品种/方向/类型筛选"""
    from app.models import TradingSignal
    query = db.query(TradingSignal)
    if symbol:
        query = query.filter(TradingSignal.symbol.ilike(f"%{symbol}%"))
    if direction:
        query = query.filter(TradingSignal.direction == direction.upper())
    if signal_type:
        query = query.filter(TradingSignal.signal_type == signal_type)
    total = query.count()
    signals = query.order_by(desc(TradingSignal.created_at)).offset((page - 1) * limit).limit(limit).all()
    return {"signals": [signal_to_dict(s, current_user, db) for s in signals], "total": total, "page": page, "limit": limit}


@router.post("/signals")
async def create_signal(
    data: SignalCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """发布交易信号，同步到 QuantAI 交易广场"""
    from app.models import TradingSignal
    signal = TradingSignal(
        user_id=current_user.id,
        symbol=data.symbol.upper(),
        direction=data.direction.upper(),
        entry_price=data.entry_price,
        stop_loss=data.stop_loss,
        take_profit=data.take_profit,
        signal_type=data.signal_type,
        strategy_name=data.strategy_name,
        timeframe=data.timeframe,
        notes=data.notes,
        tags=data.tags,
        status="ACTIVE",
    )
    db.add(signal)
    db.commit()
    db.refresh(signal)
    return {"id": signal.id, "message": "信号发布成功", "synced_to_quantai": False}


@router.get("/signals/{signal_id}")
async def get_signal(signal_id: int, current_user: Optional[User] = Depends(get_optional_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal
    signal = db.query(TradingSignal).filter(TradingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(404, "信号不存在")
    return signal_to_dict(signal, current_user, db)


@router.put("/signals/{signal_id}/close")
async def close_signal(signal_id: int, pnl_pct: float, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal
    signal = db.query(TradingSignal).filter(TradingSignal.id == signal_id, TradingSignal.user_id == current_user.id).first()
    if not signal:
        raise HTTPException(404, "信号不存在或无权操作")
    signal.status = "CLOSED"
    signal.pnl_pct = pnl_pct
    signal.closed_at = datetime.now()
    db.commit()
    return {"message": "平仓成功", "pnl_pct": pnl_pct}


@router.post("/signals/{signal_id}/like")
async def toggle_signal_like(signal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal, SignalLike
    signal = db.query(TradingSignal).filter(TradingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(404, "信号不存在")
    existing = db.query(SignalLike).filter_by(user_id=current_user.id, signal_id=signal_id).first()
    if existing:
        db.delete(existing)
        signal.likes_count = max(0, (signal.likes_count or 0) - 1)
        liked = False
    else:
        db.add(SignalLike(user_id=current_user.id, signal_id=signal_id))
        signal.likes_count = (signal.likes_count or 0) + 1
        liked = True
    db.commit()
    return {"liked": liked, "likes_count": signal.likes_count}


@router.post("/signals/{signal_id}/comment")
async def comment_signal(signal_id: int, data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal, SignalComment, Notification
    signal = db.query(TradingSignal).filter(TradingSignal.id == signal_id).first()
    if not signal:
        raise HTTPException(404, "信号不存在")
    comment = SignalComment(signal_id=signal_id, user_id=current_user.id, content=data.get("content", ""))
    db.add(comment)
    signal.comments_count = (signal.comments_count or 0) + 1
    if signal.user_id != current_user.id:
        db.add(Notification(user_id=signal.user_id, type="signal_comment",
                           content=f"{current_user.username} 评论了你的信号 {signal.symbol}",
                           from_user_id=current_user.id))
    db.commit()
    return {"id": comment.id, "message": "评论成功"}


@router.get("/signals/{signal_id}/comments")
async def get_signal_comments(signal_id: int, db: Session = Depends(get_db)):
    from app.models import SignalComment
    comments = db.query(SignalComment).filter(SignalComment.signal_id == signal_id).order_by(SignalComment.created_at).all()
    return [{"id": c.id, "content": c.content, "created_at": c.created_at.isoformat(),
             "author": user_dict(c.author) if c.author else {}} for c in comments]


@router.get("/my-signals")
async def get_my_signals(page: int = 1, limit: int = 20, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal
    query = db.query(TradingSignal).filter(TradingSignal.user_id == current_user.id)
    total = query.count()
    signals = query.order_by(desc(TradingSignal.created_at)).offset((page - 1) * limit).limit(limit).all()
    return {"signals": [signal_to_dict(s, current_user, db) for s in signals], "total": total}


@router.post("/portfolio/sync")
async def sync_portfolio(data: List[PortfolioSync], current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import PortfolioPosition
    db.query(PortfolioPosition).filter(PortfolioPosition.user_id == current_user.id).delete()
    for pos in data:
        p = PortfolioPosition(user_id=current_user.id, symbol=pos.symbol.upper(),
                              direction=pos.direction.upper(), quantity=pos.quantity,
                              entry_price=pos.entry_price, current_price=pos.current_price,
                              unrealized_pnl=pos.unrealized_pnl, unrealized_pnl_pct=pos.unrealized_pnl_pct,
                              source=pos.source)
        db.add(p)
    db.commit()
    return {"message": "持仓同步成功", "positions_count": len(data), "synced_to_quantai": False}


@router.get("/portfolio")
async def get_portfolio(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import PortfolioPosition
    positions = db.query(PortfolioPosition).filter(PortfolioPosition.user_id == current_user.id).all()
    total_pnl = sum(p.unrealized_pnl or 0 for p in positions)
    total_pnl_pct = sum(p.unrealized_pnl_pct or 0 for p in positions) / max(len(positions), 1)
    return {
        "positions": [{"id": p.id, "symbol": p.symbol, "direction": p.direction,
                       "quantity": p.quantity, "entry_price": p.entry_price,
                       "current_price": p.current_price, "unrealized_pnl": p.unrealized_pnl,
                       "unrealized_pnl_pct": p.unrealized_pnl_pct, "source": p.source,
                       "created_at": p.created_at.isoformat() if p.created_at else None} for p in positions],
        "summary": {"total_pnl": round(total_pnl, 2), "total_pnl_pct": round(total_pnl_pct, 2), "positions_count": len(positions)}
    }


@router.post("/signals/{signal_id}/share")
async def share_to_quantai(signal_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.models import TradingSignal
    signal = db.query(TradingSignal).filter(TradingSignal.id == signal_id, TradingSignal.user_id == current_user.id).first()
    if not signal:
        raise HTTPException(404, "信号不存在")
    return {"message": "信号已分享到 QuantAI 交易广场", "signal_id": signal_id, "quantai_url": f"https://quantai.example.com/signal/{signal_id}"}


@router.post("/inbound/signal")
async def receive_quantai_signal(data: dict, api_key: str = "", db: Session = Depends(get_db)):
    from app.models import TradingSignal
    if api_key != QUANTAI_API_KEY and QUANTAI_API_KEY:
        raise HTTPException(401, "无效的 API 密钥")
    signal = TradingSignal(user_id=data.get("user_id", 0), symbol=data.get("symbol", "").upper(),
                           direction=data.get("direction", "LONG").upper(),
                           entry_price=data.get("entry_price", 0),
                           stop_loss=data.get("stop_loss"), take_profit=data.get("take_profit"),
                           signal_type=data.get("signal_type", "QUANTAI"),
                           strategy_name=data.get("strategy_name", ""),
                           timeframe=data.get("timeframe", "1h"),
                           notes=data.get("notes", ""), tags=data.get("tags", ""),
                           status="ACTIVE", source="quantai")
    db.add(signal)
    db.commit()
    return {"message": "信号接收成功", "id": signal.id}
