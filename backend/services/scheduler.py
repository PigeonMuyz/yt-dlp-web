"""
定时任务调度器
"""
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
    from services.file_organizer import build_movie_path, ensure_dirs, get_codec_label
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
                # 获取视频信息
                cookies = settings.youtube_cookies_file
                if task.platform == Platform.BILIBILI:
                    cookies = settings.bilibili_cookies_file

                info = extract_info(task.video_url, proxy=settings.proxy, cookies_file=cookies)
                task.title = task.title or info.get("title", "")
                task.video_id = info.get("id", "")
                task.channel_name = info.get("uploader", "")
                task.channel_url = info.get("uploader_url", "")
                task.upload_date = info.get("upload_date", "")
                task.duration = info.get("duration", 0)
                task.description = info.get("description", "")
                task.thumbnail = info.get("thumbnail", "")
                await db.commit()

                # 构建路径
                year = task.upload_date[:4] if task.upload_date else ""
                category = "YouTube" if task.platform == Platform.YOUTUBE else "B站"
                ext = ".webm" if task.codec in ("vp9", "av1") else ".mp4"

                paths = build_movie_path(
                    settings.download_dir, category, task.title, year,
                    codec=task.codec, ext=ext,
                )
                ensure_dirs(paths)

                # 构建 format string
                format_str = build_format_string(task.codec, task.resolution) if task.codec else "bestvideo+bestaudio/best"

                # 进度回调
                def on_progress(data):
                    import asyncio
                    progress_data = json.dumps(data)
                    # 同步写 Redis
                    import redis as sync_redis
                    sr = sync_redis.from_url(settings.redis_dsn, decode_responses=True)
                    sr.set(f"task_progress:{task_id}", progress_data, ex=300)
                    sr.close()

                # 下载
                dl_info = download_video(
                    task.video_url,
                    output_path=paths["video"],
                    format_string=format_str,
                    subtitle_langs=task.resolution or "zh-Hans,en,ja",
                    proxy=settings.proxy,
                    cookies_file=cookies,
                    progress_callback=on_progress,
                )

                # 转换字幕
                convert_all_subtitles(paths["subtitle_dir"])

                # 生成 NFO
                premiered = ""
                if task.upload_date and len(task.upload_date) == 8:
                    premiered = f"{task.upload_date[:4]}-{task.upload_date[4:6]}-{task.upload_date[6:8]}"

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
                    thumb_filename=os.path.basename(paths["thumb"]),
                    duration_seconds=task.duration,
                    tags=[category],
                )
                save_nfo(nfo_content, paths["nfo"])

                # 更新任务状态
                task.status = TaskStatus.COMPLETED
                task.progress = 100
                task.output_path = paths["video"]
                task.completed_at = datetime.utcnow()
                await db.commit()

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
        # 检查是否有手动触发的检查
        sub_id = await r.lpop("check_subscription")
        if sub_id:
            await _check_single_subscription(int(sub_id))
            return

        # 自动检查到期的订阅
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

            # 获取视频列表
            try:
                info = extract_flat(sub.url, proxy=settings.proxy, cookies_file=cookies)
            except Exception:
                return

            entries = info.get("entries", [])
            archive = set(sub.download_archive.split("\n")) if sub.download_archive else set()

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

                # 创建下载任务
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

            # 更新 archive 和 last_checked
            sub.download_archive = "\n".join(archive)
            sub.last_checked = datetime.utcnow()
            await db.commit()

            # 新任务加入队列
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
