from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from app.database import get_db
from app.models import User, Post, Comment, post_likes, Notification
from app.auth import get_current_user, get_optional_user

router = APIRouter()


@router.get("/")
def get_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    tag: str = Query(""),
    user_id: int = Query(None),
    q: str = Query(""),
    current_user: Any = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(Post)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    if user_id:
        query = query.filter(Post.author_id == user_id)
    if q:
        query = query.filter(or_(Post.title.contains(q), Post.content.contains(q)))
    total = query.count()
    posts = query.order_by(desc(Post.created_at)).offset((page - 1) * limit).limit(limit).all()
    return {"posts": [_post_to_dict(p, current_user, db) for p in posts], "total": total, "page": page, "limit": limit}


@router.get("/feed")
def get_feed(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    current_user: Any = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    following_ids = [u.id for u in current_user.following]
    if not following_ids:
        following_ids = [current_user.id]
    query = db.query(Post).filter(Post.author_id.in_(following_ids))
    total = query.count()
    posts = query.order_by(desc(Post.created_at)).offset((page - 1) * limit).limit(limit).all()
    return {"posts": [_post_to_dict(p, current_user, db) for p in posts], "total": total, "page": page, "limit": limit}


@router.get("/{post_id}")
def get_post(post_id: int, current_user: Any = Depends(get_optional_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "post not found")
    post.views += 1
    db.commit()
    return _post_to_dict(post, current_user, db)


@router.post("/")
def create_post(data: dict, current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    post = Post(title=data.get("title", ""), content=data.get("content", ""),
                tags=data.get("tags", ""), image_url=data.get("image_url", ""),
                author_id=current_user.id)
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "message": "ok"}


@router.put("/{post_id}")
def update_post(post_id: int, data: dict, current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == current_user.id).first()
    if not post:
        raise HTTPException(404, "post not found")
    for k in ("title", "content", "tags"):
        if k in data and data[k] is not None:
            setattr(post, k, data[k])
    db.commit()
    return {"message": "ok"}


@router.delete("/{post_id}")
def delete_post(post_id: int, current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == current_user.id).first()
    if not post:
        raise HTTPException(404, "post not found")
    db.delete(post)
    db.commit()
    return {"message": "ok"}


@router.post("/{post_id}/like")
def toggle_like(post_id: int, current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "post not found")
    existing = db.query(post_likes).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.execute(post_likes.delete().where(post_likes.c.user_id == current_user.id, post_likes.c.post_id == post_id))
        db.commit()
        return {"liked": False}
    else:
        db.execute(post_likes.insert().values(user_id=current_user.id, post_id=post_id))
        if post.author_id != current_user.id:
            db.add(Notification(user_id=post.author_id, type="like",
                               content=f"{current_user.username} liked your post",
                               from_user_id=current_user.id, post_id=post_id))
        db.commit()
        return {"liked": True}


@router.get("/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at).all()
    return [{"id": c.id, "content": c.content, "created_at": c.created_at.isoformat(),
             "author": {"id": c.author.id, "username": c.author.username, "avatar": c.author.avatar}} for c in comments]


@router.post("/{post_id}/comments")
def create_comment(post_id: int, data: dict, current_user: Any = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "post not found")
    comment = Comment(content=data.get("content", ""), post_id=post_id, author_id=current_user.id)
    db.add(comment)
    if post.author_id != current_user.id:
        db.add(Notification(user_id=post.author_id, type="comment",
                           content=f"{current_user.username} commented on your post",
                           from_user_id=current_user.id, post_id=post_id))
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "message": "ok"}


def _post_to_dict(post, current_user, db):
    liked = False
    if current_user:
        liked = db.query(post_likes).filter_by(user_id=current_user.id, post_id=post.id).first() is not None
    return {
        "id": post.id, "title": post.title, "content": post.content, "tags": post.tags,
        "image_url": post.image_url, "author_id": post.author_id, "views": post.views,
        "likes_count": db.query(post_likes).filter_by(post_id=post.id).count(),
        "comments_count": db.query(Comment).filter_by(post_id=post.id).count(),
        "is_liked": liked, "created_at": post.created_at.isoformat(),
        "author": {"id": post.author.id, "username": post.author.username, "avatar": post.author.avatar, "bio": post.author.bio},
    }
