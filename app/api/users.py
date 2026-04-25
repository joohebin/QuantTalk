from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, Form, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_
from app.database import get_db
from app.models import User, Notification, FriendRequest, friendships
from app.auth import get_current_user, hash_password, verify_password
from app.schemas import FriendRequestCreate, FriendRequestResponse, FriendResponse, FriendStatusResponse

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


# === Friend Request ===
@router.post("/friend-request")
def send_friend_request(req: FriendRequestCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if req.to_user_id == current_user.id:
        raise HTTPException(400, "cannot send friend request to yourself")
    target = db.query(User).filter(User.id == req.to_user_id).first()
    if not target:
        raise HTTPException(404, "user not found")
    # 检查是否已经是好友
    is_friend = db.query(friendships).filter(
        or_(
            and_(friendships.c.user_id == current_user.id, friendships.c.friend_id == req.to_user_id),
            and_(friendships.c.user_id == req.to_user_id, friendships.c.friend_id == current_user.id)
        )
    ).first()
    if is_friend:
        raise HTTPException(400, "already friends")
    # 检查是否已有待处理的申请
    existing = db.query(FriendRequest).filter(
        or_(
            and_(FriendRequest.from_user_id == current_user.id, FriendRequest.to_user_id == req.to_user_id),
            and_(FriendRequest.from_user_id == req.to_user_id, FriendRequest.to_user_id == current_user.id)
        ),
        FriendRequest.status == "PENDING"
    ).first()
    if existing:
        raise HTTPException(400, "friend request already exists")
    # 创建好友申请
    friend_req = FriendRequest(from_user_id=current_user.id, to_user_id=req.to_user_id, message=req.message or "")
    db.add(friend_req)
    # 发送通知
    notif = Notification(user_id=req.to_user_id, type="friend_request",
                       content=f"{current_user.username} sent you a friend request", from_user_id=current_user.id)
    db.add(notif)
    db.commit()
    return {"message": "friend request sent", "request_id": friend_req.id}


@router.get("/friend-status/{user_id}")
def get_friend_status(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user_id == current_user.id:
        return {"is_friend": False, "has_pending_request_from_me": False, "has_pending_request_to_me": False}
    # 检查是否已是好友
    is_friend = db.query(friendships).filter(
        or_(
            and_(friendships.c.user_id == current_user.id, friendships.c.friend_id == user_id),
            and_(friendships.c.user_id == user_id, friendships.c.friend_id == current_user.id)
        )
    ).first()
    # 检查我发出的待处理申请
    my_request = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == current_user.id,
        FriendRequest.to_user_id == user_id,
        FriendRequest.status == "PENDING"
    ).first()
    # 检查收到的待处理申请
    their_request = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == user_id,
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "PENDING"
    ).first()
    return {
        "is_friend": is_friend is not None,
        "has_pending_request_from_me": my_request is not None,
        "has_pending_request_to_me": their_request is not None,
        "request_id": their_request.id if their_request else (my_request.id if my_request else None)
    }


@router.get("/friend-requests")
def get_friend_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 获取收到的好友申请
    requests = db.query(FriendRequest).filter(
        FriendRequest.to_user_id == current_user.id,
        FriendRequest.status == "PENDING"
    ).order_by(FriendRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "from_user_id": r.from_user_id,
            "to_user_id": r.to_user_id,
            "message": r.message,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "from_username": r.from_user.username,
            "from_avatar": r.from_user.avatar,
        }
        for r in requests
    ]


@router.get("/friend-requests/sent")
def get_sent_friend_requests(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 获取发出的好友申请
    requests = db.query(FriendRequest).filter(
        FriendRequest.from_user_id == current_user.id,
        FriendRequest.status == "PENDING"
    ).order_by(FriendRequest.created_at.desc()).all()
    return [
        {
            "id": r.id,
            "from_user_id": r.from_user_id,
            "to_user_id": r.to_user_id,
            "message": r.message,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "to_username": r.to_user.username,
            "to_avatar": r.to_user.avatar,
        }
        for r in requests
    ]


@router.post("/friend-request/{request_id}/accept")
def accept_friend_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "friend request not found")
    if req.to_user_id != current_user.id:
        raise HTTPException(403, "not authorized to accept this request")
    if req.status != "PENDING":
        raise HTTPException(400, "request already processed")
    # 更新申请状态
    req.status = "ACCEPTED"
    # 创建好友关系（双向）
    db.execute(friendships.insert().values(user_id=current_user.id, friend_id=req.from_user_id))
    db.execute(friendships.insert().values(user_id=req.from_user_id, friend_id=current_user.id))
    # 发送通知
    notif = Notification(user_id=req.from_user_id, type="friend_accepted",
                        content=f"{current_user.username} accepted your friend request", from_user_id=current_user.id)
    db.add(notif)
    db.commit()
    return {"message": "friend request accepted"}


@router.post("/friend-request/{request_id}/reject")
def reject_friend_request(request_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    req = db.query(FriendRequest).filter(FriendRequest.id == request_id).first()
    if not req:
        raise HTTPException(404, "friend request not found")
    if req.to_user_id != current_user.id:
        raise HTTPException(403, "not authorized to reject this request")
    if req.status != "PENDING":
        raise HTTPException(400, "request already processed")
    req.status = "REJECTED"
    # 发送通知
    notif = Notification(user_id=req.from_user_id, type="friend_rejected",
                        content=f"{current_user.username} rejected your friend request", from_user_id=current_user.id)
    db.add(notif)
    db.commit()
    return {"message": "friend request rejected"}


@router.get("/friends")
def get_friends(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 获取好友列表
    friend_ids = db.query(friendships.c.friend_id).filter(friendships.c.user_id == current_user.id).all()
    friend_ids = [f[0] for f in friend_ids]
    friends = db.query(User).filter(User.id.in_(friend_ids)).all() if friend_ids else []
    return [
        {
            "id": f.id,
            "username": f.username,
            "avatar": f.avatar,
            "bio": f.bio,
            "is_online": f.is_online,
            "friends_count": db.query(friendships).filter(
                or_(friendships.c.user_id == f.id, friendships.c.friend_id == f.id)
            ).count(),
            "created_at": f.created_at.isoformat(),
        }
        for f in friends
    ]


@router.delete("/friend/{user_id}")
def remove_friend(user_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 删除好友关系（双向）
    db.query(friendships).filter(
        or_(
            and_(friendships.c.user_id == current_user.id, friendships.c.friend_id == user_id),
            and_(friendships.c.user_id == user_id, friendships.c.friend_id == current_user.id)
        )
    ).delete(synchronize_session=False)
    db.commit()
    return {"message": "friend removed"}
