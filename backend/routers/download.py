"""
下载路由
- 单次下载（URL → 解析 → 下载）
"""
from fastapi import APIRouter, Depends, HTTPException, WebSocket
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from models import DownloadTask, DownloadHistory, TaskStatus, Platform
from config import settings

router = APIRouter()


class ParseRequest(BaseModel):
    url: str


class DownloadRequest(BaseModel):
    url: str
    title: str = ""
    codec: str = ""            # vp9, av1, hevc, h264
    max_resolution: str = ""   # 2160p, 1080p, 720p
    subtitle_langs: str = "zh-Hans,en,ja"
    category: str = "YouTube"  # Emby 分类目录
    format_string: str = ""    # 高级：自定义 format


@router.post("/parse")
async def parse_url(req: ParseRequest):
    """解析视频 URL，返回视频信息和可用格式"""
    import asyncio
    from services.downloader import extract_info, get_available_formats

    # 判断平台和 cookie
    cookies_file = settings.youtube_cookies_file
    if "bilibili" in req.url or "b23.tv" in req.url:
        cookies_file = settings.bilibili_cookies_file

    try:
        info = await asyncio.to_thread(
            extract_info, req.url,
            proxy=settings.proxy, cookies_file=cookies_file,
        )
    except Exception as e:
        raise HTTPException(400, f"解析失败: {str(e)}")

    formats = await asyncio.to_thread(
        get_available_formats, req.url,
        proxy=settings.proxy, cookies_file=cookies_file,
    )

    # 判断平台
    platform = "youtube"
    if "bilibili" in req.url or "b23.tv" in req.url:
        platform = "bilibili"

    return {
        "title": info.get("title", ""),
        "description": info.get("description", ""),
        "thumbnail": info.get("thumbnail", ""),
        "duration": info.get("duration", 0),
        "uploader": info.get("uploader", ""),
        "uploader_url": info.get("uploader_url", ""),
        "upload_date": info.get("upload_date", ""),
        "view_count": info.get("view_count", 0),
        "webpage_url": info.get("webpage_url", req.url),
        "id": info.get("id", ""),
        "platform": platform,
        "formats": formats,
    }


@router.post("/start")
async def start_download(req: DownloadRequest, db: AsyncSession = Depends(get_db)):
    """创建下载任务"""
    from services.downloader import build_format_string

    # 判断平台
    platform = Platform.YOUTUBE
    cookies_file = settings.youtube_cookies_file
    if "bilibili" in req.url or "b23.tv" in req.url:
        platform = Platform.BILIBILI
        cookies_file = settings.bilibili_cookies_file

    # 构建 format string
    format_str = req.format_string
    if not format_str and req.codec:
        format_str = build_format_string(req.codec, req.max_resolution)
    if not format_str:
        format_str = "bestvideo+bestaudio/best"

    # 创建任务
    task = DownloadTask(
        platform=platform,
        video_url=req.url,
        title=req.title,
        codec=req.codec,
        resolution=req.max_resolution,
        status=TaskStatus.PENDING,
    )
    db.add(task)
    await db.commit()
    await db.refresh(task)

    # 异步执行下载（通过 Redis 队列）
    import redis.asyncio as aioredis
    from main import redis_client
    await redis_client.rpush("download_queue", str(task.id))

    return {
        "task_id": task.id,
        "status": "pending",
        "message": "任务已加入队列",
    }


@router.websocket("/ws/{task_id}")
async def download_progress(websocket: WebSocket, task_id: int):
    """WebSocket 下载进度"""
    await websocket.accept()

    from main import redis_client
    import json

    try:
        while True:
            # 从 Redis 获取进度
            progress_key = f"task_progress:{task_id}"
            data = await redis_client.get(progress_key)
            if data:
                await websocket.send_json(json.loads(data))
                parsed = json.loads(data)
                if parsed.get("status") in ("completed", "failed"):
                    break

            import asyncio
            await asyncio.sleep(1)
    except Exception:
        pass
    finally:
        await websocket.close()
