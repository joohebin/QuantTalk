from typing import Optional
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Notification
from app.auth import get_current_user, hash_password, verify_password
from app.schemas import UserUpdate, NotificationResponse

router = APIRouter()


@router.get("/profile/{username}")
def get_user_profile(username: str, current_user: Optional[User] = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "用户不存在")

    is_following = False
    if current_user and current_user.id != user.id:
        is_following = user in current_user.following

    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "bio": user.bio,
        "is_online": user.is_online,
        "followers_count": len(user.followers),
        "following_count": len(user.following),
        "posts_count": len(user.posts),
        "is_following": is_following,
        "created_at": user.created_at.isoformat(),
    }


@router.put("/profile")
def update_profile(data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.avatar is not None:
        current_user.avatar = data.avatar
    if data.bio is not None:
        current_user.bio = data.bio
    if data.old_password and data.new_password:
        if not verify_password(data.old_password, current_user.hashed_password):
            raise HTTPException(400, "原密码错误")
        current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "更新成功"}


@router.post("/follow/{user_id}")
def toggle_follow(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(400, "不能关注自己")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "用户不存在")

    if target in current_user.following:
        current_user.following.remove(target)
        db.commit()
        return {"following": False, "message": "取消关注"}
    else:
        current_user.following.append(target)
        db.commit()
        # Create notification
        notif = Notification(
            user_id=target.id, type="follow",
            content=f"{current_user.username} 关注了你",
            from_user_id=current_user.id,
        )
        db.add(notif)
        db.commit()
        return {"following": True, "message": "关注成功"}


@router.get("/search")
def search_users(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    if not q:
        return []
    users = db.query(User).filter(User.username.contains(q)).limit(limit).all()
    return [{"id": u.id, "username": u.username, "avatar": u.avatar, "bio": u.bio} for u in users]
