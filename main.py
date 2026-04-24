"""
QuantTalk - 量化交易社交平台 v2.0
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, posts, users, market, notifications, communities, ws, messages, quantai
from app.database import engine, Base
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
app.include_router(posts.router, prefix="/api/posts", tags=["动态"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(notifications.router, prefix="/api/notifications", tags=["通知"])
app.include_router(communities.router, prefix="/api/communities", tags=["社区"])
app.include_router(market.router, prefix="/api/market", tags=["行情"])
app.include_router(messages.router, prefix="/api/messages", tags=["私信"])
app.include_router(quantai.router, prefix="/api/quantai", tags=["QuantAI 交易广场"])
app.include_router(ws.router, tags=["WebSocket"])

# Static files must be mounted LAST to avoid catching API routes
app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
