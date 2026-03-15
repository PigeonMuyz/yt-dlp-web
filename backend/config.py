"""
yt-dlp Web 配置管理
支持首次启动初始化和环境变量配置
"""
from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import json
import os

CONFIG_FILE = os.environ.get("CONFIG_FILE", "/data/config.json")


class Settings(BaseSettings):
    # 应用
    app_name: str = "yt-dlp Web"
    app_port: int = 8686
    secret_key: str = "change-me-on-first-run"
    debug: bool = False

    # PostgreSQL
    database_url: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "ytdlp_web"
    db_user: str = "ytdlp"
    db_password: str = ""

    # Redis
    redis_url: str = ""
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "urn:ietf:wg:oauth:2.0:oob"

    # Emby
    emby_url: str = ""
    emby_api_key: str = ""

    # TMDB
    tmdb_api_key: str = ""

    # 下载
    download_dir: str = "/media"
    max_concurrent_downloads: int = 3
    proxy: str = ""
    default_resolution: str = "1080p"

    # 下载目录分类
    dir_videos: str = "单品"        # 单个视频，走电影 NFO
    dir_series: str = "剧集"        # 连续追番/剧集，走电视剧 NFO
    dir_collections: str = "合集"   # 合集/播放列表

    # yt-dlp Cookie 文件
    youtube_cookies_file: str = ""
    bilibili_cookies_file: str = ""

    # 开发者选项
    dev_mode: bool = False
    dev_max_items: int = 5  # 开发模式下订阅最多下载几个视频

    class Config:
        env_prefix = "YTDLP_"
        env_file = ".env"

    @property
    def pg_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"postgresql+asyncpg://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"

    @property
    def redis_dsn(self) -> str:
        if self.redis_url:
            return self.redis_url
        auth = f":{self.redis_password}@" if self.redis_password else ""
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"

    def is_initialized(self) -> bool:
        """检查是否已完成初始化配置"""
        return bool(self.db_password) and os.path.exists(CONFIG_FILE)

    def save_to_file(self):
        """保存配置到文件"""
        data = {
            "database_url": self.database_url,
            "db_host": self.db_host,
            "db_port": self.db_port,
            "db_name": self.db_name,
            "db_user": self.db_user,
            "db_password": self.db_password,
            "redis_url": self.redis_url,
            "redis_host": self.redis_host,
            "redis_port": self.redis_port,
            "redis_db": self.redis_db,
            "redis_password": self.redis_password,
            "google_client_id": self.google_client_id,
            "google_client_secret": self.google_client_secret,
            "emby_url": self.emby_url,
            "emby_api_key": self.emby_api_key,
            "tmdb_api_key": self.tmdb_api_key,
            "download_dir": self.download_dir,
            "max_concurrent_downloads": self.max_concurrent_downloads,
            "proxy": self.proxy,
            "default_resolution": self.default_resolution,
            "dir_videos": self.dir_videos,
            "dir_series": self.dir_series,
            "dir_collections": self.dir_collections,
            "youtube_cookies_file": self.youtube_cookies_file,
            "bilibili_cookies_file": self.bilibili_cookies_file,
            "dev_mode": self.dev_mode,
            "dev_max_items": self.dev_max_items,
            "secret_key": self.secret_key,
        }
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls) -> "Settings":
        """从文件和环境变量加载配置"""
        settings = cls()
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE) as f:
                data = json.load(f)
            for key, value in data.items():
                if hasattr(settings, key) and value:
                    setattr(settings, key, value)
        return settings


settings = Settings.load()
