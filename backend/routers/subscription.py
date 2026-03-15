"""
订阅管理路由
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional

from database import get_db
from models import Subscription, Platform, SubType, CodecStrategy, OrgMode
from config import settings

router = APIRouter()


class SubCreate(BaseModel):
    platform: str          # youtube / bilibili
    sub_type: str          # channel / playlist / favorites / bangumi / watch_later
    url: str
    name: str = ""
    download_dir: str = ""
    codec_strategy: str = "dual"
    preferred_codec: str = ""
    max_resolution: str = ""
    subtitle_langs: str = "zh-Hans,en,ja"
    org_mode: str = "by_year"
    check_interval: int = 3600


class SubUpdate(BaseModel):
    name: Optional[str] = None
    codec_strategy: Optional[str] = None
    preferred_codec: Optional[str] = None
    max_resolution: Optional[str] = None
    subtitle_langs: Optional[str] = None
    org_mode: Optional[str] = None
    check_interval: Optional[int] = None
    enabled: Optional[bool] = None


@router.get("/list")
async def list_subscriptions(db: AsyncSession = Depends(get_db)):
    """获取所有订阅"""
    result = await db.execute(select(Subscription).order_by(Subscription.created_at.desc()))
    subs = result.scalars().all()
    return [
        {
            "id": s.id,
            "platform": s.platform.value,
            "sub_type": s.sub_type.value,
            "url": s.url,
            "name": s.name,
            "thumbnail": s.thumbnail,
            "codec_strategy": s.codec_strategy.value,
            "preferred_codec": s.preferred_codec,
            "max_resolution": s.max_resolution,
            "org_mode": s.org_mode.value,
            "check_interval": s.check_interval,
            "enabled": s.enabled,
            "last_checked": s.last_checked.isoformat() if s.last_checked else None,
        }
        for s in subs
    ]


@router.post("/create")
async def create_subscription(req: SubCreate, db: AsyncSession = Depends(get_db)):
    """创建新订阅"""
    # 获取频道/播放列表信息
    name = req.name
    thumbnail = ""

    if not name:
        try:
            from services.downloader import extract_flat
            cookies = settings.youtube_cookies_file
            if req.platform == "bilibili":
                cookies = settings.bilibili_cookies_file
            info = extract_flat(req.url, proxy=settings.proxy, cookies_file=cookies)
            name = info.get("title", "") or info.get("uploader", "") or info.get("channel", "") or "未命名"
            # 尝试多种方式获取频道缩略图
            thumbnail = info.get("thumbnail", "")
            if not thumbnail:
                # 从 thumbnails 列表取最后一个（通常是最高质量）
                thumbs = info.get("thumbnails", [])
                if thumbs:
                    thumbnail = thumbs[-1].get("url", "")
            if not thumbnail:
                thumbnail = info.get("channel_url", "")  # 留作前端 fallback 标识
        except Exception:
            name = req.url

    sub = Subscription(
        platform=Platform(req.platform),
        sub_type=SubType(req.sub_type),
        url=req.url,
        name=name,
        thumbnail=thumbnail,
        download_dir=req.download_dir or settings.download_dir,
        codec_strategy=CodecStrategy(req.codec_strategy),
        preferred_codec=req.preferred_codec,
        max_resolution=req.max_resolution,
        subtitle_langs=req.subtitle_langs,
        org_mode=OrgMode(req.org_mode),
        check_interval=req.check_interval,
        enabled=True,
    )
    db.add(sub)
    await db.commit()
    await db.refresh(sub)

    return {"id": sub.id, "name": sub.name, "message": "订阅创建成功"}


@router.put("/{sub_id}")
async def update_subscription(sub_id: int, req: SubUpdate, db: AsyncSession = Depends(get_db)):
    """更新订阅配置"""
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar()
    if not sub:
        raise HTTPException(404, "订阅不存在")

    for field, value in req.model_dump(exclude_none=True).items():
        if field == "codec_strategy":
            setattr(sub, field, CodecStrategy(value))
        elif field == "org_mode":
            setattr(sub, field, OrgMode(value))
        else:
            setattr(sub, field, value)

    await db.commit()
    return {"success": True}


@router.delete("/{sub_id}")
async def delete_subscription(sub_id: int, db: AsyncSession = Depends(get_db)):
    """删除订阅"""
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar()
    if not sub:
        raise HTTPException(404, "订阅不存在")
    await db.delete(sub)
    await db.commit()
    return {"success": True}


@router.post("/{sub_id}/check")
async def check_now(sub_id: int, db: AsyncSession = Depends(get_db)):
    """立即检查某个订阅的新视频"""
    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar()
    if not sub:
        raise HTTPException(404, "订阅不存在")

    from main import redis_client
    await redis_client.rpush("check_subscription", str(sub_id))

    return {"message": f"已触发检查: {sub.name}"}


@router.get("/{sub_id}/tasks")
async def subscription_tasks(sub_id: int, db: AsyncSession = Depends(get_db)):
    """获取订阅下的所有下载任务"""
    from models import DownloadTask
    from sqlalchemy import desc

    result = await db.execute(select(Subscription).where(Subscription.id == sub_id))
    sub = result.scalar()
    if not sub:
        raise HTTPException(404, "订阅不存在")

    task_result = await db.execute(
        select(DownloadTask)
        .where(DownloadTask.subscription_id == sub_id)
        .order_by(desc(DownloadTask.created_at))
    )
    tasks = task_result.scalars().all()

    return [
        {
            "id": t.id,
            "title": t.title,
            "video_url": t.video_url,
            "thumbnail": t.thumbnail,
            "codec": t.codec,
            "resolution": t.resolution,
            "status": t.status.value,
            "progress": t.progress,
            "error_msg": t.error_msg,
            "created_at": t.created_at.isoformat() if t.created_at else "",
        }
        for t in tasks
    ]


@router.post("/check-all")
async def check_all_subscriptions(db: AsyncSession = Depends(get_db)):
    """立即检查所有启用的订阅"""
    result = await db.execute(select(Subscription).where(Subscription.enabled == True))
    subs = result.scalars().all()
    from main import redis_client
    for sub in subs:
        await redis_client.rpush("check_subscription", str(sub.id))
    return {"message": f"已触发 {len(subs)} 个订阅检查"}
