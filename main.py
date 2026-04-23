from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI(
    title="QuantTalk API",
    description="量化交易策略服务 - 市场数据接口与策略执行",
    version="1.0.0",
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "QuantTalk",
        "version": "1.0.0",
        "status": "running",
        "message": "量化交易策略服务 API 已就绪",
    }


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/v1/strategies")
async def list_strategies():
    return {"strategies": [], "total": 0}


@app.get("/api/v1/market/overview")
async def market_overview():
    return {"message": "市场数据接口 - 待接入数据源"}


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
