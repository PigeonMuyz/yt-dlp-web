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
            # ---- 检查是否已经下载过 ----
            # 方式1：关联的旧 DownloadTask 已完成
            existing_file = None
            existing_codec = ""
            existing_channel = ""
            existing_video_id = ""

            if ep.download_task_id:
                task_result = await db.execute(
                    select(DownloadTask).where(DownloadTask.id == ep.download_task_id)
                )
                old_task = task_result.scalar()
                if old_task and old_task.status == TaskStatus.COMPLETED and old_task.output_path:
                    # 尝试找到实际文件（路径可能不完全匹配）
                    if os.path.exists(old_task.output_path):
                        existing_file = old_task.output_path
                    else:
                        # 扫描同目录查找视频文件
                        task_dir = os.path.dirname(old_task.output_path)
                        if os.path.isdir(task_dir):
                            for f in os.listdir(task_dir):
                                if f.endswith(('.mp4', '.webm', '.mkv')):
                                    existing_file = os.path.join(task_dir, f)
                                    break
                    existing_codec = old_task.codec or ""
                    existing_channel = old_task.channel_name or ""
                    existing_video_id = old_task.video_id or ""

            # 方式2：DownloadHistory 匹配
            if not existing_file:
                history_result = await db.execute(
                    select(DownloadHistory).where(DownloadHistory.video_url == ep.video_url)
                )
                existing_hist = history_result.scalar()
                if existing_hist and existing_hist.file_path:
                    if os.path.exists(existing_hist.file_path):
                        existing_file = existing_hist.file_path
                    else:
                        hist_dir = os.path.dirname(existing_hist.file_path)
                        if os.path.isdir(hist_dir):
                            for f in os.listdir(hist_dir):
                                if f.endswith(('.mp4', '.webm', '.mkv')):
                                    existing_file = os.path.join(hist_dir, f)
                                    break
                    existing_codec = existing_hist.codec or existing_codec
                    existing_channel = existing_hist.channel_name or existing_channel
                    existing_video_id = existing_hist.video_id or existing_video_id

            if existing_file:
                # ---- 已下载 → 复制文件到剧集目录 ----
                ext = os.path.splitext(existing_file)[1] or ".mp4"
                year = ""
                paths = build_tvshow_path(
                    settings.download_dir, category, s.title, year,
                    season=s.season, episode=ep.episode_number,
                    episode_title=ep.title,
                    codec=existing_codec, ext=ext,
                )
                ensure_dirs(paths)

                # 复制视频文件（保留原始单品）
                import shutil
                shutil.copy2(existing_file, paths["video"])

                # 复制同目录的相关文件（字幕、缩略图）
                src_dir = os.path.dirname(existing_file)
                src_base = os.path.splitext(os.path.basename(existing_file))[0]
                for f in os.listdir(src_dir):
                    if f.startswith(src_base) and f != os.path.basename(existing_file):
                        dest = os.path.join(paths["season_dir"], f)
                        if not os.path.exists(dest):
                            shutil.copy2(os.path.join(src_dir, f), dest)

                # 复制封面
                for poster_name in ["poster.jpg", "poster.webp", "poster.png"]:
                    poster_src = os.path.join(src_dir, poster_name)
                    poster_dest = os.path.join(paths["season_dir"], poster_name)
                    if os.path.exists(poster_src) and not os.path.exists(poster_dest):
                        shutil.copy2(poster_src, poster_dest)

                # 生成 episode.nfo（带角色信息）
                ep_nfo = generate_episode_nfo(
                    title=ep.title,
                    season=s.season,
                    episode=ep.episode_number,
                    plot="",
                    director=existing_channel,
                    video_url=ep.video_url,
                    video_id=existing_video_id,
                    platform=s.platform.value,
                    thumb_filename=os.path.basename(paths.get("thumb", "")),
                    duration_seconds=ep.duration,
                )
                save_nfo(ep_nfo, paths["nfo"])

                ep.status = TaskStatus.COMPLETED
                moved += 1
            else:
                # ---- 未下载 → 创建下载任务 ----
                task = DownloadTask(
                    platform=s.platform,
                    video_url=ep.video_url,
                    title=ep.title,
                    status=TaskStatus.PENDING,
                    series_episode_id=ep.id,
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


# ---------- TMDB 搜索 ----------

@router.get("/tmdb/search")
async def tmdb_search(query: str, media_type: str = "tv"):
    """搜索 TMDB 获取剧集/电影元数据"""
    import aiohttp

    if not settings.tmdb_api_key:
        raise HTTPException(400, "未配置 TMDB API Key，请在系统设置中填写")

    search_url = f"https://api.themoviedb.org/3/search/{media_type}"
    params = {
        "api_key": settings.tmdb_api_key,
        "query": query,
        "language": "zh-CN",
        "page": 1,
    }

    async with aiohttp.ClientSession() as session:
        # 搜索
        async with session.get(search_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
            if resp.status != 200:
                raise HTTPException(resp.status, "TMDB 搜索失败")
            data = await resp.json()

    results = []
    for item in data.get("results", [])[:8]:
        title = item.get("name") or item.get("title") or ""
        overview = item.get("overview", "")
        poster_path = item.get("poster_path", "")
        backdrop_path = item.get("backdrop_path", "")
        year = (item.get("first_air_date") or item.get("release_date") or "")[:4]

        results.append({
            "tmdb_id": item["id"],
            "title": title,
            "original_title": item.get("original_name") or item.get("original_title") or "",
            "overview": overview,
            "poster_url": f"https://image.tmdb.org/t/p/w500{poster_path}" if poster_path else "",
            "backdrop_url": f"https://image.tmdb.org/t/p/w780{backdrop_path}" if backdrop_path else "",
            "year": year,
            "vote_average": item.get("vote_average", 0),
        })

    return results

