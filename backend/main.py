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
import logging

# 文件日志
log_file = os.environ.get("YTDLP_LOG_FILE", "/data/ytdlp.log")
os.makedirs(os.path.dirname(log_file), exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(log_file, encoding="utf-8"),
    ],
)


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
    description="视频下载管理平台 API —— 支持 YouTube / Bilibili",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
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


# ==================== 缩略图代理 ====================

@app.get("/api/thumb")
async def thumb_proxy(url: str):
    """代理并缓存远程缩略图"""
    import hashlib
    import httpx
    from fastapi.responses import FileResponse

    if not url:
        return JSONResponse({"error": "no url"}, 404)

    # 用 URL hash 做文件名
    url_hash = hashlib.md5(url.encode()).hexdigest()
    cache_dir = os.path.join(settings.download_dir, ".thumbs")
    os.makedirs(cache_dir, exist_ok=True)

    # 尝试找已缓存文件
    for ext in [".webp", ".jpg", ".png"]:
        cached = os.path.join(cache_dir, url_hash + ext)
        if os.path.exists(cached):
            return FileResponse(cached, media_type=f"image/{'jpeg' if ext == '.jpg' else ext[1:]}")

    # 下载并缓存
    try:
        async with httpx.AsyncClient(timeout=10, follow_redirects=True) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return JSONResponse({"error": "fetch failed"}, 502)

            ct = resp.headers.get("content-type", "")
            ext = ".jpg"
            if "webp" in ct:
                ext = ".webp"
            elif "png" in ct:
                ext = ".png"

            cached = os.path.join(cache_dir, url_hash + ext)
            with open(cached, "wb") as f:
                f.write(resp.content)

            return FileResponse(cached, media_type=ct or "image/jpeg")
    except Exception:
        return JSONResponse({"error": "proxy failed"}, 502)


# ==================== 版本检查 ====================

def _get_current_version():
    """读取当前版本号"""
    version_file = os.path.join(os.path.dirname(__file__), "..", "VERSION")
    try:
        with open(version_file) as f:
            return f.read().strip()
    except FileNotFoundError:
        return "1.0.0"


@app.get("/api/check-update")
async def check_update():
    """检查 GitHub 是否有新版本"""
    import httpx

    current = _get_current_version()
    repo = settings.github_repo
    if not repo:
        return {"current": current, "latest": current, "has_update": False, "message": "未配置 GitHub 仓库"}

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"https://api.github.com/repos/{repo}/releases/latest",
                headers={"Accept": "application/vnd.github.v3+json"},
            )
            if resp.status_code == 404:
                # 没有 release，尝试用 tags
                resp = await client.get(
                    f"https://api.github.com/repos/{repo}/tags",
                    headers={"Accept": "application/vnd.github.v3+json"},
                )
                if resp.status_code == 200:
                    tags = resp.json()
                    latest = tags[0]["name"].lstrip("v") if tags else current
                else:
                    return {"current": current, "latest": current, "has_update": False, "message": "查询失败"}
            elif resp.status_code == 200:
                data = resp.json()
                latest = data.get("tag_name", current).lstrip("v")
            else:
                return {"current": current, "latest": current, "has_update": False, "message": f"API {resp.status_code}"}

        has_update = latest != current
        return {
            "current": current,
            "latest": latest,
            "has_update": has_update,
            "message": f"新版本 {latest} 可用" if has_update else "已是最新版本",
            "release_url": f"https://github.com/{repo}/releases" if has_update else "",
        }
    except Exception as e:
        return {"current": current, "latest": current, "has_update": False, "message": f"检查失败: {e}"}


