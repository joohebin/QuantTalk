from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User, Notification
from app.auth import get_current_user, hash_password, verify_password
from app.schemas import UserUpdate

router = APIRouter()


@router.get("/search")
def search_users(q: str = "", limit: int = 20, db: Session = Depends(get_db)):
    if not q:
        return []
    users = db.query(User).filter(User.username.contains(q)).limit(limit).all()
    return [{"id": u.id, "username": u.username, "avatar": u.avatar, "bio": u.bio} for u in users]


@router.get("/{user_id}")
def get_user_by_id(user_id: int, current_user: Any = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user not found")
    is_following = False
    if current_user and current_user.id != user.id:
        is_following = user in current_user.following
    return {
        "id": user.id, "username": user.username, "avatar": user.avatar,
        "bio": user.bio, "is_online": user.is_online,
        "followers_count": len(user.followers), "following_count": len(user.following),
        "posts_count": len(user.posts), "is_following": is_following,
        "created_at": user.created_at.isoformat(),
    }


@router.get("/profile/{username}")
def get_user_profile(username: str, current_user: Any = None, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user:
        raise HTTPException(404, "user not found")
    is_following = False
    if current_user and current_user.id != user.id:
        is_following = user in current_user.following
    return {
        "id": user.id, "username": user.username, "avatar": user.avatar,
        "bio": user.bio, "is_online": user.is_online,
        "followers_count": len(user.followers), "following_count": len(user.following),
        "posts_count": len(user.posts), "is_following": is_following,
        "created_at": user.created_at.isoformat(),
    }


@router.put("/profile")
async def update_profile(
    bio: Optional[str] = Form(None),
    avatar: Optional[UploadFile] = File(None),
    old_password: Optional[str] = Form(None),
    new_password: Optional[str] = Form(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    if avatar and avatar.filename:
        import os
        import uuid
        # 保存头像到 static/avatars/
        ext = os.path.splitext(avatar.filename)[1] or '.jpg'
        filename = f"{uuid.uuid4()}{ext}"
        avatar_path = f"static/avatars/{filename}"
        os.makedirs("static/avatars", exist_ok=True)
        with open(avatar_path, "wb") as f:
            content = await avatar.read()
            f.write(content)
        current_user.avatar = f"/{avatar_path}"
    if bio is not None:
        current_user.bio = bio
    if old_password and new_password:
        if not verify_password(old_password, current_user.hashed_password):
            raise HTTPException(400, "wrong password")
        current_user.hashed_password = hash_password(new_password)
    db.commit()
    return {"message": "ok", "avatar": current_user.avatar}


@router.post("/follow/{user_id}")
def toggle_follow(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        raise HTTPException(400, "cannot follow yourself")
    target = db.query(User).filter(User.id == user_id).first()
    if not target:
        raise HTTPException(404, "user not found")
    if target in current_user.following:
        current_user.following.remove(target)
        db.commit()
        return {"following": False, "message": "unfollowed"}
    else:
        current_user.following.append(target)
        db.commit()
        notif = Notification(user_id=target.id, type="follow",
                            content=f"{current_user.username} followed you", from_user_id=current_user.id)
        db.add(notif)
        db.commit()
        return {"following": True, "message": "followed"}
