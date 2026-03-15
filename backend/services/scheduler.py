"""
定时任务调度器
所有 yt-dlp 同步调用通过 asyncio.to_thread 在线程池中执行，
避免阻塞 asyncio 事件循环导致 Web UI 无响应。
"""
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()


def start_scheduler():
    """启动调度器"""
    scheduler.add_job(
        process_download_queue,
        "interval",
        seconds=5,
        id="download_queue",
        replace_existing=True,
        max_instances=3,  # 允许并行下载
    )
    scheduler.add_job(
        check_subscriptions,
        "interval",
        seconds=60,
        id="check_subscriptions",
        replace_existing=True,
    )
    scheduler.start()


async def process_download_queue():
    """处理下载队列"""
    import redis.asyncio as aioredis
    from config import settings
    from database import async_session
    from models import DownloadTask, DownloadHistory, TaskStatus, Platform
    from services.downloader import download_video, build_format_string, extract_info
    from services.file_organizer import build_movie_path, ensure_dirs
    from services.nfo_generator import generate_movie_nfo, save_nfo
    from services.subtitle_converter import convert_all_subtitles
    import json, os
    from datetime import datetime

    r = aioredis.from_url(settings.redis_dsn, decode_responses=True)

    try:
        task_id = await r.lpop("download_queue")
        if not task_id:
            return

        async with async_session() as db:
            from sqlalchemy import select
            result = await db.execute(select(DownloadTask).where(DownloadTask.id == int(task_id)))
            task = result.scalar()
            if not task or task.status == TaskStatus.CANCELLED:
                return

            task.status = TaskStatus.DOWNLOADING
            await db.commit()

            try:
                # 获取视频信息 —— 在线程池中执行！
                cookies = settings.youtube_cookies_file
                if task.platform == Platform.BILIBILI:
                    cookies = settings.bilibili_cookies_file

                info = await asyncio.to_thread(
                    extract_info, task.video_url,
                    proxy=settings.proxy, cookies_file=cookies
                )

                task.title = task.title or info.get("title", "")
                task.video_id = info.get("id", "")
                task.channel_name = info.get("uploader", "")
                task.channel_url = info.get("uploader_url", "")
                task.upload_date = info.get("upload_date", "")
                task.duration = info.get("duration", 0)
                task.description = info.get("description", "")
                task.thumbnail = info.get("thumbnail", "")

                # 自动提取编码和分辨率（如果用户未指定）
                if not task.codec:
                    vcodec = info.get("vcodec", "")
                    if vcodec and vcodec != "none":
                        if "av01" in vcodec or "av1" in vcodec:
                            task.codec = "av1"
                        elif "vp9" in vcodec or "vp09" in vcodec:
                            task.codec = "vp9"
                        elif "avc" in vcodec or "h264" in vcodec:
                            task.codec = "h264"
                        elif "hev" in vcodec or "h265" in vcodec or "hevc" in vcodec:
                            task.codec = "hevc"
                        else:
                            task.codec = vcodec.split(".")[0]
                if not task.resolution:
                    height = info.get("height", 0)
                    if height:
                        task.resolution = f"{height}p"

                await db.commit()

                # 构建路径 —— 区分单品 vs 剧集
                year = task.upload_date[:4] if task.upload_date else ""
                ext = ".webm" if task.codec in ("vp9", "av1") else ".mp4"
                is_series_task = bool(task.series_episode_id)

                if is_series_task:
                    # 剧集任务：查找关联的 SeriesEpisode 和 ManualSeries
                    from models import SeriesEpisode, ManualSeries, SeriesStatus
                    ep_result = await db.execute(
                        select(SeriesEpisode).where(SeriesEpisode.id == task.series_episode_id)
                    )
                    series_ep = ep_result.scalar()
                    series_result = await db.execute(
                        select(ManualSeries).where(ManualSeries.id == series_ep.series_id)
                    ) if series_ep else None
                    series_obj = series_result.scalar() if series_result else None

                    if series_obj and series_ep:
                        category = series_obj.category or settings.dir_series
                        from services.file_organizer import build_tvshow_path
                        paths = build_tvshow_path(
                            settings.download_dir, category, series_obj.title, year,
                            season=series_obj.season, episode=series_ep.episode_number,
                            episode_title=task.title,
                            codec=task.codec, ext=ext,
                        )
                    else:
                        # fallback 到单品
                        is_series_task = False

                if not is_series_task:
                    # 单品任务
                    category = "YouTube" if task.platform == Platform.YOUTUBE else "B站"
                    paths = build_movie_path(
                        settings.download_dir, category, task.title, year,
                        codec=task.codec, ext=ext,
                    )

                ensure_dirs(paths)

                # 构建 format string
                format_str = build_format_string(task.codec, task.resolution) if task.codec else "bestvideo+bestaudio/best"

                # 进度回调（在下载线程中调用）
                def on_progress(data):
                    progress_data = json.dumps(data)
                    import redis as sync_redis
                    sr = sync_redis.from_url(settings.redis_dsn, decode_responses=True)
                    sr.set(f"task_progress:{task_id}", progress_data, ex=300)
                    sr.close()

                # 下载 —— 在线程池中执行！
                dl_info = await asyncio.to_thread(
                    download_video,
                    task.video_url,
                    output_path=paths["video"],
                    format_string=format_str,
                    subtitle_langs="zh-Hans,en,ja",
                    proxy=settings.proxy,
                    cookies_file=cookies,
                    progress_callback=on_progress,
                )

                # 字幕转换 —— 在线程池中执行
                await asyncio.to_thread(convert_all_subtitles, paths["subtitle_dir"])

                # 整理缩略图：yt-dlp 下载的缩略图可能是 .webp/.jpg/.png，重命名为标准封面
                thumb_found = False
                folder = paths.get("folder") or paths.get("season_dir") or os.path.dirname(paths["video"])
                for f in os.listdir(folder):
                    if any(f.endswith(ext) for ext in [".webp", ".jpg", ".jpeg", ".png"]):
                        if "thumb" not in f.lower() and f != os.path.basename(paths.get("thumb", "")):
                            src = os.path.join(folder, f)
                            # 检查是否是缩略图（小于 5MB 且是图片）
                            if os.path.getsize(src) < 5 * 1024 * 1024:
                                import shutil
                                # 复制为 poster.jpg（Emby 兼容） + 保留原文件 + 复制为 thumb
                                poster_path = os.path.join(folder, "poster" + os.path.splitext(f)[1])
                                if not os.path.exists(poster_path):
                                    shutil.copy2(src, poster_path)
                                if paths.get("thumb") and not os.path.exists(paths["thumb"]):
                                    shutil.copy2(src, paths["thumb"])
                                thumb_found = True
                                break

                # 生成 NFO（仅单品生成 movie.nfo，剧集 episode.nfo 在后面生成）
                premiered = ""
                if task.upload_date and len(task.upload_date) == 8:
                    premiered = f"{task.upload_date[:4]}-{task.upload_date[4:6]}-{task.upload_date[6:8]}"

                if not is_series_task:
                    nfo_content = generate_movie_nfo(
                        title=task.title,
                        plot=task.description[:2000] if task.description else "",
                        year=year,
                        premiered=premiered,
                        studio=task.channel_name,
                        director=task.channel_name,
                        video_url=task.video_url,
                        video_id=task.video_id,
                        platform=task.platform.value,
                        thumb_filename=os.path.basename(paths.get("thumb", "")),
                        duration_seconds=task.duration,
                        tags=[category],
                    )
                    save_nfo(nfo_content, paths["nfo"])

                # 更新任务状态
                actual_size = os.path.getsize(paths["video"]) if os.path.exists(paths["video"]) else 0
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.output_path = paths["video"]
                task.file_size = actual_size
                task.completed_at = datetime.utcnow()

                # 同步剧集状态
                if is_series_task and series_ep and series_obj:
                    series_ep.status = TaskStatus.COMPLETED
                    # 检查该剧集所有集是否全部完成
                    from sqlalchemy.orm import selectinload
                    all_eps_result = await db.execute(
                        select(SeriesEpisode).where(SeriesEpisode.series_id == series_obj.id)
                    )
                    all_eps = all_eps_result.scalars().all()
                    if all(ep.status == TaskStatus.COMPLETED for ep in all_eps):
                        series_obj.status = SeriesStatus.COMPLETED
                    else:
                        series_obj.status = SeriesStatus.PARTIAL

                    # 为剧集集数生成 episode.nfo
                    from services.nfo_generator import generate_episode_nfo, save_nfo as save_nfo_file
                    ep_nfo = generate_episode_nfo(
                        title=task.title,
                        season=series_obj.season,
                        episode=series_ep.episode_number,
                        plot=task.description[:2000] if task.description else "",
                        director=task.channel_name,
                        video_url=task.video_url,
                        video_id=task.video_id,
                        platform=task.platform.value,
                        thumb_filename=os.path.basename(paths.get("thumb", "")),
                        duration_seconds=task.duration,
                    )
                    save_nfo_file(ep_nfo, paths["nfo"])

                await db.commit()

                # 触发 Emby 库刷新
                if settings.emby_url and settings.emby_api_key:
                    try:
                        import aiohttp
                        emby_scan_url = f"{settings.emby_url.rstrip('/')}/Library/Refresh"
                        async with aiohttp.ClientSession() as session:
                            await session.post(
                                emby_scan_url,
                                params={"api_key": settings.emby_api_key},
                                timeout=aiohttp.ClientTimeout(total=10),
                            )
                    except Exception:
                        pass  # Emby 刷新失败不影响任务

                # 写下载历史
                history = DownloadHistory(
                    platform=task.platform,
                    video_id=task.video_id,
                    video_url=task.video_url,
                    title=task.title,
                    channel_name=task.channel_name,
                    codec=task.codec,
                    resolution=task.resolution,
                    file_path=paths["video"],
                    file_size=os.path.getsize(paths["video"]) if os.path.exists(paths["video"]) else 0,
                    nfo_path=paths["nfo"],
                )
                db.add(history)
                await db.commit()

                # 完成通知
                await r.set(
                    f"task_progress:{task_id}",
                    json.dumps({"status": "completed", "progress": "100%", "title": task.title}),
                    ex=300,
                )

            except Exception as e:
                task.status = TaskStatus.FAILED
                task.error_msg = str(e)[:1000]
                await db.commit()
                await r.set(
                    f"task_progress:{task_id}",
                    json.dumps({"status": "failed", "error": str(e)[:500]}),
                    ex=300,
                )
    finally:
        await r.close()


