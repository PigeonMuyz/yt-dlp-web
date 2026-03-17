"""
媒体文件路由 — 视频预览 / 流式播放
"""
import os
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from database import get_db
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

router = APIRouter()


@router.get("/stream/{task_id}")
async def stream_video(task_id: int, request: Request, db: AsyncSession = Depends(get_db)):
    """流式播放视频（支持 Range 请求）"""
    from models import DownloadTask
    from sqlalchemy import select

    result = await db.execute(select(DownloadTask).where(DownloadTask.id == task_id))
    task = result.scalar()
    if not task or not task.output_path:
        raise HTTPException(404, "视频不存在")

    file_path = task.output_path
    if not os.path.exists(file_path):
        # 尝试查找同目录同名的其他扩展名
        base = os.path.splitext(file_path)[0]
        for ext in [".mkv", ".mp4", ".webm"]:
            if os.path.exists(base + ext):
                file_path = base + ext
                break
        else:
            raise HTTPException(404, "文件不存在")

    file_size = os.path.getsize(file_path)

    # 推断 content-type
    ext = os.path.splitext(file_path)[1].lower()
    content_types = {
        ".mp4": "video/mp4",
        ".mkv": "video/x-matroska",
        ".webm": "video/webm",
    }
    content_type = content_types.get(ext, "video/mp4")

    # Range 请求
    range_header = request.headers.get("range")
    if range_header:
        range_val = range_header.strip().replace("bytes=", "")
        parts = range_val.split("-")
        start = int(parts[0])
        end = int(parts[1]) if parts[1] else file_size - 1
        length = end - start + 1

        def _iter():
            with open(file_path, "rb") as f:
                f.seek(start)
                remaining = length
                while remaining > 0:
                    chunk_size = min(8192, remaining)
                    data = f.read(chunk_size)
                    if not data:
                        break
                    remaining -= len(data)
                    yield data

        return StreamingResponse(
            _iter(),
            status_code=206,
            media_type=content_type,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
            },
        )

    # 完整文件
    return FileResponse(file_path, media_type=content_type)
