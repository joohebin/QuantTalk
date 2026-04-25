"""
成绩单/交易报告 API
用户可以晒自己的交易记录、盈亏曲线、回测报告
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/portfolio", tags=["成绩单"])

# ========== 模型 ==========

class TradeRecordCreate(BaseModel):
    symbol: str
    direction: str  # long / short
    entry_price: float
    exit_price: Optional[float] = None
    entry_time: str
    exit_time: Optional[str] = None
    quantity: float
    pnl: Optional[float] = None
    pnl_pct: Optional[float] = None
    strategy_name: Optional[str] = None
    notes: Optional[str] = None

class TradeRecordResponse(BaseModel):
    id: int
    user_id: int
    username: str
    symbol: str
    direction: str
    entry_price: float
    exit_price: Optional[float]
    entry_time: str
    exit_time: Optional[str]
    quantity: float
    pnl: Optional[float]
    pnl_pct: Optional[float]
    strategy_name: Optional[str]
    notes: Optional[str]
    created_at: str

class BacktestReportCreate(BaseModel):
    name: str
    strategy_name: str
    symbol: str
    period: str  # 1m, 5m, 1h, 1d
    start_date: str
    end_date: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float] = None
    total_return: float
    annualized_return: Optional[float] = None
    equity_curve: Optional[str] = None  # JSON string
    trades_summary: Optional[str] = None  # JSON string
    chart_data: Optional[str] = None  # JSON string
    notes: Optional[str] = None
    is_public: bool = True

class BacktestReportResponse(BaseModel):
    id: int
    user_id: int
    username: str
    name: str
    strategy_name: str
    symbol: str
    period: str
    start_date: str
    end_date: str
    total_trades: int
    win_rate: float
    profit_factor: float
    max_drawdown: float
    sharpe_ratio: Optional[float]
    total_return: float
    annualized_return: Optional[float]
    equity_curve: Optional[str]
    trades_summary: Optional[str]
    chart_data: Optional[str]
    notes: Optional[str]
    is_public: bool
    likes_count: int
    views_count: int
    created_at: str

class PortfolioStats(BaseModel):
    total_trades: int
    total_pnl: float
    win_rate: float
    best_trade: float
    worst_trade: float
    avg_trade: float
    current_streak: str
    largest_win_pct: float
    largest_loss_pct: float

# ========== 交易记录 ==========

@router.get("/trades", response_model=List[TradeRecordResponse])
def get_my_trades(limit: int = 50, offset: int = 0, symbol: str = None,
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取我的交易记录"""
    from app.models import TradeRecord
    query = db.query(TradeRecord).filter(TradeRecord.user_id == user.id)
    if symbol:
        query = query.filter(TradeRecord.symbol == symbol)
    trades = query.order_by(TradeRecord.created_at.desc()).offset(offset).limit(limit).all()
    return [_trade_to_response(t) for t in trades]

