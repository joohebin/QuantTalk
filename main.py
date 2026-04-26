"""
QuantTalk - 量化交易社交平台 v2.0
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, posts, users, market, notifications, communities, ws, messages, quantai, trademux, exchanges, upload, room_signaling, guilds, groups, portfolio, trading_community, wallet, social, trading_embed
from app.database import engine, Base

# 导入所有模型以确保数据库表被创建
from app.models import *  # noqa
from app.models_phase3 import *  # noqa
from app.models_phase4 import *  # noqa
from app.models_phase5 import *  # noqa
import uvicorn

Base.metadata.create_all(bind=engine)

app = FastAPI(title="QuantTalk API", description="量化交易社交平台", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(groups.router, tags=["Group Chat"])
app.include_router(portfolio.router, tags=["Portfolio"])
app.include_router(posts.router, prefix="/api/posts", tags=["动态"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["通知"])
app.include_router(communities.router, prefix="/api/communities", tags=["社区"])
app.include_router(market.router, prefix="/api/market", tags=["行情"])
app.include_router(messages.router, prefix="/api/messages", tags=["私信"])
app.include_router(quantai.router, prefix="/api/quantai", tags=["QuantAI 交易广场"])
app.include_router(trademux.router, tags=["TradeMux MT5"])
app.include_router(exchanges.router, tags=["交易所配置"])
app.include_router(ws.router, tags=["WebSocket"])
app.include_router(upload.router, tags=["上传"])
app.include_router(room_signaling.router, tags=["视频通话"])
app.include_router(guilds.router, tags=["Discord服务器"])
app.include_router(trading_community.router, tags=["第三阶段：交易社区"])
app.include_router(wallet.router, tags=["第四阶段：钱包和转账"])
app.include_router(social.router, tags=["社区互动"])
app.include_router(trading_embed.router, tags=["第五阶段：交易内容嵌入"])

# 上传文件目录 - 必须在 static 之前挂载
import os
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# 静态文件上传端点（临时用于修复 CDN 问题）
from fastapi import Request
from fastapi.responses import PlainTextResponse

@app.put("/upload/static/{filename}")
async def upload_static_file(filename: str, request: Request):
    """上传静态 JS/CSS 文件"""
    content = await request.body()
    static_dir = "static"
    os.makedirs(static_dir, exist_ok=True)
    filepath = os.path.join(static_dir, filename)
    with open(filepath, "wb") as f:
        f.write(content)
    return {"status": "ok", "file": filename, "size": len(content)}

# Static files must be mounted LAST to avoid catching API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
