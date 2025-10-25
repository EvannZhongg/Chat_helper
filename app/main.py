from fastapi import FastAPI
from app.routers import import_router, profile_router
from app.core.config import settings
import os
from fastapi.middleware.cors import CORSMiddleware  # 确保这个导入在顶部

app = FastAPI(
    title="Chat Helper API",
    description="社交军师 Agent 后端服务",
    version="0.1.0"
)

# -----------------------------------------------------------------
# [修正] CORS 中间件必须在注册路由 (include_router) 之前添加
# -----------------------------------------------------------------
# origins = [
#     "http://localhost:5175",  # <-- Add this new line
#     "http://localhost:5174",
#     "http://localhost:5173",
#     "http://localhost"
# ]
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # 允许访问的源
    allow_credentials=True, # 允许 cookies
    allow_methods=["*"],    # 允许所有方法 (GET, POST, PATCH, etc.)
    allow_headers=["*"],    # 允许所有请求头
)
# -----------------------------------------------------------------

# 注册路由 (现在在中间件之后)
app.include_router(import_router.router)
app.include_router(profile_router.router)


@app.on_event("startup")
async def on_startup():
    # 确保数据目录在启动时存在
    os.makedirs(settings.DATA_PATH, exist_ok=True)
    print(f"Data directory '{settings.DATA_PATH}' ensured.")


@app.get("/")
async def root():
    return {"message": "Welcome to Chat Helper API"}