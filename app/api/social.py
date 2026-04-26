"""
社区互动 API - 关注/粉丝/收藏/转发
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(prefix="/api/social", tags=["社区互动"])


# ========== 数据模型 ==========

class FollowResponse(BaseModel):
    user_id: int
    username: str
    avatar: str
    is_following: bool
    is_follower: bool
    is_mutual: bool
    bio: Optional[str] = None


class FollowerListResponse(BaseModel):
    total: int
    users: List[FollowResponse]


class FavoriteItem(BaseModel):
    id: int
    item_type: str  # signal, strategy, post, chart
    item_id: int
    title: str
    summary: str
    created_at: str


class ShareRequest(BaseModel):
    item_type: str  # signal, strategy, post
    item_id: int
    target_type: str  # community, friends
    content: Optional[str] = None


# ========== 关注/粉丝 ==========

@router.post("/{user_id}/follow")
async def follow_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """关注用户"""
    if user_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能关注自己")
    
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    from app.models import UserFollow
    # 检查是否已关注
    existing = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == user_id
    ).first()
    
    if existing:
        return {"ok": True, "following": True, "message": "已关注"}
    
    # 创建关注关系
    follow = UserFollow(follower_id=current_user.id, following_id=user_id)
    db.add(follow)
    
    # 更新粉丝数
    target.follower_count = (target.follower_count or 0) + 1
    current_user.following_count = (current_user.following_count or 0) + 1
    
    db.commit()
    
    return {"ok": True, "following": True, "message": "关注成功"}


@router.delete("/{user_id}/follow")
async def unfollow_user(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """取消关注"""
    from app.models import UserFollow
    
    follow = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == user_id
    ).first()
    
    if not follow:
        return {"ok": True, "following": False, "message": "未关注"}
    
    db.delete(follow)
    
    target = db.query(User).filter(User.id == user_id).first()
    if target:
        target.follower_count = max(0, (target.follower_count or 0) - 1)
    current_user.following_count = max(0, (current_user.following_count or 0) - 1)
    
    db.commit()
    
    return {"ok": True, "following": False, "message": "已取消关注"}


@router.get("/{user_id}/follow-status")
async def get_follow_status(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取关注状态"""
    from app.models import UserFollow
    
    is_following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id,
        UserFollow.following_id == user_id
    ).first() is not None
    
    is_follower = db.query(UserFollow).filter(
        UserFollow.follower_id == user_id,
        UserFollow.following_id == current_user.id
    ).first() is not None
    
    return {
        "is_following": is_following,
        "is_follower": is_follower,
        "is_mutual": is_following and is_follower
    }


@router.get("/{user_id}/followers", response_model=FollowerListResponse)
async def get_followers(user_id: int, limit: int = 20, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取粉丝列表"""
    from app.models import UserFollow
    
    # 获取粉丝
    followers = db.query(UserFollow).filter(
        UserFollow.following_id == user_id
    ).order_by(UserFollow.created_at.desc()).offset(offset).limit(limit).all()
    
    total = db.query(UserFollow).filter(UserFollow.following_id == user_id).count()
    
    # 获取当前用户关注的ID列表（用于判断互相关注）
    my_following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id
    ).all()
    my_following_ids = set(f.following_id for f in my_following)
    
    users = []
    for f in followers:
        u = f.follower
        users.append(FollowResponse(
            user_id=u.id,
            username=u.username,
            avatar=u.avatar or "",
            is_following=u.id in my_following_ids,
            is_follower=True,
            is_mutual=u.id in my_following_ids,
            bio=getattr(u, 'bio', None)
        ))
    
    return FollowerListResponse(total=total, users=users)


@router.get("/{user_id}/following", response_model=FollowerListResponse)
async def get_following(user_id: int, limit: int = 20, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取关注列表"""
    from app.models import UserFollow
    
    following = db.query(UserFollow).filter(
        UserFollow.follower_id == user_id
    ).order_by(UserFollow.created_at.desc()).offset(offset).limit(limit).all()
    
    total = db.query(UserFollow).filter(UserFollow.follower_id == user_id).count()
    
    # 获取当前用户关注的ID列表
    my_following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id
    ).all()
    my_following_ids = set(f.following_id for f in my_following)
    
    users = []
    for f in following:
        u = f.following
        users.append(FollowResponse(
            user_id=u.id,
            username=u.username,
            avatar=u.avatar or "",
            is_following=True,
            is_follower=u.id in my_following_ids,
            is_mutual=u.id in my_following_ids,
            bio=getattr(u, 'bio', None)
        ))
    
    return FollowerListResponse(total=total, users=users)


