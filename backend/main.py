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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """启动和关闭"""
    global redis_client

    if settings.is_initialized():
        # 初始化数据库
        await init_db()
        # 连接 Redis
        redis_client = redis.from_url(settings.redis_dsn, decode_responses=True)
        # 启动调度器
        from services.scheduler import start_scheduler
        start_scheduler()
        print("✅ 服务启动完成")
    else:
        print("⚠️  首次启动，请访问 /api/setup 进行初始化配置")

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


# ==================== 初始化 API ====================

@app.get("/api/status")
async def get_status():
    """获取系统状态"""
    initialized = settings.is_initialized()
    db_ok = False
    redis_ok = False

    if initialized:
        db_ok = await check_db_connection()
        try:
            await redis_client.ping()
            redis_ok = True
        except Exception:
            pass

    return {
        "initialized": initialized,
        "database": db_ok,
        "redis": redis_ok,
        "version": "1.0.0",
    }


@app.post("/api/setup")
async def setup(request: Request):
    """
    首次初始化配置
    接收 PostgreSQL 和 Redis 连接信息
    """
    data = await request.json()

    # 更新配置
    if "db_host" in data:
        settings.db_host = data["db_host"]
    if "db_port" in data:
        settings.db_port = int(data["db_port"])
    if "db_name" in data:
        settings.db_name = data["db_name"]
    if "db_user" in data:
        settings.db_user = data["db_user"]
    if "db_password" in data:
        settings.db_password = data["db_password"]
    if "database_url" in data:
        settings.database_url = data["database_url"]

    if "redis_host" in data:
        settings.redis_host = data["redis_host"]
    if "redis_port" in data:
        settings.redis_port = int(data["redis_port"])
    if "redis_db" in data:
        settings.redis_db = int(data.get("redis_db", 0))
    if "redis_password" in data:
        settings.redis_password = data["redis_password"]
    if "redis_url" in data:
        settings.redis_url = data["redis_url"]

    if "download_dir" in data:
        settings.download_dir = data["download_dir"]
    if "proxy" in data:
        settings.proxy = data["proxy"]
    if "emby_url" in data:
        settings.emby_url = data["emby_url"]
    if "emby_api_key" in data:
        settings.emby_api_key = data["emby_api_key"]

    # 生成 secret key
    if settings.secret_key == "change-me-on-first-run":
        settings.secret_key = secrets.token_hex(32)

    # 设置管理员密码
    admin_password = data.get("admin_password", "")
    if not admin_password:
        return JSONResponse({"error": "请设置管理员密码"}, status_code=400)

    # 测试连接
    from database import engine
    from sqlalchemy.ext.asyncio import create_async_engine
    test_engine = create_async_engine(settings.pg_url)
    try:
        async with test_engine.connect() as conn:
            from sqlalchemy import text
            await conn.execute(text("SELECT 1"))
    except Exception as e:
        return JSONResponse({"error": f"数据库连接失败: {str(e)}"}, status_code=400)
    finally:
        await test_engine.dispose()

    # 测试 Redis
    try:
        test_redis = redis.from_url(settings.redis_dsn, decode_responses=True)
        await test_redis.ping()
        await test_redis.close()
    except Exception as e:
        return JSONResponse({"error": f"Redis 连接失败: {str(e)}"}, status_code=400)

    # 保存配置
    settings.save_to_file()

    # 初始化数据库表
    init_engine = create_async_engine(settings.pg_url)
    from models import Base
    async with init_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await init_engine.dispose()

    # 创建管理员账号
    from passlib.hash import bcrypt
    from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession
    init_engine2 = create_async_engine(settings.pg_url)
    session_factory = async_sessionmaker(init_engine2, class_=AsyncSession)
    async with session_factory() as session:
        from models import User
        from sqlalchemy import select
        existing = await session.execute(select(User).where(User.username == "admin"))
        if not existing.scalar():
            admin = User(
                username="admin",
                password_hash=bcrypt.hash(admin_password),
                is_admin=True,
            )
            session.add(admin)
            await session.commit()
    await init_engine2.dispose()

    return {
        "success": True,
        "message": "初始化完成！请重启服务。",
    }


# ==================== 注册路由 ====================

from routers import auth, download, subscription, task

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(download.router, prefix="/api/download", tags=["下载"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["订阅"])
app.include_router(task.router, prefix="/api/task", tags=["任务"])


# ==================== 静态文件 ====================

# 生产模式下提供前端静态文件
frontend_dist = os.path.join(os.path.dirname(__file__), "..", "frontend", "dist")
if os.path.exists(frontend_dist):
    app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.debug,
    )
