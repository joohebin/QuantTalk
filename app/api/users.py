from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Post
from app.schemas import UserUpdate
from app.auth import get_current_user

router = APIRouter()


@router.get("/profile/{username}")
def get_user_profile(username: str, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "用户不存在")
    return {
        "id": user.id,
        "username": user.username,
        "avatar": user.avatar,
        "bio": user.bio,
        "followers_count": len(user.followers),
        "following_count": len(user.following),
        "posts_count": len(user.posts),
        "created_at": user.created_at.isoformat(),
    }


@router.put("/profile")
def update_profile(data: UserUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if data.avatar is not None:
        current_user.avatar = data.avatar
    if data.bio is not None:
        current_user.bio = data.bio
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
        return {"following": True, "message": "关注成功"}