# ========== 收藏功能 ==========

@router.post("/favorites/{item_type}/{item_id}")
async def add_favorite(item_type: str, item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """添加收藏"""
    from app.models import Favorite
    
    # 检查是否已收藏
    existing = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.item_type == item_type,
        Favorite.item_id == item_id
    ).first()
    
    if existing:
        return {"ok": True, "favorited": True, "message": "已收藏"}
    
    # 获取标题
    title = await get_item_title(item_type, item_id, db)
    
    favorite = Favorite(
        user_id=current_user.id,
        item_type=item_type,
        item_id=item_id,
        title=title or f"{item_type} #{item_id}"
    )
    db.add(favorite)
    db.commit()
    
    return {"ok": True, "favorited": True, "message": "已添加收藏"}


@router.delete("/favorites/{item_type}/{item_id}")
async def remove_favorite(item_type: str, item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """取消收藏"""
    from app.models import Favorite
    
    favorite = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.item_type == item_type,
        Favorite.item_id == item_id
    ).first()
    
    if favorite:
        db.delete(favorite)
        db.commit()
    
    return {"ok": True, "favorited": False, "message": "已取消收藏"}


@router.get("/favorites")
async def get_favorites(item_type: Optional[str] = None, limit: int = 20, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取收藏列表"""
    from app.models import Favorite
    
    query = db.query(Favorite).filter(Favorite.user_id == current_user.id)
    
    if item_type:
        query = query.filter(Favorite.item_type == item_type)
    
    favorites = query.order_by(Favorite.created_at.desc()).offset(offset).limit(limit).all()
    total = query.count()
    
    return {
        "total": total,
        "items": [
            {
                "id": f.id,
                "item_type": f.item_type,
                "item_id": f.item_id,
                "title": f.title,
                "summary": f.title,
                "created_at": f.created_at.isoformat()
            }
            for f in favorites
        ]
    }


@router.get("/favorites/status/{item_type}/{item_id}")
async def check_favorite_status(item_type: str, item_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """检查收藏状态"""
    from app.models import Favorite
    
    is_favorited = db.query(Favorite).filter(
        Favorite.user_id == current_user.id,
        Favorite.item_type == item_type,
        Favorite.item_id == item_id
    ).first() is not None
    
    return {"is_favorited": is_favorited}


# ========== 分享功能 ==========

@router.post("/share")
async def share_item(data: ShareRequest, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """分享内容到社区/好友"""
    from app.models import ShareRecord
    
    # 获取原内容
    title = await get_item_title(data.item_type, data.item_id, db)
    
    share = ShareRecord(
        user_id=current_user.id,
        item_type=data.item_type,
        item_id=data.item_id,
        target_type=data.target_type,
        content=data.content or f"分享了 {title or data.item_type}"
    )
    db.add(share)
    db.commit()
    
    return {"ok": True, "share_id": share.id, "message": "分享成功"}


@router.get("/shares")
async def get_my_shares(limit: int = 20, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取我的分享记录"""
    from app.models import ShareRecord
    
    shares = db.query(ShareRecord).filter(
        ShareRecord.user_id == current_user.id
    ).order_by(ShareRecord.created_at.desc()).offset(offset).limit(limit).all()
    
    return {
        "total": len(shares),
        "shares": [
            {
                "id": s.id,
                "item_type": s.item_type,
                "item_id": s.item_id,
                "title": s.title or s.item_type,
                "content": s.content,
                "target_type": s.target_type,
                "created_at": s.created_at.isoformat()
            }
            for s in shares
        ]
    }


# ========== 辅助函数 ==========

async def get_item_title(item_type: str, item_id: int, db: Session):
    """获取内容标题"""
    from app.models import TradingSignal, Strategy, Post
    
    try:
        if item_type == "signal":
            item = db.query(TradingSignal).filter(TradingSignal.id == item_id).first()
            if item:
                return f"{item.symbol} {'多' if item.direction == 'LONG' else '空'} @ {item.entry_price}"
        elif item_type == "strategy":
            item = db.query(Strategy).filter(Strategy.id == item_id).first()
            if item:
                return item.name or "策略"
        elif item_type == "post":
            item = db.query(Post).filter(Post.id == item_id).first()
            if item:
                return item.content[:50] if item.content else "帖子"
    except:
        pass
    return None


# ========== 动态/动态流 ==========

@router.get("/feed")
async def get_social_feed(limit: int = 20, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取社交动态流（关注的人的更新）"""
    from app.models import UserFollow, TradingSignal, Strategy, PortfolioUpdate
    
    # 获取关注的人
    following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id
    ).all()
    following_ids = [f.following_id for f in following]
    following_ids.append(current_user.id)  # 也包含自己的
    
    activities = []
    
    # 获取交易信号
    signals = db.query(TradingSignal).filter(
        TradingSignal.user_id.in_(following_ids)
    ).order_by(TradingSignal.created_at.desc()).limit(limit // 2).all()
    
    for s in signals:
        activities.append({
            "type": "signal",
            "id": s.id,
            "user_id": s.user_id,
            "username": s.author.username if s.author else "未知",
            "avatar": s.author.avatar if s.author else "",
            "title": f"{s.symbol} {'做多' if s.direction == 'LONG' else '做空'} @ {s.entry_price}",
            "summary": s.notes[:100] if s.notes else "",
            "created_at": s.created_at.isoformat(),
            "likes_count": s.likes_count or 0,
            "comments_count": s.comments_count or 0
        })
    
    # 按时间排序
    activities.sort(key=lambda x: x["created_at"], reverse=True)
    
    return {
        "total": len(activities),
        "activities": activities[:limit]
    }


# ========== 用户关系推荐 ==========

@router.get("/suggestions")
async def get_follow_suggestions(limit: int = 10, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """获取关注推荐（基于共同关注）"""
    from app.models import UserFollow
    
    # 获取当前用户关注的人
    my_following = db.query(UserFollow).filter(
        UserFollow.follower_id == current_user.id
    ).all()
    my_following_ids = set(f.following_id for f in my_following)
    
    # 获取这些人也关注的用户（共同关注）
    if my_following_ids:
        suggestions = db.query(UserFollow).filter(
            UserFollow.follower_id.in_(my_following_ids),
            UserFollow.following_id.notin_(list(my_following_ids) + [current_user.id])
        ).all()
        
        # 统计被多少关注的人关注
        suggestion_scores = {}
        for s in suggestions:
            fid = s.following_id
            suggestion_scores[fid] = suggestion_scores.get(fid, 0) + 1
        
        # 按分数排序
        sorted_ids = sorted(suggestion_scores.keys(), key=lambda x: suggestion_scores[x], reverse=True)[:limit]
        
        users = []
        for uid in sorted_ids:
            u = db.query(User).filter(User.id == uid).first()
            if u:
                users.append({
                    "user_id": u.id,
                    "username": u.username,
                    "avatar": u.avatar or "",
                    "mutual_count": suggestion_scores[uid]
                })
        
        return {"suggestions": users}
    
    return {"suggestions": []}
