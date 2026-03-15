"""
yt-dlp Web - FastAPI 主入口
"""
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from config import settings, CONFIG_FILE
from database import init_db, check_db_connection

import redis.asyncio as redis


# Redis 连接
redis_client: redis.Redis = None


async def auto_initialize():
    """
    自动初始化：
    - 如果环境变量中已提供 PG/Redis 信息，自动连接并创建表
    - 如果没有管理员账号，自动创建默认管理员
    """
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
    from models import Base, User
    import bcrypt as bc
    from sqlalchemy import select

    # 生成 secret_key
    if settings.secret_key == "change-me-on-first-run":
        settings.secret_key = secrets.token_hex(32)

    # 初始化数据库表
    await init_db()

    # 创建默认管理员（如果不存在）
    from database import async_session
    async with async_session() as session:
        existing = await session.execute(select(User).where(User.username == "admin"))
        if not existing.scalar():
            default_password = os.environ.get("YTDLP_ADMIN_PASSWORD", "admin123")
            admin = User(
                username="admin",
                password_hash=bc.hashpw(default_password.encode(), bc.gensalt()).decode(),
                is_admin=True,
            )
            session.add(admin)
            await session.commit()
            print(f"✅ 已创建管理员账号 admin（密码: {default_password}）")

    # 保存配置
    settings.save_to_file()
    print("✅ 自动初始化完成")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动和关闭"""
    global redis_client

    try:
        # 自动初始化数据库
        await auto_initialize()

        # 连接 Redis
        redis_client = redis.from_url(settings.redis_dsn, decode_responses=True)
        await redis_client.ping()
        print("✅ Redis 连接成功")

        # 启动调度器
        from services.scheduler import start_scheduler
        start_scheduler()

        print("✅ 服务启动完成")
    except Exception as e:
        print(f"⚠️  启动异常: {e}")
        print("⚠️  部分功能可能不可用，请检查 PG/Redis 连接")

    yield

    # 关闭
    if redis_client:
        await redis_client.close()


app = FastAPI(
    title="yt-dlp Web",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ==================== 状态 API ====================

@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    db_ok = await check_db_connection()
    redis_ok = False
    try:
        if redis_client:
            await redis_client.ping()
            redis_ok = True
    except Exception:
        pass

    return {
        "initialized": True,
        "database": db_ok,
        "redis": redis_ok,
        "version": "1.0.0",
    }


# ==================== 设置 API ====================

@app.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return {
        "proxy": settings.proxy,
        "download_dir": settings.download_dir,
        "default_resolution": getattr(settings, "default_resolution", "1080p"),
        "emby_url": settings.emby_url,
        "emby_api_key": settings.emby_api_key,
        "env_proxy": os.environ.get("YTDLP_PROXY", ""),
    }


@app.post("/api/settings")
async def update_settings(request: Request):
    """更新配置"""
    data = await request.json()

    for key in ["download_dir", "proxy", "emby_url", "emby_api_key", "default_resolution"]:
        if key in data:
            setattr(settings, key, data[key])

    settings.save_to_file()
    return {"success": True, "message": "配置已更新"}


# ==================== 统计 API ====================

@app.get("/api/task/stats")
async def get_task_stats():
    """获取任务统计"""
    from database import async_session
    from models import DownloadTask, Subscription, TaskStatus
    from sqlalchemy import select, func

    async with async_session() as db:
        downloading = (await db.execute(
            select(func.count()).where(DownloadTask.status == TaskStatus.DOWNLOADING)
        )).scalar() or 0
        completed = (await db.execute(
            select(func.count()).where(DownloadTask.status == TaskStatus.COMPLETED)
        )).scalar() or 0
        failed = (await db.execute(
            select(func.count()).where(DownloadTask.status == TaskStatus.FAILED)
        )).scalar() or 0
        subs = (await db.execute(
            select(func.count()).select_from(Subscription)
        )).scalar() or 0

    return {
        "subscriptions": subs,
        "downloading": downloading,
        "completed": completed,
        "failed": failed,
    }


# ==================== 注册路由 ====================

from routers import auth, download, subscription, task

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(download.router, prefix="/api/download", tags=["下载"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["订阅"])
app.include_router(task.router, prefix="/api/task", tags=["任务"])


# ==================== 静态文件 + SPA Fallback ====================

frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    from fastapi.responses import FileResponse

    # 静态资源（js/css/images）
    app.mount("/assets", StaticFiles(directory=os.path.join(frontend_dist, "assets")), name="assets")

    # SPA fallback：所有非 /api 路径返回 index.html
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # 尝试直接提供静态文件（如 favicon.ico）
        file_path = os.path.join(frontend_dist, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        # 否则返回 index.html，由 Vue Router 处理
        return FileResponse(os.path.join(frontend_dist, "index.html"))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )
