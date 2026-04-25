# Database Configuration
DATABASE_URL = "sqlite:///./quanttalk.db"

# JWT Configuration
SECRET_KEY = "quanttalk-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# App Config
APP_NAME = "QuantTalk"
APP_VERSION = "2.0.0"

# ============================================
# API2Trade MT4/MT5 配置（主用）
# 文档: https://www.api2trade.com
# Base URL: https://api.metatraderapi.dev
# 认证: x-api-key header
# ============================================
API2TRADE_BASE_URL = "https://api.metatraderapi.dev"
API2TRADE_API_KEY = "a915ec00-8a72-4df2-9fc1-1caf13d6b6e2"  # API2Trade API Key
API2TRADE_ACCOUNT_UUID = "ff982e56-23b0-4e3d-b6f6-7f7b8c40679e"  # MT4/MT5 账户 UUID
API2TRADE_WS_URL = "wss://api.metatraderapi.dev/stream"
API2TRADE_CACHE_TTL = 5  # 实时行情缓存秒数

# ============================================
# MetaApi MT5 配置（备用）
# 账户ID (UUID): ff982e56-23b0-4e3d-b6f6-7f7b8c40679e
# API Key: a915ec00-8a72-4df2-9fc1-1caf13d6b6e2
# 账户名称: QuantAI Main (账户号 87954362)
# 注意: MetaApi 服务器当前使用占位 SSL 证书，所有 API 返回 404，作为备用保留
# ============================================
METAAPI_ACCOUNT_ID = "ff982e56-23b0-4e3d-b6f6-7f7b8c40679e"
METAAPI_API_KEY = "a915ec00-8a72-4df2-9fc1-1caf13d6b6e2"
METAAPI_BASE_URL = "https://api.metaapi.cloud"
METAAPI_CACHE_TTL = 5  # 实时行情缓存秒数
