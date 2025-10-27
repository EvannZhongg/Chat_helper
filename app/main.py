from fastapi import FastAPI
from app.routers import import_router, profile_router, event_router, persona_router, assist_router, timeline_router
from app.core.config import settings
import os
from fastapi.middleware.cors import CORSMiddleware

# --- main.py: Script execution started ---
print("--- main.py: Script execution started ---")

# --- main.py: Imports completed ---
print("--- main.py: Imports completed ---")

app = FastAPI(
    title="Chat Helper API",
    description="社交军师 Agent 后端服务",
    version="0.1.0"
)

# --- main.py: FastAPI app created ---
print("--- main.py: FastAPI app created ---")

# CORS 中间件必须在注册路由之前添加
# 使用 "*" 允许所有源，方便本地开发
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- main.py: CORS middleware added ---
print("--- main.py: CORS middleware added ---")

# 注册路由
app.include_router(import_router.router)
app.include_router(profile_router.router)
app.include_router(event_router.router) # 确保事件路由被包含
app.include_router(persona_router.router) # 2. 包含新路由
app.include_router(assist_router.router)
app.include_router(timeline_router.router)

# --- main.py: Routers included ---
print("--- main.py: Routers included ---")


@app.on_event("startup")
async def on_startup():
    # 确保数据目录在启动时存在
    print("--- main.py: Startup event triggered ---")
    os.makedirs(settings.DATA_PATH, exist_ok=True)
    print(f"--- main.py: Data directory '{settings.DATA_PATH}' ensured. ---")

@app.get("/")
async def root():
    print("--- main.py: Root path '/' accessed ---") # 添加根路径访问日志
    return {"message": "Welcome to Chat Helper API"}

# --- main.py: Script execution finished (before Uvicorn server runs app) ---
print("--- main.py: Script execution finished (before Uvicorn server runs app) ---")


