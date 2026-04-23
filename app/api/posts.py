from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from app.database import get_db
from app.models import User, Post, Comment, post_likes
from app.schemas import PostCreate, PostUpdate, PostResponse, CommentCreate, CommentResponse
from app.auth import get_current_user, get_optional_user

router = APIRouter()


@router.get("/")
def get_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=50),
    tag: str = Query("", description="按标签筛选"),
    user_id: int = Query(None, description="按用户筛选"),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
):
    query = db.query(Post)
    if tag:
        query = query.filter(Post.tags.contains(tag))
    if user_id:
        query = query.filter(Post.author_id == user_id)

    total = query.count()
    posts = query.order_by(desc(Post.created_at)).offset((page - 1) * limit).limit(limit).all()

    result = []
    for post in posts:
        liked = False
        if current_user:
            liked = db.query(post_likes).filter_by(user_id=current_user.id, post_id=post.id).first() is not None
        result.append({
            "id": post.id,
            "title": post.title,
            "content": post.content,
            "tags": post.tags,
            "image_url": post.image_url,
            "author_id": post.author_id,
            "views": post.views,
            "likes_count": db.query(post_likes).filter_by(post_id=post.id).count(),
            "comments_count": db.query(Comment).filter_by(post_id=post.id).count(),
            "is_liked": liked,
            "created_at": post.created_at.isoformat(),
            "author": {
                "id": post.author.id,
                "username": post.author.username,
                "avatar": post.author.avatar,
                "bio": post.author.bio,
            }
        })

    return {"posts": result, "total": total, "page": page, "limit": limit}


@router.get("/{post_id}")
def get_post(post_id: int, current_user: User | None = Depends(get_optional_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")

    post.views += 1
    db.commit()

    liked = False
    if current_user:
        liked = db.query(post_likes).filter_by(user_id=current_user.id, post_id=post.id).first() is not None

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "tags": post.tags,
        "image_url": post.image_url,
        "author_id": post.author_id,
        "views": post.views,
        "likes_count": db.query(post_likes).filter_by(post_id=post.id).count(),
        "comments_count": db.query(Comment).filter_by(post_id=post.id).count(),
        "is_liked": liked,
        "created_at": post.created_at.isoformat(),
        "author": {
            "id": post.author.id,
            "username": post.author.username,
            "avatar": post.author.avatar,
            "bio": post.author.bio,
        }
    }


@router.post("/")
def create_post(data: PostCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = Post(
        title=data.title or "",
        content=data.content,
        tags=data.tags or "",
        image_url=data.image_url or "",
        author_id=current_user.id,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    return {"id": post.id, "message": "发布成功"}


@router.put("/{post_id}")
def update_post(post_id: int, data: PostUpdate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == current_user.id).first()
    if not post:
        raise HTTPException(404, "帖子不存在或无权修改")
    if data.title is not None:
        post.title = data.title
    if data.content is not None:
        post.content = data.content
    if data.tags is not None:
        post.tags = data.tags
    db.commit()
    return {"message": "更新成功"}


@router.delete("/{post_id}")
def delete_post(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id, Post.author_id == current_user.id).first()
    if not post:
        raise HTTPException(404, "帖子不存在或无权删除")
    db.delete(post)
    db.commit()
    return {"message": "删除成功"}


@router.post("/{post_id}/like")
def toggle_like(post_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")

    existing = db.query(post_likes).filter_by(user_id=current_user.id, post_id=post_id).first()
    if existing:
        db.execute(post_likes.delete().where(post_likes.c.user_id == current_user.id, post_likes.c.post_id == post_id))
        db.commit()
        return {"liked": False, "message": "取消点赞"}
    else:
        db.execute(post_likes.insert().values(user_id=current_user.id, post_id=post_id))
        db.commit()
        return {"liked": True, "message": "点赞成功"}


# Comments
@router.get("/{post_id}/comments")
def get_comments(post_id: int, db: Session = Depends(get_db)):
    comments = db.query(Comment).filter(Comment.post_id == post_id).order_by(Comment.created_at).all()
    return [{
        "id": c.id,
        "content": c.content,
        "created_at": c.created_at.isoformat(),
        "author": {
            "id": c.author.id,
            "username": c.author.username,
            "avatar": c.author.avatar,
        }
    } for c in comments]


@router.post("/{post_id}/comments")
def create_comment(post_id: int, data: CommentCreate, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    if not post:
        raise HTTPException(404, "帖子不存在")
    comment = Comment(content=data.content, post_id=post_id, author_id=current_user.id)
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return {"id": comment.id, "message": "评论成功"}