async def check_subscriptions():
    """检查到期的订阅"""
    from datetime import datetime, timedelta
    from database import async_session
    from models import Subscription
    from sqlalchemy import select, or_
    import redis.asyncio as aioredis
    from config import settings

    r = aioredis.from_url(settings.redis_dsn, decode_responses=True)

    try:
        sub_id = await r.lpop("check_subscription")
        if sub_id:
            await _check_single_subscription(int(sub_id))
            return

        async with async_session() as db:
            now = datetime.utcnow()
            result = await db.execute(
                select(Subscription).where(
                    Subscription.enabled == True,
                    or_(
                        Subscription.last_checked == None,
                        Subscription.last_checked < now - timedelta(seconds=3600),
                    ),
                )
            )
            subs = result.scalars().all()

            for sub in subs:
                if sub.last_checked:
                    elapsed = (now - sub.last_checked).total_seconds()
                    if elapsed < sub.check_interval:
                        continue
                await _check_single_subscription(sub.id)
    finally:
        await r.close()


async def _check_single_subscription(sub_id: int):
    """检查单个订阅的新视频"""
    from database import async_session
    from models import Subscription, DownloadTask, TaskStatus
    from services.downloader import extract_flat
    from config import settings
    from sqlalchemy import select
    from datetime import datetime
    import redis.asyncio as aioredis

    r = aioredis.from_url(settings.redis_dsn, decode_responses=True)

    try:
        async with async_session() as db:
            result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
            sub = result.scalar()
            if not sub:
                return

            cookies = settings.youtube_cookies_file
            if sub.platform.value == "bilibili":
                cookies = settings.bilibili_cookies_file

            # 获取视频列表 —— 在线程池中执行！
            try:
                info = await asyncio.to_thread(
                    extract_flat, sub.url,
                    proxy=settings.proxy, cookies_file=cookies
                )
            except Exception:
                return

            entries = info.get("entries", [])
            archive = set(sub.download_archive.split("\n")) if sub.download_archive else set()

            # 开发模式：限制最多处理 N 个视频
            if settings.dev_mode:
                entries = entries[:settings.dev_max_items]

            new_count = 0
            for entry in entries:
                vid = entry.get("id", "")
                if not vid or vid in archive:
                    continue

                url = entry.get("url", "")
                if not url:
                    if sub.platform.value == "youtube":
                        url = f"https://www.youtube.com/watch?v={vid}"
                    else:
                        url = f"https://www.bilibili.com/video/{vid}"

                task = DownloadTask(
                    platform=sub.platform,
                    video_url=url,
                    video_id=vid,
                    title=entry.get("title", ""),
                    codec=sub.preferred_codec,
                    resolution=sub.max_resolution,
                    status=TaskStatus.PENDING,
                    subscription_id=sub.id,
                )
                db.add(task)
                archive.add(vid)
                new_count += 1

            sub.download_archive = "\n".join(archive)
            sub.last_checked = datetime.utcnow()
            await db.commit()

            if new_count > 0:
                result = await db.execute(
                    select(DownloadTask).where(
                        DownloadTask.subscription_id == sub.id,
                        DownloadTask.status == TaskStatus.PENDING,
                    )
                )
                for task in result.scalars().all():
                    await r.rpush("download_queue", str(task.id))
    finally:
        await r.close()
