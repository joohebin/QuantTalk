from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime
from app.database import get_db
from app.models import User, PrivateMessage, Notification
from app.auth import get_current_user

router = APIRouter(tags=["私信"])


class MessageCreate(BaseModel):
    receiver_id: int
    content: str


class MessageResponse(BaseModel):
    id: int
    sender_id: int
    receiver_id: int
    content: str
    is_read: bool
    created_at: datetime
    sender: dict = None
    receiver: dict = None

    class Config:
        from_attributes = True


class ConversationResponse(BaseModel):
    user_id: int
    username: str
    avatar: str
    last_message: str
    last_time: datetime
    unread_count: int


def user_to_dict(user):
    return {"id": user.id, "username": user.username, "avatar": user.avatar, "is_online": user.is_online}


@router.post("/", response_model=MessageResponse)
async def send_message(message: MessageCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    receiver = db.query(User).filter(User.id == message.receiver_id).first()
    if not receiver:
        raise HTTPException(status_code=404, detail="用户不存在")
    if message.receiver_id == current_user.id:
        raise HTTPException(status_code=400, detail="不能给自己发私信")
    db_message = PrivateMessage(sender_id=current_user.id, receiver_id=message.receiver_id, content=message.content)
    db.add(db_message)
    # 发送私信通知
    notif = Notification(
        user_id=message.receiver_id,
        type="message",
        content=f"{current_user.username} sent you a private message",
        from_user_id=current_user.id
    )
    db.add(notif)
    db.commit()
    db.refresh(db_message)
    return MessageResponse(id=db_message.id, sender_id=db_message.sender_id, receiver_id=db_message.receiver_id, content=db_message.content, is_read=db_message.is_read, created_at=db_message.created_at, sender=user_to_dict(current_user), receiver=user_to_dict(receiver))


@router.get("/conversations")
async def get_conversations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    messages = db.query(PrivateMessage).filter((PrivateMessage.sender_id == current_user.id) | (PrivateMessage.receiver_id == current_user.id)).order_by(PrivateMessage.created_at.desc()).all()
    conversations = {}
    for msg in messages:
        other_user_id = msg.receiver_id if msg.sender_id == current_user.id else msg.sender_id
        other_user = msg.receiver if msg.sender_id == current_user.id else msg.sender
        if other_user_id not in conversations:
            unread_count = db.query(PrivateMessage).filter(PrivateMessage.sender_id == other_user_id, PrivateMessage.receiver_id == current_user.id, PrivateMessage.is_read == False).count()
            conversations[other_user_id] = {"user_id": other_user_id, "username": other_user.username, "avatar": other_user.avatar, "last_message": msg.content[:100], "last_time": str(msg.created_at), "unread_count": unread_count}
    return list(conversations.values())


@router.get("/unread/count")
async def get_unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    count = db.query(PrivateMessage).filter(
        PrivateMessage.receiver_id == current_user.id,
        PrivateMessage.is_read == False
    ).count()
    return {"unread": count}


@router.get("/{user_id}")
async def get_messages_with_user(user_id: int, limit: int = 50, offset: int = 0, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    other_user = db.query(User).filter(User.id == user_id).first()
    if not other_user:
        raise HTTPException(status_code=404, detail="用户不存在")
    messages = db.query(PrivateMessage).filter(((PrivateMessage.sender_id == current_user.id) & (PrivateMessage.receiver_id == user_id)) | ((PrivateMessage.sender_id == user_id) & (PrivateMessage.receiver_id == current_user.id))).order_by(PrivateMessage.created_at.desc()).limit(limit).offset(offset).all()
    db.query(PrivateMessage).filter(PrivateMessage.sender_id == user_id, PrivateMessage.receiver_id == current_user.id, PrivateMessage.is_read == False).update({"is_read": True})
    db.commit()
    return [{"id": msg.id, "sender_id": msg.sender_id, "receiver_id": msg.receiver_id, "content": msg.content, "is_read": msg.is_read, "created_at": str(msg.created_at), "sender": user_to_dict(msg.sender), "receiver": user_to_dict(msg.receiver)} for msg in reversed(messages)]


@router.post("/{message_id}/read")
async def mark_as_read(message_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    message = db.query(PrivateMessage).filter(PrivateMessage.id == message_id, PrivateMessage.receiver_id == current_user.id).first()
    if not message:
        raise HTTPException(status_code=404, detail="私信不存在")
    message.is_read = True
    db.commit()
    return {"status": "ok"}
