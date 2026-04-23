"""
QuantTalk - 量化交易社交平台
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api import auth, posts, users, market
from app.database import engine, Base
import uvicorn

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="QuantTalk API",
    description="量化交易社交平台 - 策略分享、行情讨论、社区交流",
    version="2.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(posts.router, prefix="/api/posts", tags=["动态"])
app.include_router(users.router, prefix="/api/users", tags=["用户"])
app.include_router(market.router, prefix="/api/market", tags=["行情"])

# Serve frontend static files
app.mount("/", StaticFiles(directory="static", html=True), name="static")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
