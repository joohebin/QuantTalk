from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# Auth schemas
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


# User schemas
class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    avatar: str = ""
    bio: str = "量化交易爱好者"
    is_verified: bool = False
    created_at: datetime
    followers_count: int = 0
    following_count: int = 0
    posts_count: int = 0

    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    avatar: Optional[str] = None
    bio: Optional[str] = None


# Post schemas
class PostCreate(BaseModel):
    title: Optional[str] = ""
    content: str
    tags: Optional[str] = ""
    image_url: Optional[str] = ""


class PostUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    title: str
    content: str
    tags: str = ""
    image_url: str = ""
    author_id: int
    views: int = 0
    likes_count: int = 0
    comments_count: int = 0
    is_liked: bool = False
    created_at: datetime
    author: Optional[UserResponse] = None

    class Config:
        from_attributes = True


# Comment schemas
class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    content: str
    post_id: int
    author_id: int
    created_at: datetime
    author: Optional[UserResponse] = None

    class Config:
        from_attributes = True
