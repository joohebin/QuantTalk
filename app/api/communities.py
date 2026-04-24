from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import User, Community, Channel, ChannelMessage, community_members
from app.auth import get_current_user
from app.schemas import CommunityCreate, CommunityUpdate, ChannelCreate, ChannelMessageCreate

router = APIRouter()


@router.get("/")
def list_communities(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    q: str = Query(""),
    current_user: Optional[User] = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Community).filter(Community.is_public == True)
    if q:
        query = query.filter(Community.display_name.contains(q) | Community.description.contains(q))
    total = query.count()
    communities = query.order_by(desc(Community.created_at)).offset((page - 1) * limit).limit(limit).all()

    results = []
    for c in communities:
        member_count = db.query(community_members).filter(community_members.c.community_id == c.id).count()
        channel_count = len(c.channels)
        is_member = False
        if current_user:
            is_member = db.query(community_members).filter_by(community_id=c.id, user_id=current_user.id).first() is not None
        results.append({
            "id": c.id, "name": c.name, "display_name": c.display_name,
            "description": c.description, "icon": c.icon,
            "owner_id": c.owner_id, "is_public": c.is_public,
            "members_count": member_count, "channels_count": channel_count,
            "is_member": is_member, "created_at": c.created_at.isoformat(),
        })
    return {"communities": results, "total": total, "page": page, "limit": limit}


@router.post("/")
def create_community(data: CommunityCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if db.query(Community).filter(Community.name == data.name).first():
        raise HTTPException(400, "社区名称已被使用")
    community = Community(
        name=data.name, display_name=data.display_name,
        description=data.description or "", icon=data.icon or "",
        owner_id=current_user.id,
    )
    db.add(community)
    db.commit()
    db.refresh(community)

    # Auto-add creator as owner
    db.execute(community_members.insert().values(community_id=community.id, user_id=current_user.id, role="owner"))
    # Create default channels
    general = Channel(community_id=community.id, name="general", channel_type="text", description="通用讨论", sort_order=0)
    random_ch = Channel(community_id=community.id, name="random", channel_type="text", description="闲聊", sort_order=1)
    voice_ch = Channel(community_id=community.id, name="语音大厅", channel_type="voice", description="语音聊天", sort_order=2)
    db.add_all([general, random_ch, voice_ch])
    db.commit()

    return {"id": community.id, "message": "社区创建成功"}


@router.get("/my")
def my_communities(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = db.query(community_members).filter(community_members.c.user_id == current_user.id).all()
    results = []
    for row in rows:
        c = db.query(Community).filter(Community.id == row.community_id).first()
        if c:
            results.append({
                "id": c.id, "name": c.name, "display_name": c.display_name,
                "icon": c.icon, "members_count": db.query(community_members).filter(community_members.c.community_id == c.id).count(),
            })
    return results


@router.get("/{community_id}")
def get_community(community_id: int, current_user: Optional[User] = None, db: Session = Depends(get_db)):
    c = db.query(Community).filter(Community.id == community_id).first()
    if not c:
        raise HTTPException(404, "社区不存�?)
    member_count = db.query(community_members).filter(community_members.c.community_id == c.id).count()
    is_member = False
    if current_user:
        is_member = db.query(community_members).filter_by(community_id=c.id, user_id=current_user.id).first() is not None
    return {
        "id": c.id, "name": c.name, "display_name": c.display_name,
        "description": c.description, "icon": c.icon,
        "owner_id": c.owner_id, "is_public": c.is_public,
        "members_count": member_count, "channels_count": len(c.channels),
        "is_member": is_member, "created_at": c.created_at.isoformat(),
        "channels": [{"id": ch.id, "name": ch.name, "channel_type": ch.channel_type, "description": ch.description, "sort_order": ch.sort_order} for ch in sorted(c.channels, key=lambda x: x.sort_order)],
    }


@router.put("/{community_id}")
def update_community(community_id: int, data: CommunityUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Community).filter(Community.id == community_id).first()
    if not c or c.owner_id != current_user.id:
        raise HTTPException(403, "无权修改")
    for k in ("display_name", "description", "icon"):
        if hasattr(data, k) and getattr(data, k) is not None:
            setattr(c, k, getattr(data, k))
    db.commit()
    return {"message": "更新成功"}


@router.post("/{community_id}/join")
def join_community(community_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Community).filter(Community.id == community_id).first()
    if not c:
        raise HTTPException(404, "社区不存�?)
    existing = db.query(community_members).filter_by(community_id=community_id, user_id=current_user.id).first()
    if existing:
        db.execute(community_members.delete().where(community_members.c.community_id == community_id, community_members.c.user_id == current_user.id))
        db.commit()
        return {"joined": False, "message": "已退出社�?}
    db.execute(community_members.insert().values(community_id=community_id, user_id=current_user.id, role="member"))
    db.commit()
    return {"joined": True, "message": "加入成功"}


# === Channels ===
@router.get("/{community_id}/channels")
def get_channels(community_id: int, db: Session = Depends(get_db)):
    channels = db.query(Channel).filter(Channel.community_id == community_id).order_by(Channel.sort_order).all()
    return [{"id": ch.id, "name": ch.name, "channel_type": ch.channel_type, "description": ch.description} for ch in channels]


@router.post("/{community_id}/channels")
def create_channel(community_id: int, data: ChannelCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.query(Community).filter(Community.id == community_id).first()
    if not c or c.owner_id != current_user.id:
        raise HTTPException(403, "无权创建频道")
    max_order = db.query(Channel).filter(Channel.community_id == community_id).count()
    ch = Channel(community_id=community_id, name=data.name, channel_type=data.channel_type,
                 description=data.description or "", sort_order=max_order)
    db.add(ch)
    db.commit()
    db.refresh(ch)
    return {"id": ch.id, "message": "频道创建成功"}


# === Messages ===
@router.get("/{community_id}/channels/{channel_id}/messages")
def get_messages(community_id: int, channel_id: int, limit: int = Query(50, ge=1, le=100), db: Session = Depends(get_db)):
    ch = db.query(Channel).filter(Channel.id == channel_id, Channel.community_id == community_id).first()
    if not ch:
        raise HTTPException(404, "频道不存�?)
    msgs = db.query(ChannelMessage).filter(ChannelMessage.channel_id == channel_id).order_by(ChannelMessage.created_at).limit(limit).all()
    return [{"id": m.id, "content": m.content, "author_id": m.author_id, "created_at": m.created_at.isoformat(),
             "author": {"id": m.author.id, "username": m.author.username, "avatar": m.author.avatar}} for m in msgs]
