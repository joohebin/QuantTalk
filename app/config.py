# Database Configuration
DATABASE_URL = "sqlite:///./quanttalk.db"

# JWT Configuration
SECRET_KEY = "quanttalk-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 10080  # 7 days

# App Config
APP_NAME = "QuantTalk"
APP_VERSION = "2.0.0"

# MetaApi MT5 真实账户配置
# 账户ID (UUID): ff982e56-23b0-4e3d-b6f6-7f7b8c40679e
# API Key: a915ec00-8a72-4df2-9fc1-1caf13d6b6e2
# 账户名称: QuantAI Main (账户号 87954362)
METAAPI_ACCOUNT_ID = "ff982e56-23b0-4e3d-b6f6-7f7b8c40679e"
METAAPI_API_KEY = "a915ec00-8a72-4df2-9fc1-1caf13d6b6e2"
METAAPI_BASE_URL = "https://api.metaapi.cloud"
METAAPI_CACHE_TTL = 5  # 实时行情缓存秒数
