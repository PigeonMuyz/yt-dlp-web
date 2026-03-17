"""
下载任务路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from typing import List

from database import get_db
from models import DownloadTask, DownloadHistory, TaskStatus
from schemas import BatchRequest, SuccessResponse

router = APIRouter()


@router.get("/list")
async def list_tasks(
    status: str = "",
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """获取下载任务列表"""
    query = select(DownloadTask).order_by(desc(DownloadTask.created_at))
    if status:
        query = query.where(DownloadTask.status == TaskStatus(status))
    query = query.limit(limit).offset(offset)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # 从 Redis 批量读取下载中任务的实时进度
    import json
    import redis.asyncio as aioredis
    from config import settings
    progress_map = {}
    downloading_ids = [t.id for t in tasks if t.status == TaskStatus.DOWNLOADING]
    if downloading_ids:
        r = aioredis.from_url(settings.redis_dsn, decode_responses=True)
        try:
            keys = [f"task_progress:{tid}" for tid in downloading_ids]
            values = await r.mget(keys)
            for tid, val in zip(downloading_ids, values):
                if val:
                    try:
                        progress_map[tid] = json.loads(val)
                    except Exception:
                        pass
        finally:
            await r.close()

    items = []
    for t in tasks:
        p = progress_map.get(t.id, {})
        # 解析百分比字符串 "45.2%" -> 45
        progress_val = t.progress
        speed_val = t.speed or ""
        eta_val = t.eta or ""
        if p:
            pct_str = p.get("progress", "0%").replace("%", "").strip()
            try:
                progress_val = int(float(pct_str))
            except (ValueError, TypeError):
                pass
            speed_val = p.get("speed", speed_val) or speed_val
            eta_val = p.get("eta", eta_val) or eta_val

        items.append({
            "id": t.id,
            "platform": t.platform.value,
            "video_id": t.video_id,
            "title": t.title,
            "video_url": t.video_url,
            "thumbnail": t.thumbnail,
            "channel_name": t.channel_name,
            "codec": t.codec,
            "resolution": t.resolution,
            "file_size": t.file_size,
            "duration": t.duration,
            "output_path": t.output_path,
            "status": t.status.value,
            "progress": progress_val,
            "speed": speed_val,
            "eta": eta_val,
            "error_msg": t.error_msg,
            "created_at": t.created_at.isoformat() if t.created_at else "",
            "completed_at": t.completed_at.isoformat() if t.completed_at else "",
        })

    return items


@router.get("/stats")
async def task_stats(db: AsyncSession = Depends(get_db)):
    """任务统计"""
    from sqlalchemy import func

    counts = {}
    for status in TaskStatus:
        result = await db.execute(
            select(func.count(DownloadTask.id)).where(DownloadTask.status == status)
        )
        counts[status.value] = result.scalar()

    total_result = await db.execute(select(func.count(DownloadTask.id)))
    counts["total"] = total_result.scalar()

    return counts


@router.post("/{task_id}/retry")
async def retry_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """重试失败任务"""
    result = await db.execute(select(DownloadTask).where(DownloadTask.id == task_id))
    task = result.scalar()
    if not task:
        raise HTTPException(404, "任务不存在")
    if task.status != TaskStatus.FAILED:
        raise HTTPException(400, "只能重试失败的任务")

    task.status = TaskStatus.PENDING
    task.progress = 0
    task.error_msg = ""
    await db.commit()

    from main import redis_client
    await redis_client.rpush("download_queue", str(task.id))

    return {"success": True, "message": "已重新加入队列"}


@router.post("/{task_id}/cancel")
async def cancel_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """取消任务"""
    result = await db.execute(select(DownloadTask).where(DownloadTask.id == task_id))
    task = result.scalar()
    if not task:
        raise HTTPException(404, "任务不存在")

    task.status = TaskStatus.CANCELLED
    await db.commit()

    return {"success": True}


@router.delete("/{task_id}")
async def delete_task(task_id: int, db: AsyncSession = Depends(get_db)):
    """删除任务记录"""
    result = await db.execute(select(DownloadTask).where(DownloadTask.id == task_id))
    task = result.scalar()
    if not task:
        raise HTTPException(404, "任务不存在")
    await db.delete(task)
    await db.commit()
    return {"success": True}


@router.get("/history")
async def download_history(
    limit: int = 50,
    offset: int = 0,
    db: AsyncSession = Depends(get_db),
):
    """下载历史"""
    result = await db.execute(
        select(DownloadHistory)
        .order_by(desc(DownloadHistory.downloaded_at))
        .limit(limit).offset(offset)
    )
    items = result.scalars().all()
    return [
        {
            "id": h.id,
            "platform": h.platform.value,
            "video_id": h.video_id,
            "title": h.title,
            "channel_name": h.channel_name,
            "codec": h.codec,
            "resolution": h.resolution,
            "file_path": h.file_path,
            "file_size": h.file_size,
            "downloaded_at": h.downloaded_at.isoformat() if h.downloaded_at else "",
        }
        for h in items
    ]


@router.post("/batch", response_model=SuccessResponse)
async def batch_tasks(req: BatchRequest, db: AsyncSession = Depends(get_db)):
    """批量操作任务 — 支持 retry / delete / cancel"""
    from main import redis_client

    result = await db.execute(
        select(DownloadTask).where(DownloadTask.id.in_(req.ids))
    )
    tasks = result.scalars().all()

    count = 0
    for task in tasks:
        if req.action == "retry" and task.status == TaskStatus.FAILED:
            task.status = TaskStatus.PENDING
            task.progress = 0
            task.error_msg = ""
            await redis_client.rpush("download_queue", str(task.id))
            count += 1
        elif req.action == "delete":
            await db.delete(task)
            count += 1
        elif req.action == "cancel" and task.status == TaskStatus.PENDING:
            task.status = TaskStatus.CANCELLED
            count += 1

    await db.commit()
    return SuccessResponse(message=f"已处理 {count} 个任务")