@router.post("/trades", response_model=TradeRecordResponse)
def add_trade(data: TradeRecordCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """添加交易记录"""
    from app.models import TradeRecord
    
    # 计算盈亏
    pnl = data.pnl
    pnl_pct = data.pnl_pct
    if data.exit_price and not pnl:
        pnl = (data.exit_price - data.entry_price) * data.quantity
        if data.direction == 'short':
            pnl = -pnl
        pnl_pct = (data.exit_price - data.entry_price) / data.entry_price * 100
        if data.direction == 'short':
            pnl_pct = -pnl_pct
    
    trade = TradeRecord(
        user_id=user.id,
        symbol=data.symbol,
        direction=data.direction,
        entry_price=data.entry_price,
        exit_price=data.exit_price,
        entry_time=datetime.fromisoformat(data.entry_time),
        exit_time=datetime.fromisoformat(data.exit_time) if data.exit_time else None,
        quantity=data.quantity,
        pnl=pnl,
        pnl_pct=pnl_pct,
        strategy_name=data.strategy_name,
        notes=data.notes
    )
    db.add(trade)
    db.commit()
    
    return _trade_to_response(trade)

@router.get("/trades/stats", response_model=PortfolioStats)
def get_trade_stats(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取交易统计"""
    from app.models import TradeRecord
    from sqlalchemy import func
    
    trades = db.query(TradeRecord).filter(
        TradeRecord.user_id == user.id,
        TradeRecord.pnl.isnot(None)
    ).all()
    
    if not trades:
        return PortfolioStats(
            total_trades=0, total_pnl=0, win_rate=0,
            best_trade=0, worst_trade=0, avg_trade=0,
            current_streak="0胜0负", largest_win_pct=0, largest_loss_pct=0
        )
    
    total = len(trades)
    wins = [t for t in trades if t.pnl and t.pnl > 0]
    total_pnl = sum(t.pnl for t in trades if t.pnl)
    
    return PortfolioStats(
        total_trades=total,
        total_pnl=total_pnl,
        win_rate=len(wins) / total * 100,
        best_trade=max(t.pnl for t in trades if t.pnl),
        worst_trade=min(t.pnl for t in trades if t.pnl),
        avg_trade=total_pnl / total,
        current_streak=f"{len(wins)}胜{total-len(wins)}负",
        largest_win_pct=max(t.pnl_pct for t in trades if t.pnl_pct) or 0,
        largest_loss_pct=min(t.pnl_pct for t in trades if t.pnl_pct) or 0
    )

@router.get("/trades/{trade_id}")
def delete_trade(trade_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """删除交易记录"""
    from app.models import TradeRecord
    trade = db.query(TradeRecord).filter(
        TradeRecord.id == trade_id,
        TradeRecord.user_id == user.id
    ).first()
    if not trade:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete(trade)
    db.commit()
    return {"ok": True}

# ========== 回测报告 ==========

@router.get("/reports", response_model=List[BacktestReportResponse])
def get_my_reports(limit: int = 20, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取我的回测报告"""
    from app.models import BacktestReport
    reports = db.query(BacktestReport).filter(
        BacktestReport.user_id == user.id
    ).order_by(BacktestReport.created_at.desc()).limit(limit).all()
    return [_report_to_response(r, user.username) for r in reports]

@router.get("/reports/public", response_model=List[BacktestReportResponse])
def get_public_reports(limit: int = 20, offset: int = 0, search: str = None,
                       db: Session = Depends(get_db)):
    """获取公开回测报告"""
    from app.models import BacktestReport
    query = db.query(BacktestReport).filter(BacktestReport.is_public == True)
    if search:
        query = query.filter(
            (BacktestReport.name.ilike(f"%{search}%")) |
            (BacktestReport.strategy_name.ilike(f"%{search}%")) |
            (BacktestReport.symbol.ilike(f"%{search}%"))
        )
    reports = query.order_by(BacktestReport.created_at.desc()).offset(offset).limit(limit).all()
    return [_report_to_response(r) for r in reports]

@router.get("/reports/{report_id}", response_model=BacktestReportResponse)
def get_report(report_id: int, db: Session = Depends(get_db)):
    """获取回测报告详情"""
    from app.models import BacktestReport
    report = db.query(BacktestReport).filter(BacktestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    # 增加浏览数
    report.views_count += 1
    db.commit()
    
    return _report_to_response(report)

@router.post("/reports", response_model=BacktestReportResponse)
def create_report(data: BacktestReportCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """创建回测报告"""
    from app.models import BacktestReport
    
    report = BacktestReport(
        user_id=user.id,
        name=data.name,
        strategy_name=data.strategy_name,
        symbol=data.symbol,
        period=data.period,
        start_date=data.start_date,
        end_date=data.end_date,
        total_trades=data.total_trades,
        win_rate=data.win_rate,
        profit_factor=data.profit_factor,
        max_drawdown=data.max_drawdown,
        sharpe_ratio=data.sharpe_ratio,
        total_return=data.total_return,
        annualized_return=data.annualized_return,
        equity_curve=data.equity_curve,
        trades_summary=data.trades_summary,
        chart_data=data.chart_data,
        notes=data.notes,
        is_public=data.is_public
    )
    db.add(report)
    db.commit()
    
    return _report_to_response(report, user.username)

@router.put("/reports/{report_id}", response_model=BacktestReportResponse)
def update_report(report_id: int, data: BacktestReportCreate, 
                  db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """更新回测报告"""
    from app.models import BacktestReport
    report = db.query(BacktestReport).filter(
        BacktestReport.id == report_id,
        BacktestReport.user_id == user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    for field in ['name', 'strategy_name', 'symbol', 'period', 'start_date', 'end_date',
                  'total_trades', 'win_rate', 'profit_factor', 'max_drawdown', 'sharpe_ratio',
                  'total_return', 'annualized_return', 'equity_curve', 'trades_summary',
                  'chart_data', 'notes', 'is_public']:
        if hasattr(data, field):
            setattr(report, field, getattr(data, field))
    
    db.commit()
    return _report_to_response(report, user.username)

@router.delete("/reports/{report_id}")
def delete_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """删除回测报告"""
    from app.models import BacktestReport
    report = db.query(BacktestReport).filter(
        BacktestReport.id == report_id,
        BacktestReport.user_id == user.id
    ).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    db.delete(report)
    db.commit()
    return {"ok": True}

@router.post("/reports/{report_id}/like")
def like_report(report_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """点赞回测报告"""
    from app.models import BacktestReport, BacktestLike
    
    report = db.query(BacktestReport).filter(BacktestReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="报告不存在")
    
    existing = db.query(BacktestLike).filter(
        BacktestLike.report_id == report_id,
        BacktestLike.user_id == user.id
    ).first()
    
    if existing:
        db.delete(existing)
        report.likes_count -= 1
        liked = False
    else:
        like = BacktestLike(report_id=report_id, user_id=user.id)
        db.add(like)
        report.likes_count += 1
        liked = True
    
    db.commit()
    return {"liked": liked, "count": report.likes_count}

# ========== 辅助函数 ==========

def _trade_to_response(t) -> TradeRecordResponse:
    return TradeRecordResponse(
        id=t.id,
        user_id=t.user_id,
        username=t.user.username,
        symbol=t.symbol,
        direction=t.direction,
        entry_price=t.entry_price,
        exit_price=t.exit_price,
        entry_time=t.entry_time.isoformat(),
        exit_time=t.exit_time.isoformat() if t.exit_time else None,
        quantity=t.quantity,
        pnl=t.pnl,
        pnl_pct=t.pnl_pct,
        strategy_name=t.strategy_name,
        notes=t.notes,
        created_at=t.created_at.isoformat()
    )

def _report_to_response(r, current_username: str = None) -> BacktestReportResponse:
    username = r.user.username if r.user else "Unknown"
    return BacktestReportResponse(
        id=r.id,
        user_id=r.user_id,
        username=username,
        name=r.name,
        strategy_name=r.strategy_name,
        symbol=r.symbol,
        period=r.period,
        start_date=r.start_date,
        end_date=r.end_date,
        total_trades=r.total_trades,
        win_rate=r.win_rate,
        profit_factor=r.profit_factor,
        max_drawdown=r.max_drawdown,
        sharpe_ratio=r.sharpe_ratio,
        total_return=r.total_return,
        annualized_return=r.annualized_return,
        equity_curve=r.equity_curve,
        trades_summary=r.trades_summary,
        chart_data=r.chart_data,
        notes=r.notes,
        is_public=r.is_public,
        likes_count=r.likes_count or 0,
        views_count=r.views_count or 0,
        created_at=r.created_at.isoformat()
    )
