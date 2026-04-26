from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel, EmailStr

from app.database import get_db
from app.models import User, VerificationCode
from app.schemas import UserRegister, UserLogin, Token, UserResponse
from app.auth import hash_password, verify_password, create_access_token, get_current_user
from app.email_utils import generate_code, send_verification_email

router = APIRouter()


# ========== Request/Response Models ==========

class SendCodeRequest(BaseModel):
    email: str
    purpose: str = "register"  # register/login/reset_password


class VerifyCodeRequest(BaseModel):
    email: str
    code: str
    purpose: str = "register"


class RegisterWithCodeRequest(BaseModel):
    username: str
    email: str
    password: str
    code: str  # 验证码


class LoginWithCodeRequest(BaseModel):
    email: str
    code: str


# ========== 验证码相关 API ==========

@router.post("/send-code")
def send_verification(
    data: SendCodeRequest,
    db: Session = Depends(get_db)
):
    """发送邮箱验证码"""
    # 频率限制：同一邮箱 60 秒内不能重复发送
    recent = db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.purpose == data.purpose,
        VerificationCode.created_at > datetime.utcnow() - timedelta(seconds=60)
    ).first()
    
    if recent:
        raise HTTPException(400, "请稍后再试，验证码发送太频繁")
    
    # 生成验证码
    code = generate_code(6)
    expires_at = datetime.utcnow() + timedelta(minutes=10)
    
    # 保存到数据库
    vc = VerificationCode(
        email=data.email,
        code=code,
        purpose=data.purpose,
        expires_at=expires_at
    )
    db.add(vc)
    db.commit()
    
    # 发送邮件
    purpose_text = "注册" if data.purpose == "register" else "登录"
    success = send_verification_email(data.email, code, purpose_text)
    
    if not success:
        # 邮件发送失败，但验证码已生成（开发调试用）
        return {
            "message": "验证码已生成（邮件服务未配置）",
            "code": code,  # 开发模式下直接返回验证码
            "hint": "请配置 SendGrid 或 SMTP 邮件服务"
        }
    
    return {"message": "验证码已发送"}


@router.post("/verify-code")
def verify_code(
    data: VerifyCodeRequest,
    db: Session = Depends(get_db)
):
    """验证验证码"""
    vc = db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.code == data.code,
        VerificationCode.purpose == data.purpose,
        VerificationCode.used == False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not vc:
        raise HTTPException(400, "验证码错误或已过期")
    
    if vc.expires_at < datetime.utcnow():
        raise HTTPException(400, "验证码已过期，请重新获取")
    
    # 标记为已使用
    vc.used = True
    db.commit()
    
    return {"message": "验证成功", "valid": True}


@router.post("/register", response_model=Token)
def register(data: UserRegister, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已被注册")
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "邮箱已被注册")

    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "bio": user.bio,
        }
    )


@router.post("/login", response_model=Token)
def login(data: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(401, "用户名或密码错误")

    token = create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "bio": user.bio,
        }
    )


@router.post("/register-with-code", response_model=Token)
def register_with_code(data: RegisterWithCodeRequest, db: Session = Depends(get_db)):
    """邮箱验证码注册"""
    # 验证验证码
    vc = db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.code == data.code,
        VerificationCode.purpose == "register",
        VerificationCode.used == False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not vc:
        raise HTTPException(400, "验证码错误")
    
    if vc.expires_at < datetime.utcnow():
        raise HTTPException(400, "验证码已过期，请重新获取")
    
    # 检查用户名和邮箱是否已存在
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "用户名已被注册")
    
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "邮箱已被注册")
    
    # 创建用户
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        is_verified=True,  # 验证通过
    )
    db.add(user)
    
    # 标记验证码已使用
    vc.used = True
    db.commit()
    db.refresh(user)
    
    token = create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "bio": user.bio,
        }
    )


@router.post("/login-with-code", response_model=Token)
def login_with_code(data: LoginWithCodeRequest, db: Session = Depends(get_db)):
    """邮箱验证码登录"""
    # 验证验证码
    vc = db.query(VerificationCode).filter(
        VerificationCode.email == data.email,
        VerificationCode.code == data.code,
        VerificationCode.purpose == "login",
        VerificationCode.used == False
    ).order_by(VerificationCode.created_at.desc()).first()
    
    if not vc:
        raise HTTPException(400, "验证码错误")
    
    if vc.expires_at < datetime.utcnow():
        raise HTTPException(400, "验证码已过期，请重新获取")
    
    # 查找用户
    user = db.query(User).filter(User.email == data.email).first()
    if not user:
        raise HTTPException(404, "该邮箱未注册，请先注册")
    
    # 标记验证码已使用
    vc.used = True
    db.commit()
    
    token = create_access_token(user.id, user.username)
    return Token(
        access_token=token,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "avatar": user.avatar,
            "bio": user.bio,
        }
    )


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "avatar": current_user.avatar,
        "bio": current_user.bio,
        "followers_count": len(current_user.followers),
        "following_count": len(current_user.following),
        "posts_count": len(current_user.posts),
        "created_at": current_user.created_at.isoformat(),
    }
