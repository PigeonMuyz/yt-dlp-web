"""
日志查看路由
"""
import os
import logging
from fastapi import APIRouter
from fastapi.responses import StreamingResponse

router = APIRouter()

LOG_FILE = os.environ.get("YTDLP_LOG_FILE", "/data/ytdlp.log")


@router.get("/recent")
async def get_recent_logs(lines: int = 200):
    """获取最近 N 行日志"""
    if not os.path.exists(LOG_FILE):
        return {"lines": [], "total": 0}

    try:
        with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
            all_lines = f.readlines()
        recent = all_lines[-lines:] if len(all_lines) > lines else all_lines
        return {
            "lines": [l.rstrip() for l in recent],
            "total": len(all_lines),
        }
    except Exception as e:
        return {"lines": [f"读取日志失败: {e}"], "total": 0}


@router.get("/download")
async def download_log():
    """下载完整日志文件"""
    if not os.path.exists(LOG_FILE):
        return {"error": "日志文件不存在"}

    def _iter():
        with open(LOG_FILE, "rb") as f:
            while chunk := f.read(8192):
                yield chunk

    return StreamingResponse(
        _iter(),
        media_type="text/plain",
        headers={"Content-Disposition": "attachment; filename=ytdlp.log"},
    )