@app.post("/api/update")
async def trigger_update():
    """触发一键更新：git pull + docker compose rebuild"""
    import subprocess
    import asyncio

    project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    async def _do_update():
        try:
            # git pull
            proc = await asyncio.create_subprocess_exec(
                "git", "pull", "--ff-only",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()
            pull_msg = stdout.decode() + stderr.decode()

            if proc.returncode != 0:
                return {"success": False, "message": f"git pull 失败: {pull_msg}"}

            # 前端重新构建
            npm_proc = await asyncio.create_subprocess_exec(
                "npm", "run", "build",
                cwd=os.path.join(project_dir, "frontend"),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await npm_proc.communicate()

            # docker compose rebuild
            dc_proc = await asyncio.create_subprocess_exec(
                "docker", "compose", "up", "-d", "--build",
                cwd=project_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await dc_proc.communicate()

            return {"success": True, "message": f"更新完成，容器已重建\n{pull_msg}"}
        except Exception as e:
            return {"success": False, "message": f"更新失败: {e}"}

    # 在后台执行，立即返回
    asyncio.create_task(_do_update())
    return {"success": True, "message": "更新已触发，容器将在约 30 秒后重建"}


# ==================== 设置 API ====================

@app.get("/api/settings")
async def get_settings():
    """获取当前设置"""
    return {
        "proxy": settings.proxy,
        "download_dir": settings.download_dir,
        "default_resolution": settings.default_resolution,
        "dir_videos": settings.dir_videos,
        "dir_series": settings.dir_series,
        "dir_collections": settings.dir_collections,
        "emby_url": settings.emby_url,
        "emby_api_key": settings.emby_api_key,
        "tmdb_api_key": settings.tmdb_api_key,
        "dev_mode": settings.dev_mode,
        "dev_max_items": settings.dev_max_items,
        "github_repo": settings.github_repo,
        "notify_type": settings.notify_type,
        "notify_token": settings.notify_token,
        "notify_webhook_url": settings.notify_webhook_url,
        "rate_limit": settings.rate_limit,
        "download_schedule": settings.download_schedule,
        "env_proxy": os.environ.get("YTDLP_PROXY", ""),
        "version": _get_current_version(),
    }


@app.post("/api/settings")
async def update_settings(request: Request):
    """更新配置"""
    data = await request.json()

    for key in ["download_dir", "proxy", "emby_url", "emby_api_key", "tmdb_api_key", "default_resolution",
                "dir_videos", "dir_series", "dir_collections", "dev_mode", "dev_max_items", "github_repo",
                "notify_type", "notify_token", "notify_webhook_url", "rate_limit", "download_schedule"]:
        if key in data:
            setattr(settings, key, data[key])

    settings.save_to_file()
    return {"success": True, "message": "配置已更新"}


@app.post("/api/notify/test", tags=["系统"])
async def test_notification():
    """测试通知推送"""
    from services.notifier import send_notification
    await send_notification("🔔 测试通知", "yt-dlp Web 通知配置成功！")
    return {"success": True, "message": "测试通知已发送"}


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
        pending = (await db.execute(
            select(func.count()).where(DownloadTask.status == TaskStatus.PENDING)
        )).scalar() or 0
        subs = (await db.execute(
            select(func.count()).select_from(Subscription)
        )).scalar() or 0

        # 今日下载量
        from datetime import datetime, timedelta
        today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        today_count = (await db.execute(
            select(func.count()).where(
                DownloadTask.status == TaskStatus.COMPLETED,
                DownloadTask.completed_at >= today_start,
            )
        )).scalar() or 0

        # 7天趋势
        trend = []
        for i in range(6, -1, -1):
            day = today_start - timedelta(days=i)
            next_day = day + timedelta(days=1)
            count = (await db.execute(
                select(func.count()).where(
                    DownloadTask.status == TaskStatus.COMPLETED,
                    DownloadTask.completed_at >= day,
                    DownloadTask.completed_at < next_day,
                )
            )).scalar() or 0
            trend.append({"date": day.strftime("%m-%d"), "count": count})

    # 存储占用
    total_size = 0
    try:
        import subprocess
        result = subprocess.run(
            ["du", "-sb", settings.download_dir],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode == 0:
            total_size = int(result.stdout.split()[0])
    except Exception:
        pass

    return {
        "subscriptions": subs,
        "downloading": downloading,
        "completed": completed,
        "failed": failed,
        "pending": pending,
        "today": today_count,
        "storage_bytes": total_size,
        "trend": trend,
    }


# ==================== 备份 / 恢复 ====================

@app.get("/api/backup", tags=["系统"])
async def backup_config():
    """导出配置和订阅数据"""
    from database import async_session
    from models import Subscription
    from sqlalchemy import select

    data = {
        "version": _get_current_version(),
        "settings": {
            "proxy": settings.proxy,
            "download_dir": settings.download_dir,
            "default_resolution": settings.default_resolution,
            "dir_videos": settings.dir_videos,
            "dir_series": settings.dir_series,
            "dir_collections": settings.dir_collections,
            "emby_url": settings.emby_url,
            "emby_api_key": settings.emby_api_key,
            "tmdb_api_key": settings.tmdb_api_key,
            "github_repo": settings.github_repo,
            "notify_type": settings.notify_type,
            "notify_token": settings.notify_token,
            "notify_webhook_url": settings.notify_webhook_url,
            "rate_limit": settings.rate_limit,
            "download_schedule": settings.download_schedule,
        },
        "subscriptions": [],
    }

    async with async_session() as db:
        result = await db.execute(select(Subscription))
        for s in result.scalars().all():
            data["subscriptions"].append({
                "platform": s.platform.value,
                "sub_type": s.sub_type.value,
                "url": s.url,
                "name": s.name,
                "codec_strategy": s.codec_strategy.value,
                "preferred_codec": s.preferred_codec,
                "max_resolution": s.max_resolution,
                "subtitle_langs": s.subtitle_langs,
                "org_mode": s.org_mode.value,
                "check_interval": s.check_interval,
                "enabled": s.enabled,
            })

    return data


@app.post("/api/restore", tags=["系统"])
async def restore_config(request: Request):
    """恢复配置和订阅数据"""
    data = await request.json()

    # 恢复设置
    if "settings" in data:
        for key, val in data["settings"].items():
            if hasattr(settings, key):
                setattr(settings, key, val)
        settings.save_to_file()

    # 恢复订阅
    if "subscriptions" in data:
        from database import async_session
        from models import Subscription, Platform, SubType, CodecStrategy, OrgMode
        from sqlalchemy import select

        async with async_session() as db:
            for sub_data in data["subscriptions"]:
                # 检查是否已存在
                existing = await db.execute(
                    select(Subscription).where(Subscription.url == sub_data["url"])
                )
                if existing.scalar():
                    continue

                sub = Subscription(
                    platform=Platform(sub_data["platform"]),
                    sub_type=SubType(sub_data["sub_type"]),
                    url=sub_data["url"],
                    name=sub_data.get("name", ""),
                    codec_strategy=CodecStrategy(sub_data.get("codec_strategy", "dual")),
                    preferred_codec=sub_data.get("preferred_codec", ""),
                    max_resolution=sub_data.get("max_resolution", ""),
                    subtitle_langs=sub_data.get("subtitle_langs", "zh-Hans,en,ja"),
                    org_mode=OrgMode(sub_data.get("org_mode", "by_year")),
                    check_interval=sub_data.get("check_interval", 3600),
                    enabled=sub_data.get("enabled", True),
                )
                db.add(sub)
            await db.commit()

    return {"success": True, "message": f"已恢复配置和 {len(data.get('subscriptions', []))} 个订阅"}


# ==================== 存储管理 ====================

@app.get("/api/storage", tags=["系统"])
async def storage_info():
    """获取存储详情"""
    import subprocess

    result_data = {"total": 0, "dirs": []}

    try:
        # 总占用
        result = subprocess.run(
            ["du", "-sb", settings.download_dir],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            result_data["total"] = int(result.stdout.split()[0])

        # 子目录占用
        result = subprocess.run(
            ["du", "-sb", "--max-depth=1", settings.download_dir],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t", 1)
                if len(parts) == 2 and parts[1] != settings.download_dir:
                    result_data["dirs"].append({
                        "path": os.path.basename(parts[1]),
                        "size": int(parts[0]),
                    })
            result_data["dirs"].sort(key=lambda x: x["size"], reverse=True)
    except Exception:
        pass

    # 磁盘信息
    try:
        import shutil
        usage = shutil.disk_usage(settings.download_dir)
        result_data["disk_total"] = usage.total
        result_data["disk_used"] = usage.used
        result_data["disk_free"] = usage.free
    except Exception:
        pass

    return result_data


@app.post("/api/storage/cleanup", tags=["系统"])
async def cleanup_storage():
    """清理缩略图缓存和临时文件"""
    import shutil

    cleaned = 0
    # 清理缩略图缓存
    thumbs_dir = os.path.join(settings.download_dir, ".thumbs")
    if os.path.exists(thumbs_dir):
        count = len(os.listdir(thumbs_dir))
        shutil.rmtree(thumbs_dir, ignore_errors=True)
        cleaned += count

    # 清理 .part 临时文件
    for root, dirs, files in os.walk(settings.download_dir):
        for f in files:
            if f.endswith(".part") or f.endswith(".ytdl"):
                try:
                    os.remove(os.path.join(root, f))
                    cleaned += 1
                except Exception:
                    pass

    return {"success": True, "message": f"已清理 {cleaned} 个临时文件"}


# ==================== 注册路由 ====================

from routers import auth, download, subscription, task, series, log, media

app.include_router(auth.router, prefix="/api/auth", tags=["认证"])
app.include_router(download.router, prefix="/api/download", tags=["下载"])
app.include_router(subscription.router, prefix="/api/subscription", tags=["订阅"])
app.include_router(task.router, prefix="/api/task", tags=["任务"])
app.include_router(series.router, prefix="/api/series", tags=["剧集"])
app.include_router(log.router, prefix="/api/logs", tags=["日志"])
app.include_router(media.router, prefix="/api/media", tags=["媒体"])


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
