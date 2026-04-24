from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import Notification, User
from app.auth import get_current_user

router = APIRouter()


@router.get("/")
def get_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notifs = db.query(Notification).filter(Notification.user_id == current_user.id).order_by(desc(Notification.created_at)).limit(50).all()
    results = []
    for n in notifs:
        from_user = db.query(User).filter(User.id == n.from_user_id).first() if n.from_user_id else None
        results.append({
            "id": n.id, "type": n.type, "content": n.content,
            "from_user_id": n.from_user_id, "post_id": n.post_id,
            "is_read": n.is_read, "created_at": n.created_at.isoformat(),
            "from_username": from_user.username if from_user else None,
            "from_avatar": from_user.avatar if from_user else None,
        })
    unread = db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).count()
    return {"notifications": results, "unread_count": unread}


@router.post("/{notif_id}/read")
def mark_read(notif_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    notif = db.query(Notification).filter(Notification.id == notif_id, Notification.user_id == current_user.id).first()
    if not notif:
        raise HTTPException(404, "通知不存在")
    notif.is_read = True
    db.commit()
    return {"message": "已读"}


@router.post("/read-all")
def mark_all_read(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    db.query(Notification).filter(Notification.user_id == current_user.id, Notification.is_read == False).update({"is_read": True})
    db.commit()
    return {"message": "全部已读"}
