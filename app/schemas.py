from pydantic import BaseModel
from typing import Optional
from datetime import datetime


# === Auth ===
class UserRegister(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


# === User ===
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar: str = ""
    bio: str = "量化交易爱好者"
    is_online: bool = False
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0
    class Config:
        from_attributes = True

class UserUpdate(BaseModel):
    bio: Optional[str] = None
    old_password: Optional[str] = None
    new_password: Optional[str] = None


# === Post ===
class PostCreate(BaseModel):
    title: Optional[str] = ""
    content: str
    tags: Optional[str] = ""
    image_url: Optional[str] = ""

class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


# === Comment ===
class CommentCreate(BaseModel):
    content: str


# === Notification ===
class NotificationResponse(BaseModel):
    id: int
    type: str
    content: str
    from_user_id: Optional[int] = None
    post_id: Optional[int] = None
    is_read: bool = False
    created_at: datetime
    from_username: Optional[str] = None
    from_avatar: Optional[str] = None
    class Config:
        from_attributes = True


# === Community ===
class CommunityCreate(BaseModel):
    name: str
    display_name: str
    description: Optional[str] = ""
    icon: Optional[str] = ""

class CommunityUpdate(BaseModel):
    display_name: Optional[str] = None
    description: Optional[str] = None
    icon: Optional[str] = None

class CommunityResponse(BaseModel):
    id: int
    name: str
    display_name: str
    description: str = ""
    icon: str = ""
    owner_id: int
    is_public: bool = True
    members_count: int = 0
    channels_count: int = 0
    created_at: datetime
    class Config:
        from_attributes = True


# === Channel ===
class ChannelCreate(BaseModel):
    name: str
    channel_type: str = "text"
    description: Optional[str] = ""

class ChannelResponse(BaseModel):
    id: int
    name: str
    channel_type: str = "text"
    description: str = ""
    sort_order: int = 0
    created_at: datetime
    class Config:
        from_attributes = True


# === Channel Message ===
class ChannelMessageCreate(BaseModel):
    content: str

class ChannelMessageResponse(BaseModel):
    id: int
    channel_id: int
    author_id: int
    content: str
    created_at: datetime
    author_username: Optional[str] = None
    author_avatar: Optional[str] = None
    class Config:
        from_attributes = True


# === Friend Request ===
class FriendRequestCreate(BaseModel):
    to_user_id: int
    message: Optional[str] = ""

class FriendRequestResponse(BaseModel):
    id: int
    from_user_id: int
    to_user_id: int
    message: str = ""
    status: str = "PENDING"
    created_at: datetime
    from_username: Optional[str] = None
    from_avatar: Optional[str] = None
    to_username: Optional[str] = None
    to_avatar: Optional[str] = None
    class Config:
        from_attributes = True

class FriendResponse(BaseModel):
    id: int
    username: str
    avatar: str = ""
    bio: str = ""
    is_online: bool = False
    friends_count: int = 0
    created_at: datetime
    class Config:
        from_attributes = True

class FriendStatusResponse(BaseModel):
    is_friend: bool = False
    has_pending_request_from_me: bool = False
    has_pending_request_to_me: bool = False
    request_id: Optional[int] = None
