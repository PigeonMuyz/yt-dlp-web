"""
API 请求/响应模型 — 用于 OpenAPI 文档自动生成
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ==================== 通用 ====================

class SuccessResponse(BaseModel):
    success: bool = True
    message: str = ""


# ==================== 下载 ====================

class ParseRequest(BaseModel):
    url: str = Field(..., description="视频/播放列表 URL")


class ParseResponse(BaseModel):
    title: str
    description: str = ""
    thumbnail: str = ""
    duration: int = 0
    uploader: str = ""
    uploader_url: str = ""
    upload_date: str = ""
    view_count: int = 0
    webpage_url: str = ""
    id: str = ""
    platform: str
    formats: list = []


class DownloadRequest(BaseModel):
    url: str = Field(..., description="视频 URL")
    title: str = ""
    codec: str = Field("", description="编码: vp9/av1/hevc/h264")
    max_resolution: str = Field("", description="分辨率: 2160p/1080p/720p")
    subtitle_langs: str = "zh-Hans,en,ja"
    category: str = "YouTube"
    format_string: str = Field("", description="高级: 自定义 yt-dlp format 字符串")


class DownloadStartResponse(BaseModel):
    task_id: int
    status: str = "pending"
    message: str


# ==================== 任务 ====================

class TaskItem(BaseModel):
    id: int
    platform: str
    video_id: Optional[str] = None
    title: Optional[str] = None
    video_url: Optional[str] = None
    thumbnail: Optional[str] = None
    channel_name: Optional[str] = None
    codec: Optional[str] = None
    resolution: Optional[str] = None
    file_size: Optional[int] = None
    duration: Optional[int] = None
    output_path: Optional[str] = None
    status: str
    progress: int = 0
    speed: str = ""
    eta: str = ""
    error_msg: Optional[str] = None
    created_at: str = ""
    completed_at: str = ""


class TaskStatsResponse(BaseModel):
    total: int = 0
    pending: int = 0
    downloading: int = 0
    completed: int = 0
    failed: int = 0
    cancelled: int = 0


class BatchRequest(BaseModel):
    action: str = Field(..., description="操作: retry/delete/cancel")
    ids: List[int] = Field(..., description="任务 ID 列表")


# ==================== 订阅 ====================

class SubCreate(BaseModel):
    platform: str = Field(..., description="平台: youtube/bilibili")
    sub_type: str = Field(..., description="类型: channel/playlist/favorites/bangumi/watch_later")
    url: str = Field(..., description="频道/播放列表 URL")
    name: str = ""
    download_dir: str = ""
    codec_strategy: str = Field("dual", description="编码策略: single/dual/all")
    preferred_codec: str = ""
    max_resolution: str = ""
    subtitle_langs: str = "zh-Hans,en,ja"
    org_mode: str = Field("by_year", description="目录组织: by_year/by_playlist/flat/season")
    check_interval: int = Field(3600, description="检查间隔(秒)")


class SubUpdate(BaseModel):
    name: Optional[str] = None
    codec_strategy: Optional[str] = None
    preferred_codec: Optional[str] = None
    max_resolution: Optional[str] = None
    subtitle_langs: Optional[str] = None
    org_mode: Optional[str] = None
    check_interval: Optional[int] = None
    enabled: Optional[bool] = None


class SubItem(BaseModel):
    id: int
    platform: str
    sub_type: str
    url: str
    name: str
    thumbnail: Optional[str] = None
    codec_strategy: str
    preferred_codec: str = ""
    max_resolution: str = ""
    org_mode: str
    check_interval: int
    enabled: bool
    last_checked: Optional[str] = None


# ==================== 历史 ====================

class HistoryItem(BaseModel):
    id: int
    platform: str
    video_id: str = ""
    title: str = ""
    channel_name: str = ""
    codec: str = ""
    resolution: str = ""
    file_path: str = ""
    file_size: int = 0
    downloaded_at: str = ""


# ==================== 设置 ====================

class SettingsResponse(BaseModel):
    proxy: str = ""
    download_dir: str = ""
    default_resolution: str = ""
    dir_videos: str = ""
    dir_series: str = ""
    dir_collections: str = ""
    emby_url: str = ""
    emby_api_key: str = ""
    tmdb_api_key: str = ""
    dev_mode: bool = False
    dev_max_items: int = 5
    github_repo: str = ""
    env_proxy: str = ""
    version: str = ""
    # 通知
    notify_type: str = ""
    notify_token: str = ""
    notify_webhook_url: str = ""
    # 限速
    rate_limit: int = 0


class SettingsUpdate(BaseModel):
    proxy: Optional[str] = None
    download_dir: Optional[str] = None
    default_resolution: Optional[str] = None
    dir_videos: Optional[str] = None
    dir_series: Optional[str] = None
    dir_collections: Optional[str] = None
    emby_url: Optional[str] = None
    emby_api_key: Optional[str] = None
    tmdb_api_key: Optional[str] = None
    dev_mode: Optional[bool] = None
    dev_max_items: Optional[int] = None
    github_repo: Optional[str] = None
    notify_type: Optional[str] = Field(None, description="通知类型: telegram/bark/webhook/空")
    notify_token: Optional[str] = Field(None, description="Telegram Bot Token 或 Bark Key")
    notify_webhook_url: Optional[str] = None
    rate_limit: Optional[int] = Field(None, description="下载限速(KB/s), 0=不限")


# ==================== 版本更新 ====================

class UpdateCheckResponse(BaseModel):
    current: str
    latest: str
    has_update: bool
    message: str
    release_url: str = ""
