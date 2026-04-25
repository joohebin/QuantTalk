"""
群聊系统 API
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import secrets
import string

from app.database import get_db
from app.models import User
from app.auth import get_current_user

def generate_code(length=8):
    """生成随机邀请码"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

router = APIRouter(prefix="/api/groups", tags=["群聊"])

# ========== 模型 ==========

class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    avatar: Optional[str] = None
    is_private: bool = False

class GroupUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    avatar: Optional[str] = None

class GroupResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    avatar: Optional[str]
    owner_id: int
    member_count: int
    created_at: str
    is_private: bool

class GroupMember(BaseModel):
    id: int
    username: str
    avatar: Optional[str]
    is_owner: bool
    is_admin: bool
    joined_at: str

class GroupMessageCreate(BaseModel):
    content: str
    reply_to: Optional[int] = None

class GroupMessageResponse(BaseModel):
    id: int
    group_id: int
    author_id: int
    author_username: str
    content: str
    reply_to: Optional[int]
    created_at: str

# ========== 群组 CRUD ==========

@router.get("/", response_model=List[GroupResponse])
def get_my_groups(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取我加入的群组"""
    from app.models import GroupMember as GM
    memberships = db.query(GM).filter(GM.user_id == user.id).all()
    groups = []
    for m in memberships:
        g = m.group
        member_count = db.query(GM).filter(GM.group_id == g.id).count()
        groups.append(GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            avatar=g.avatar,
            owner_id=g.owner_id,
            member_count=member_count,
            created_at=g.created_at.isoformat(),
            is_private=g.is_private
        ))
    return groups

@router.post("/", response_model=GroupResponse)
def create_group(data: GroupCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """创建群组"""
    from app.models import Group, GroupMember as GM
    
    group = Group(
        name=data.name,
        description=data.description,
        avatar=data.avatar,
        owner_id=user.id,
        is_private=data.is_private,
        invite_code=generate_code()
    )
    db.add(group)
    db.flush()
    
    # 自动加入创建者
    member = GM(group_id=group.id, user_id=user.id, is_owner=True, is_admin=True)
    db.add(member)
    db.commit()
    
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        avatar=group.avatar,
        owner_id=group.owner_id,
        member_count=1,
        created_at=group.created_at.isoformat(),
        is_private=group.is_private
    )

@router.get("/{group_id}", response_model=GroupResponse)
def get_group(group_id: int, db: Session = Depends(get_db)):
    """获取群组信息"""
    from app.models import Group, GroupMember as GM
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    member_count = db.query(GM).filter(GM.group_id == group.id).count()
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        avatar=group.avatar,
        owner_id=group.owner_id,
        member_count=member_count,
        created_at=group.created_at.isoformat(),
        is_private=group.is_private
    )

@router.put("/{group_id}", response_model=GroupResponse)
def update_group(group_id: int, data: GroupUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """更新群组"""
    from app.models import Group, GroupMember as GM
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    if group.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有群主可以修改")
    
    if data.name: group.name = data.name
    if data.description is not None: group.description = data.description
    if data.avatar is not None: group.avatar = data.avatar
    db.commit()
    
    member_count = db.query(GM).filter(GM.group_id == group.id).count()
    return GroupResponse(
        id=group.id,
        name=group.name,
        description=group.description,
        avatar=group.avatar,
        owner_id=group.owner_id,
        member_count=member_count,
        created_at=group.created_at.isoformat(),
        is_private=group.is_private
    )

@router.delete("/{group_id}")
def delete_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """解散群组"""
    from app.models import Group, GroupMember as GM, GroupMessage
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    if group.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有群主可以解散")
    
    # 删除消息和成员
    db.query(GroupMessage).filter(GroupMessage.group_id == group_id).delete()
    db.query(GM).filter(GM.group_id == group_id).delete()
    db.delete(group)
    db.commit()
    return {"ok": True}

# ========== 成员管理 ==========

@router.get("/{group_id}/members", response_model=List[GroupMember])
def get_group_members(group_id: int, db: Session = Depends(get_db)):
    """获取群成员"""
    from app.models import Group, GroupMember as GM
    members = db.query(GM).filter(GM.group_id == group_id).all()
    result = []
    for m in members:
        u = m.user
        result.append(GroupMember(
            id=u.id,
            username=u.username,
            avatar=u.avatar,
            is_owner=m.is_owner,
            is_admin=m.is_admin,
            joined_at=m.joined_at.isoformat()
        ))
    return result

@router.post("/{group_id}/join/{invite_code}")
def join_group_by_code(group_id: int, invite_code: str, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """通过邀请码加入群组"""
    from app.models import Group, GroupMember as GM
    group = db.query(Group).filter(Group.id == group_id, Group.invite_code == invite_code).first()
    if not group:
        raise HTTPException(status_code=404, detail="邀请码无效")
    
    existing = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user.id).first()
    if existing:
        return {"ok": True, "message": "已在群中"}
    
    member = GM(group_id=group_id, user_id=user.id)
    db.add(member)
    db.commit()
    return {"ok": True, "message": "加入成功"}

@router.post("/{group_id}/join")
def join_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """加入群组"""
    from app.models import Group, GroupMember as GM
    group = db.query(Group).filter(Group.id == group_id).first()
    if not group:
        raise HTTPException(status_code=404, detail="群组不存在")
    
    existing = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user.id).first()
    if existing:
        return {"ok": True, "message": "已在群中"}
    
    member = GM(group_id=group_id, user_id=user.id)
    db.add(member)
    db.commit()
    return {"ok": True, "message": "加入成功"}

@router.delete("/{group_id}/leave")
def leave_group(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """离开群组"""
    from app.models import Group, GroupMember as GM
    member = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=404, detail="不在群中")
    if member.is_owner:
        raise HTTPException(status_code=400, detail="群主不能退出，请先转让群主")
    
    db.delete(member)
    db.commit()
    return {"ok": True}

@router.post("/{group_id}/members/{user_id}/admin")
def set_admin(group_id: int, user_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """设置为管理员"""
    from app.models import Group, GroupMember as GM
    group = db.query(Group).filter(Group.id == group_id).first()
    if group.owner_id != user.id:
        raise HTTPException(status_code=403, detail="只有群主可以设置管理员")
    
    member = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user_id).first()
    if not member:
        raise HTTPException(status_code=404, detail="成员不存在")
    
    member.is_admin = True
    db.commit()
    return {"ok": True}

# ========== 消息 ==========

@router.get("/{group_id}/messages", response_model=List[GroupMessageResponse])
def get_group_messages(group_id: int, limit: int = 50, offset: int = 0, db: Session = Depends(get_db)):
    """获取群消息"""
    from app.models import GroupMessage
    msgs = db.query(GroupMessage).filter(
        GroupMessage.group_id == group_id
    ).order_by(GroupMessage.created_at.desc()).offset(offset).limit(limit).all()
    
    return [GroupMessageResponse(
        id=m.id,
        group_id=m.group_id,
        author_id=m.author_id,
        author_username=m.author.username,
        content=m.content,
        reply_to=m.reply_to,
        created_at=m.created_at.isoformat()
    ) for m in reversed(msgs)]

@router.post("/{group_id}/messages", response_model=GroupMessageResponse)
def send_group_message(group_id: int, data: GroupMessageCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """发送群消息"""
    from app.models import Group, GroupMember as GM, GroupMessage
    
    # 验证成员
    member = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="不在群组中")
    
    msg = GroupMessage(
        group_id=group_id,
        author_id=user.id,
        content=data.content,
        reply_to=data.reply_to
    )
    db.add(msg)
    db.commit()
    
    return GroupMessageResponse(
        id=msg.id,
        group_id=msg.group_id,
        author_id=msg.author_id,
        author_username=user.username,
        content=msg.content,
        reply_to=msg.reply_to,
        created_at=msg.created_at.isoformat()
    )

@router.get("/{group_id}/invite")
def get_group_invite(group_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    """获取邀请链接"""
    from app.models import Group, GroupMember as GM
    member = db.query(GM).filter(GM.group_id == group_id, GM.user_id == user.id).first()
    if not member:
        raise HTTPException(status_code=403, detail="不在群中")
    
    group = db.query(Group).filter(Group.id == group_id).first()
    return {"invite_code": group.invite_code, "invite_url": f"/groups/join/{group.id}/{group.invite_code}"}

# ========== 搜索公开群组 ==========

@router.get("/public/list", response_model=List[GroupResponse])
def list_public_groups(search: str = None, limit: int = 20, db: Session = Depends(get_db)):
    """搜索公开群组"""
    from app.models import Group, GroupMember as GM
    query = db.query(Group).filter(Group.is_private == False)
    if search:
        query = query.filter(Group.name.ilike(f"%{search}%"))
    groups = query.order_by(Group.created_at.desc()).limit(limit).all()
    
    result = []
    for g in groups:
        member_count = db.query(GM).filter(GM.group_id == g.id).count()
        result.append(GroupResponse(
            id=g.id,
            name=g.name,
            description=g.description,
            avatar=g.avatar,
            owner_id=g.owner_id,
            member_count=member_count,
            created_at=g.created_at.isoformat(),
            is_private=g.is_private
        ))
    return result
