"""
手动剧集路由
- 创建/编辑/删除剧集
- 添加/编辑/删除单集
- 批量下载
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List

from database import get_db
from models import (
    ManualSeries, SeriesEpisode, DownloadTask,
    SeriesStatus, TaskStatus, Platform,
)
from config import settings

router = APIRouter()


# ---------- Pydantic Schemas ----------

class CreateSeriesRequest(BaseModel):
    title: str
    description: str = ""
    platform: str = "bilibili"
    season: int = 1


class AddEpisodeRequest(BaseModel):
    video_url: str
    title: str = ""
    episode_number: int = 0  # 0 = 自动分配


class AddEpisodesBatchRequest(BaseModel):
    urls: List[str]  # 多个 URL，自动分配集号


class UpdateEpisodeRequest(BaseModel):
    title: str = ""
    episode_number: int = 0


class UpdateSeriesRequest(BaseModel):
    title: str = ""
    description: str = ""
    poster_url: str = ""
    season: int = 0


# ---------- Series CRUD ----------

@router.post("")
async def create_series(req: CreateSeriesRequest, db: AsyncSession = Depends(get_db)):
    """创建手动剧集"""
    platform = Platform.BILIBILI if req.platform == "bilibili" else Platform.YOUTUBE
    series = ManualSeries(
        title=req.title,
        description=req.description,
        platform=platform,
        season=req.season,
        category=settings.dir_series,
    )
    db.add(series)
    await db.commit()
    await db.refresh(series)
    return {"id": series.id, "title": series.title}


@router.get("")
async def list_series(db: AsyncSession = Depends(get_db)):
    """列出所有手动剧集"""
    result = await db.execute(
        select(ManualSeries)
        .options(selectinload(ManualSeries.episodes))
        .order_by(ManualSeries.created_at.desc())
    )
    items = result.scalars().all()
    return [
        {
            "id": s.id,
            "title": s.title,
            "description": s.description,
            "platform": s.platform.value,
            "season": s.season,
            "status": s.status.value,
            "episode_count": len(s.episodes),
            "poster_url": s.poster_url,
            "created_at": s.created_at.isoformat() if s.created_at else "",
        }
        for s in items
    ]


@router.get("/{series_id}")
async def get_series(series_id: int, db: AsyncSession = Depends(get_db)):
    """获取剧集详情"""
    result = await db.execute(
        select(ManualSeries)
        .options(selectinload(ManualSeries.episodes))
        .where(ManualSeries.id == series_id)
    )
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")
    return {
        "id": s.id,
        "title": s.title,
        "description": s.description,
        "platform": s.platform.value,
        "season": s.season,
        "status": s.status.value,
        "poster_url": s.poster_url,
        "episodes": [
            {
                "id": ep.id,
                "episode_number": ep.episode_number,
                "video_url": ep.video_url,
                "title": ep.title,
                "thumbnail": ep.thumbnail,
                "duration": ep.duration,
                "status": ep.status.value,
                "download_task_id": ep.download_task_id,
            }
            for ep in sorted(s.episodes, key=lambda x: x.episode_number)
        ],
    }


@router.delete("/{series_id}")
async def delete_series(series_id: int, db: AsyncSession = Depends(get_db)):
    """删除剧集"""
    result = await db.execute(select(ManualSeries).where(ManualSeries.id == series_id))
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")
    await db.delete(s)
    await db.commit()
    return {"success": True}


@router.put("/{series_id}")
async def update_series(series_id: int, req: UpdateSeriesRequest, db: AsyncSession = Depends(get_db)):
    """更新剧集信息"""
    result = await db.execute(select(ManualSeries).where(ManualSeries.id == series_id))
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")
    if req.title:
        s.title = req.title
    if req.description is not None:
        s.description = req.description
    if req.poster_url is not None:
        s.poster_url = req.poster_url
    if req.season > 0:
        s.season = req.season
    await db.commit()
    return {"success": True}


# ---------- Episode CRUD ----------

@router.post("/{series_id}/episodes")
async def add_episode(series_id: int, req: AddEpisodeRequest, db: AsyncSession = Depends(get_db)):
    """添加单集"""
    result = await db.execute(
        select(ManualSeries).options(selectinload(ManualSeries.episodes)).where(ManualSeries.id == series_id)
    )
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")

    # 自动分配集号
    ep_num = req.episode_number
    if ep_num <= 0:
        existing_nums = [ep.episode_number for ep in s.episodes]
        ep_num = max(existing_nums) + 1 if existing_nums else 1

    # 尝试解析视频标题
    title = req.title
    thumbnail = ""
    duration = 0
    if not title:
        try:
            import asyncio
            from services.downloader import extract_info
            cookies = settings.bilibili_cookies_file if s.platform == Platform.BILIBILI else settings.youtube_cookies_file
            info = await asyncio.to_thread(
                extract_info, req.video_url,
                proxy=settings.proxy, cookies_file=cookies,
            )
            title = info.get("title", "")
            thumbnail = info.get("thumbnail", "")
            duration = info.get("duration", 0)
        except Exception:
            title = f"第 {ep_num} 集"

    episode = SeriesEpisode(
        series_id=series_id,
        episode_number=ep_num,
        video_url=req.video_url,
        title=title,
        thumbnail=thumbnail,
        duration=duration,
    )
    db.add(episode)
    await db.commit()
    await db.refresh(episode)

    return {
        "id": episode.id,
        "episode_number": episode.episode_number,
        "title": episode.title,
        "thumbnail": episode.thumbnail,
        "duration": episode.duration,
    }


@router.post("/{series_id}/episodes/batch")
async def add_episodes_batch(series_id: int, req: AddEpisodesBatchRequest, db: AsyncSession = Depends(get_db)):
    """批量添加多集"""
    result = await db.execute(
        select(ManualSeries).options(selectinload(ManualSeries.episodes)).where(ManualSeries.id == series_id)
    )
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")

    existing_nums = [ep.episode_number for ep in s.episodes]
    next_num = max(existing_nums) + 1 if existing_nums else 1

    added = []
    for url in req.urls:
        url = url.strip()
        if not url:
            continue
        episode = SeriesEpisode(
            series_id=series_id,
            episode_number=next_num,
            video_url=url,
            title=f"第 {next_num} 集",
        )
        db.add(episode)
        next_num += 1
        added.append({"episode_number": episode.episode_number, "video_url": url})

    await db.commit()
    return {"added": len(added), "episodes": added}


@router.put("/{series_id}/episodes/{episode_id}")
async def update_episode(series_id: int, episode_id: int, req: UpdateEpisodeRequest, db: AsyncSession = Depends(get_db)):
    """修改单集信息"""
    result = await db.execute(
        select(SeriesEpisode).where(SeriesEpisode.id == episode_id, SeriesEpisode.series_id == series_id)
    )
    ep = result.scalar()
    if not ep:
        raise HTTPException(404, "集不存在")
    if req.title:
        ep.title = req.title
    if req.episode_number > 0:
        ep.episode_number = req.episode_number
    await db.commit()
    return {"success": True}


@router.delete("/{series_id}/episodes/{episode_id}")
async def delete_episode(series_id: int, episode_id: int, db: AsyncSession = Depends(get_db)):
    """删除单集"""
    result = await db.execute(
        select(SeriesEpisode).where(SeriesEpisode.id == episode_id, SeriesEpisode.series_id == series_id)
    )
    ep = result.scalar()
    if not ep:
        raise HTTPException(404, "集不存在")
    await db.delete(ep)
    await db.commit()
    return {"success": True}


# ---------- Download ----------

@router.post("/{series_id}/download")
async def download_series(series_id: int, db: AsyncSession = Depends(get_db)):
    """
    批量下载整个剧集
    - 已下载过的视频：直接移动文件到剧集目录
    - 未下载过的视频：创建下载任务
    """
    import os
    import shutil
    import redis.asyncio as aioredis
    from models import DownloadHistory
    from services.file_organizer import build_tvshow_path, ensure_dirs, sanitize_filename
    from services.nfo_generator import generate_tvshow_nfo, generate_episode_nfo, save_nfo

    result = await db.execute(
        select(ManualSeries).options(selectinload(ManualSeries.episodes)).where(ManualSeries.id == series_id)
    )
    s = result.scalar()
    if not s:
        raise HTTPException(404, "剧集不存在")

    pending_eps = [ep for ep in s.episodes if ep.status in (TaskStatus.PENDING, TaskStatus.FAILED)]
    if not pending_eps:
        raise HTTPException(400, "没有待下载的集")

    r = aioredis.from_url(settings.redis_dsn, decode_responses=True)
    created = 0
    moved = 0
    category = s.category or settings.dir_series

    try:
        for ep in pending_eps:
            # 1. 检查是否已经下载过（通过 video_url 匹配 DownloadHistory）
            history_result = await db.execute(
                select(DownloadHistory).where(DownloadHistory.video_url == ep.video_url)
            )
            existing = history_result.scalar()

            if existing and existing.file_path and os.path.exists(existing.file_path):
                # 已下载 → 移动文件到剧集目录
                ext = os.path.splitext(existing.file_path)[1] or ".mp4"
                year = ""
                paths = build_tvshow_path(
                    settings.download_dir, category, s.title, year,
                    season=s.season, episode=ep.episode_number,
                    episode_title=ep.title,
                    codec=existing.codec or "",
                    ext=ext,
                )
                ensure_dirs(paths)

                # 移动视频文件
                shutil.move(existing.file_path, paths["video"])

                # 移动同目录的相关文件（nfo, 字幕, 缩略图等）
                src_dir = os.path.dirname(existing.file_path)
                src_base = os.path.splitext(os.path.basename(existing.file_path))[0]
                for f in os.listdir(src_dir):
                    if f.startswith(src_base) and f != os.path.basename(existing.file_path):
                        shutil.move(os.path.join(src_dir, f), os.path.join(paths["season_dir"], f))

                # 移动封面
                for poster_name in ["poster.jpg", "poster.webp", "poster.png"]:
                    poster_src = os.path.join(src_dir, poster_name)
                    if os.path.exists(poster_src):
                        shutil.move(poster_src, os.path.join(paths["season_dir"], poster_name))

                # 清理空的源目录
                try:
                    if not os.listdir(src_dir):
                        os.rmdir(src_dir)
                except Exception:
                    pass

                # 生成 episode.nfo（带角色信息）
                ep_nfo = generate_episode_nfo(
                    title=ep.title,
                    season=s.season,
                    episode=ep.episode_number,
                    plot="",
                    director=existing.channel_name or "",
                    video_url=ep.video_url,
                    video_id=existing.video_id or "",
                    platform=s.platform.value,
                    thumb_filename=os.path.basename(paths["thumb"]) if os.path.exists(paths.get("thumb", "")) else "",
                    duration_seconds=ep.duration,
                )
                save_nfo(ep_nfo, paths["nfo"])

                # 更新历史记录的文件路径
                existing.file_path = paths["video"]
                ep.status = TaskStatus.COMPLETED
                moved += 1
            else:
                # 未下载 → 创建下载任务（标记为剧集集数）
                task = DownloadTask(
                    platform=s.platform,
                    video_url=ep.video_url,
                    title=ep.title,
                    status=TaskStatus.PENDING,
                )
                db.add(task)
                await db.flush()

                ep.download_task_id = task.id
                ep.status = TaskStatus.PENDING
                await r.rpush("download_queue", str(task.id))
                created += 1

        # 生成 tvshow.nfo（剧集根目录）
        year = ""
        tvshow_paths = build_tvshow_path(
            settings.download_dir, category, s.title, year,
            season=s.season, episode=1,
        )
        ensure_dirs(tvshow_paths)
        tvshow_nfo = generate_tvshow_nfo(
            title=s.title,
            plot=s.description,
            studio=s.platform.value.capitalize(),
            platform=s.platform.value,
            tags=[category, s.platform.value.capitalize()],
        )
        save_nfo(tvshow_nfo, tvshow_paths["tvshow_nfo"])

        s.status = SeriesStatus.DOWNLOADING if created > 0 else (
            SeriesStatus.COMPLETED if moved == len(pending_eps) else SeriesStatus.PARTIAL
        )
        await db.commit()
    finally:
        await r.close()

    return {
        "success": True,
        "tasks_created": created,
        "files_moved": moved,
        "message": f"移动 {moved} 个已下载文件，新建 {created} 个下载任务",
    }
