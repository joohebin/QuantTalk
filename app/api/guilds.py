"""
Discord风格服务器/频道 API
"""
import random
import string
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional, List

from app.database import get_db
from app.models import Guild, TextChannel, VoiceChannel, GuildMessage, User, guild_members, voice_members
from app.auth import get_current_user

router = APIRouter(prefix="/api/guilds", tags=["guilds"])


def generate_invite_code():
    """生成8位邀请码"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(8))


# ============ Schemas ============

class TextChannelCreate(BaseModel):
    name: str
    topic: str = ""


class VoiceChannelCreate(BaseModel):
    name: str
    channel_type: str = "voice"
    bitrate: int = 64000
    user_limit: int = 0


class GuildCreate(BaseModel):
    name: str
    description: str = ""
    is_public: bool = True


class GuildUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None


class MessageCreate(BaseModel):
    content: str


class GuildMessageResponse(BaseModel):
    id: int
    content: str
    author_id: int
    author_username: str
    author_avatar: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelResponse(BaseModel):
    id: int
    name: str
    topic: Optional[str] = None
    position: int

    class Config:
        from_attributes = True


class VoiceChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str
    user_limit: int
    position: int
    online_count: int = 0
    online_users: List[dict] = []

    class Config:
        from_attributes = True


class GuildMemberInfo(BaseModel):
    user_id: int
    username: str
    avatar: str
    nickname: str
    role: str
    is_online: bool


class GuildResponse(BaseModel):
    id: int
    name: str
    icon: str
    description: str
    owner_id: int
    invite_code: Optional[str]
    member_count: int
    text_channel_count: int
    voice_channel_count: int
    my_role: Optional[str] = None

    class Config:
        from_attributes = True


# ============ 路由 ============

@router.get("/")
def list_guilds(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取用户加入的所有服务器"""
    guilds = db.query(Guild).join(guild_members).filter(
        guild_members.c.user_id == current_user.id
    ).all()

    result = []
    for g in guilds:
        # 获取成员角色
        member = db.execute(
            guild_members.select().where(
                guild_members.c.guild_id == g.id,
                guild_members.c.user_id == current_user.id
            )
        ).first()

        result.append({
            "id": g.id,
            "name": g.name,
            "icon": g.icon,
            "description": g.description,
            "owner_id": g.owner_id,
            "invite_code": g.invite_code,
            "member_count": len(g.members),
            "text_channel_count": len(g.text_channels),
            "voice_channel_count": len(g.voice_channels),
            "my_role": member.role if member else None
        })

    return result


@router.get("/public")
def list_public_guilds(db: Session = Depends(get_db)):
    """获取公开服务器列表"""
    guilds = db.query(Guild).filter(Guild.is_public == True).limit(20).all()
    return [{
        "id": g.id,
        "name": g.name,
        "icon": g.icon,
        "description": g.description,
        "owner_id": g.owner_id,
        "invite_code": g.invite_code,
        "member_count": len(g.members),
    } for g in guilds]


@router.post("/")
def create_guild(data: GuildCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建新服务器"""
    guild = Guild(
        name=data.name,
        description=data.description,
        owner_id=current_user.id,
        is_public=data.is_public,
        invite_code=generate_invite_code()
    )
    db.add(guild)
    db.commit()
    db.refresh(guild)

    # 创建默认文字频道
    default_text = TextChannel(
        guild_id=guild.id,
        name="general",
        topic="欢迎来到服务器！",
        position=0
    )
    db.add(default_text)

    # 创建默认语音频道
    default_voice = VoiceChannel(
        guild_id=guild.id,
        name="语音",
        channel_type="voice",
        position=0
    )
    db.add(default_voice)

    # 创建交易讨论语音频道
    trading_voice = VoiceChannel(
        guild_id=guild.id,
        name="交易大厅",
        channel_type="video",  # 视频频道
        position=1
    )
    db.add(trading_voice)

    # 创建行情频道
    market_voice = VoiceChannel(
        guild_id=guild.id,
        name="行情分析",
        channel_type="video",
        position=2
    )
    db.add(market_voice)

    # 自动加入创建者为owner
    db.execute(guild_members.insert().values(
        user_id=current_user.id,
        guild_id=guild.id,
        role="owner"
    ))

    db.commit()

    return {
        "id": guild.id,
        "name": guild.name,
        "invite_code": guild.invite_code,
        "message": "服务器创建成功"
    }


@router.get("/{guild_id}")
def get_guild(guild_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取服务器详情"""
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="服务器不存在")

    # 检查是否是成员
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    return {
        "id": guild.id,
        "name": guild.name,
        "icon": guild.icon,
        "description": guild.description,
        "owner_id": guild.owner_id,
        "invite_code": guild.invite_code,
        "member_count": len(guild.members),
        "my_role": member.role
    }


