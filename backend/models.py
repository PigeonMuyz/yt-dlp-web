"""
数据库 ORM 模型
"""
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, Text, JSON, Enum as SAEnum,
    func, ForeignKey
)
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime
import enum


class Base(DeclarativeBase):
    pass


class Platform(str, enum.Enum):
    YOUTUBE = "youtube"
    BILIBILI = "bilibili"


class TaskStatus(str, enum.Enum):
    PENDING = "pending"
    DOWNLOADING = "downloading"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class SubType(str, enum.Enum):
    CHANNEL = "channel"           # YouTube 频道 / B站 UP主
    PLAYLIST = "playlist"         # YouTube 播放列表
    FAVORITES = "favorites"       # B站收藏夹
    BANGUMI = "bangumi"           # B站追番
    WATCH_LATER = "watch_later"   # B站稍后再看


class CodecStrategy(str, enum.Enum):
    SINGLE = "single"             # 只下首选编码
    DUAL = "dual"                 # 兼容 + 高质量
    ALL = "all"                   # 所有可用


class OrgMode(str, enum.Enum):
    BY_YEAR = "by_year"           # 频道名/2024/
    BY_PLAYLIST = "by_playlist"   # 频道名/播放列表名/
    FLAT = "flat"                 # 频道名/
    SEASON = "season"             # 番名/Season 01/


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_admin = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())


class AccountCookie(Base):
    """平台账号 Cookie 存储"""
    __tablename__ = "account_cookies"

    id = Column(Integer, primary_key=True)
    platform = Column(SAEnum(Platform), nullable=False)
    account_name = Column(String(200), default="")
    cookie_data = Column(Text, nullable=False)
    extra_data = Column(JSON, default=dict)  # token 等额外信息
    is_valid = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class Subscription(Base):
    """订阅源"""
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True)
    platform = Column(SAEnum(Platform), nullable=False)
    sub_type = Column(SAEnum(SubType), nullable=False)
    url = Column(String(500), nullable=False)
    name = Column(String(300), default="")
    thumbnail = Column(String(500), default="")
    description = Column(Text, default="")

    # 下载配置
    download_dir = Column(String(500), default="")
    codec_strategy = Column(SAEnum(CodecStrategy), default=CodecStrategy.DUAL)
    preferred_codec = Column(String(50), default="")  # vp9/av1/hevc
    max_resolution = Column(String(20), default="")    # 2160p/1080p/720p
    subtitle_langs = Column(String(200), default="zh-Hans,en,ja")
    org_mode = Column(SAEnum(OrgMode), default=OrgMode.BY_YEAR)

    # 调度
    check_interval = Column(Integer, default=3600)  # 秒
    enabled = Column(Boolean, default=True)
    last_checked = Column(DateTime, nullable=True)
    download_archive = Column(Text, default="")  # 已下载的视频 ID

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())


class DownloadTask(Base):
    """下载任务"""
    __tablename__ = "download_tasks"

    id = Column(Integer, primary_key=True)
    platform = Column(SAEnum(Platform), nullable=False)
    video_url = Column(String(500), nullable=False)
    video_id = Column(String(100), default="")
    title = Column(String(500), default="")
    thumbnail = Column(String(500), default="")
    channel_name = Column(String(300), default="")
    channel_url = Column(String(500), default="")
    upload_date = Column(String(20), default="")
    duration = Column(Integer, default=0)
    description = Column(Text, default="")

    # 下载配置
    format_id = Column(String(100), default="")
    codec = Column(String(50), default="")
    resolution = Column(String(20), default="")
    file_size = Column(Integer, default=0)  # bytes
    output_path = Column(String(1000), default="")

    # 状态
    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    progress = Column(Integer, default=0)  # 0-100
    speed = Column(String(50), default="")
    eta = Column(String(50), default="")
    error_msg = Column(Text, default="")

    # 关联
    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    subscription = relationship("Subscription", backref="tasks")
    series_episode_id = Column(Integer, ForeignKey("series_episodes.id"), nullable=True)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    completed_at = Column(DateTime, nullable=True)


class DownloadHistory(Base):
    """下载历史（持久记录）"""
    __tablename__ = "download_history"

    id = Column(Integer, primary_key=True)
    platform = Column(SAEnum(Platform), nullable=False)
    video_id = Column(String(100), nullable=False, index=True)
    video_url = Column(String(500), default="")
    title = Column(String(500), default="")
    channel_name = Column(String(300), default="")
    codec = Column(String(50), default="")
    resolution = Column(String(20), default="")
    file_path = Column(String(1000), default="")
    file_size = Column(Integer, default=0)
    nfo_path = Column(String(1000), default="")

    subscription_id = Column(Integer, ForeignKey("subscriptions.id"), nullable=True)
    downloaded_at = Column(DateTime, default=func.now())


class SeriesStatus(str, enum.Enum):
    DRAFT = "draft"               # 编辑中
    DOWNLOADING = "downloading"   # 下载中
    COMPLETED = "completed"       # 全部完成
    PARTIAL = "partial"           # 部分完成


class ManualSeries(Base):
    """手动剧集"""
    __tablename__ = "manual_series"

    id = Column(Integer, primary_key=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    platform = Column(SAEnum(Platform), default=Platform.BILIBILI)
    category = Column(String(100), default="剧集")  # 存储目录分类
    season = Column(Integer, default=1)
    poster_url = Column(String(500), default="")
    status = Column(SAEnum(SeriesStatus), default=SeriesStatus.DRAFT)

    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())

    episodes = relationship("SeriesEpisode", backref="series", order_by="SeriesEpisode.episode_number", cascade="all, delete-orphan")


class SeriesEpisode(Base):
    """剧集中的单集"""
    __tablename__ = "series_episodes"

    id = Column(Integer, primary_key=True)
    series_id = Column(Integer, ForeignKey("manual_series.id"), nullable=False)
    episode_number = Column(Integer, nullable=False)
    video_url = Column(String(500), nullable=False)
    title = Column(String(500), default="")
    thumbnail = Column(String(500), default="")
    duration = Column(Integer, default=0)

    status = Column(SAEnum(TaskStatus), default=TaskStatus.PENDING)
    download_task_id = Column(Integer, ForeignKey("download_tasks.id"), nullable=True)

    created_at = Column(DateTime, default=func.now())
