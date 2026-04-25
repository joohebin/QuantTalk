from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
import os
import uuid
import aiofiles
from app.database import get_db
from app.models import User
from app.auth import get_current_user

router = APIRouter(tags=["上传"])

# 上传目录
UPLOAD_DIR = "uploads"
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB

# 确保上传目录存在
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/avatars", exist_ok=True)
os.makedirs(f"{UPLOAD_DIR}/posts", exist_ok=True)


@router.post("/api/upload/image")
async def upload_image(
    file: UploadFile = File(...),
    type: str = "posts",
    current_user: User = Depends(get_current_user)
):
    """上传图片"""
    # 检查文件类型
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型。仅支持: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大。最大支持 {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # 生成唯一文件名
    filename = f"{uuid.uuid4().hex}{ext}"
    
    # 确定保存目录
    save_dir = f"{UPLOAD_DIR}/{type}" if type in ["avatars", "posts"] else UPLOAD_DIR
    os.makedirs(save_dir, exist_ok=True)
    
    filepath = f"{save_dir}/{filename}"
    
    # 保存文件
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)
    
    # 返回访问URL
    url = f"/{filepath}"
    
    return {
        "url": url,
        "filename": filename,
        "size": len(content)
    }


@router.post("/api/upload/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """上传头像"""
    # 检查文件类型
    ext = os.path.splitext(file.filename)[1].lower() if file.filename else ""
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型。仅支持: {', '.join(ALLOWED_EXTENSIONS)}")
    
    # 检查文件大小
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail=f"文件过大。最大支持 {MAX_FILE_SIZE // (1024*1024)}MB")
    
    # 生成唯一文件名
    filename = f"avatar_{current_user.id}_{uuid.uuid4().hex}{ext}"
    filepath = f"{UPLOAD_DIR}/avatars/{filename}"
    
    # 保存文件
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)
    
    # 更新用户头像
    url = f"/{filepath}"
    current_user.avatar = url
    db.commit()
    
    return {
        "url": url,
        "filename": filename
    }


@router.get("/uploads/{path:path}")
async def serve_upload(path: str):
    """访问上传的文件"""
    from fastapi.responses import FileResponse
    import os
    filepath = f"uploads/{path}"
    if os.path.exists(filepath):
        return FileResponse(filepath)
    raise HTTPException(status_code=404, detail="文件不存在")