@router.post("/join/{invite_code}")
def join_guild(invite_code: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """通过邀请码加入服务器"""
    guild = db.query(Guild).filter(Guild.invite_code == invite_code).first()
    if not guild:
        raise HTTPException(status_code=404, detail="邀请码无效")

    # 检查是否已经是成员
    existing = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild.id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if existing:
        return {"guild_id": guild.id, "message": "已经在服务器中"}

    # 加入服务器
    db.execute(guild_members.insert().values(
        user_id=current_user.id,
        guild_id=guild.id,
        role="member"
    ))
    db.commit()

    return {"guild_id": guild.id, "name": guild.name, "message": "加入成功"}


@router.delete("/{guild_id}/leave")
def leave_guild(guild_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """离开服务器"""
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="服务器不存在")

    if guild.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="服务器所有者不能离开，请先转让所有权或删除服务器")

    db.execute(
        guild_members.delete().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    )
    db.commit()

    return {"message": "已离开服务器"}


@router.get("/{guild_id}/channels")
def get_guild_channels(guild_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取服务器的所有频道"""
    # 验证成员身份
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    # 获取文字频道
    text_channels = db.query(TextChannel).filter(
        TextChannel.guild_id == guild_id
    ).order_by(TextChannel.position).all()

    # 获取语音频道及其在线成员（区分voice和video）
    voice_channels = db.query(VoiceChannel).filter(
        VoiceChannel.guild_id == guild_id,
        VoiceChannel.channel_type == "voice"
    ).order_by(VoiceChannel.position).all()

    # 获取视频频道
    video_channels = db.query(VoiceChannel).filter(
        VoiceChannel.guild_id == guild_id,
        VoiceChannel.channel_type == "video"
    ).order_by(VoiceChannel.position).all()

    voice_result = []
    for vc in voice_channels:
        # 获取在线成员
        online = db.query(User).join(voice_members).filter(
            voice_members.c.voice_channel_id == vc.id
        ).all()

        voice_result.append({
            "id": vc.id,
            "name": vc.name,
            "channel_type": vc.channel_type,
            "bitrate": vc.bitrate,
            "user_limit": vc.user_limit,
            "position": vc.position,
            "online_count": len(online),
            "online_users": [{"id": u.id, "username": u.username, "avatar": u.avatar} for u in online]
        })

    video_result = []
    for vc in video_channels:
        # 获取在线成员
        online = db.query(User).join(voice_members).filter(
            voice_members.c.voice_channel_id == vc.id
        ).all()

        video_result.append({
            "id": vc.id,
            "name": vc.name,
            "channel_type": vc.channel_type,
            "bitrate": vc.bitrate,
            "user_limit": vc.user_limit,
            "position": vc.position,
            "online_count": len(online),
            "online_users": [{"id": u.id, "username": u.username, "avatar": u.avatar} for u in online]
        })

    return {
        "text_channels": [{"id": c.id, "name": c.name, "topic": c.topic, "position": c.position} for c in text_channels],
        "voice_channels": voice_result,
        "video_channels": video_result
    }


@router.post("/{guild_id}/channels/text")
def create_text_channel(guild_id: int, data: TextChannelCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建文字频道"""
    # 验证权限
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member or member.role not in ["owner", "admin", "moderator"]:
        raise HTTPException(status_code=403, detail="没有权限")

    # 获取最大position
    max_pos = db.query(TextChannel).filter(
        TextChannel.guild_id == guild_id
    ).count()

    channel = TextChannel(
        guild_id=guild_id,
        name=data.name,
        topic=data.topic,
        position=max_pos
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return {"id": channel.id, "name": channel.name, "topic": channel.topic}


@router.post("/{guild_id}/channels/voice")
def create_voice_channel(guild_id: int, data: VoiceChannelCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """创建语音频道"""
    # 验证权限
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member or member.role not in ["owner", "admin", "moderator"]:
        raise HTTPException(status_code=403, detail="没有权限")

    # 获取最大position
    max_pos = db.query(VoiceChannel).filter(
        VoiceChannel.guild_id == guild_id
    ).count()

    channel = VoiceChannel(
        guild_id=guild_id,
        name=data.name,
        channel_type=data.channel_type,
        bitrate=data.bitrate,
        user_limit=data.user_limit,
        position=max_pos
    )
    db.add(channel)
    db.commit()
    db.refresh(channel)

    return {"id": channel.id, "name": channel.name, "channel_type": channel.channel_type}


@router.get("/{guild_id}/channels/text/{channel_id}/messages")
def get_text_messages(guild_id: int, channel_id: int, limit: int = 50, before: Optional[int] = None,
                      db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取文字频道消息"""
    # 验证成员
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    # 验证频道存在
    channel = db.query(TextChannel).filter(
        TextChannel.id == channel_id,
        TextChannel.guild_id == guild_id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="频道不存在")

    # 获取消息
    query = db.query(GuildMessage).filter(GuildMessage.channel_id == channel_id)

    if before:
        query = query.filter(GuildMessage.id < before)

    messages = query.order_by(GuildMessage.created_at.desc()).limit(limit).all()

    return [{
        "id": m.id,
        "content": m.content,
        "author_id": m.author_id,
        "author_username": m.author.username,
        "author_avatar": m.author.avatar,
        "created_at": m.created_at.isoformat()
    } for m in reversed(messages)]


@router.post("/{guild_id}/channels/text/{channel_id}/messages")
def send_message(guild_id: int, channel_id: int, data: MessageCreate,
                 db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """发送消息"""
    # 验证成员
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    # 验证频道
    channel = db.query(TextChannel).filter(
        TextChannel.id == channel_id,
        TextChannel.guild_id == guild_id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="频道不存在")

    # 创建消息
    message = GuildMessage(
        channel_id=channel_id,
        author_id=current_user.id,
        content=data.content
    )
    db.add(message)
    db.commit()
    db.refresh(message)

    return {
        "id": message.id,
        "content": message.content,
        "author_id": message.author_id,
        "author_username": current_user.username,
        "author_avatar": current_user.avatar,
        "created_at": message.created_at.isoformat()
    }


@router.post("/{guild_id}/channels/voice/{channel_id}/join")
def join_voice_channel(guild_id: int, channel_id: int,
                       db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """加入语音频道"""
    # 验证成员
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    # 验证频道
    channel = db.query(VoiceChannel).filter(
        VoiceChannel.id == channel_id,
        VoiceChannel.guild_id == guild_id
    ).first()

    if not channel:
        raise HTTPException(status_code=404, detail="频道不存在")

    # 检查用户限制
    current_count = db.query(voice_members).filter(
        voice_members.c.voice_channel_id == channel_id
    ).count()

    if channel.user_limit > 0 and current_count >= channel.user_limit:
        raise HTTPException(status_code=400, detail="频道人数已满")

    # 检查是否已在其他频道
    db.execute(
        voice_members.delete().where(voice_members.c.user_id == current_user.id)
    )

    # 加入频道
    db.execute(voice_members.insert().values(
        user_id=current_user.id,
        voice_channel_id=channel_id
    ))
    db.commit()

    return {
        "channel_id": channel_id,
        "channel_name": channel.name,
        "channel_type": channel.channel_type,
        "message": "已加入语音频道"
    }


@router.post("/{guild_id}/channels/voice/{channel_id}/leave")
def leave_voice_channel(guild_id: int, channel_id: int,
                        db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """离开语音频道"""
    db.execute(
        voice_members.delete().where(
            voice_members.c.user_id == current_user.id,
            voice_members.c.voice_channel_id == channel_id
        )
    )
    db.commit()

    return {"message": "已离开语音频道"}


@router.get("/{guild_id}/members")
def get_guild_members(guild_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """获取服务器成员列表"""
    # 验证成员
    member = db.execute(
        guild_members.select().where(
            guild_members.c.guild_id == guild_id,
            guild_members.c.user_id == current_user.id
        )
    ).first()

    if not member:
        raise HTTPException(status_code=403, detail="不是服务器成员")

    # 获取所有成员
    members = db.execute(
        guild_members.select().where(guild_members.c.guild_id == guild_id)
    ).all()

    result = []
    for m in members:
        user = db.query(User).filter(User.id == m.user_id).first()
        if user:
            result.append({
                "user_id": user.id,
                "username": user.username,
                "avatar": user.avatar,
                "nickname": m.nickname,
                "role": m.role,
                "is_online": user.is_online
            })

    return result


@router.get("/{guild_id}/invite")
def regenerate_invite(guild_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """重新生成邀请链接"""
    guild = db.query(Guild).filter(Guild.id == guild_id).first()
    if not guild:
        raise HTTPException(status_code=404, detail="服务器不存在")

    if guild.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有服务器所有者可以生成邀请")

    guild.invite_code = generate_invite_code()
    db.commit()

    return {"invite_code": guild.invite_code}
