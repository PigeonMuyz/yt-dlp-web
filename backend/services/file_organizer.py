"""
文件整理器
处理下载后的文件命名、目录组织、多编码命名
"""
import os
import re
from typing import Optional


def sanitize_filename(name: str) -> str:
    """清理文件名中的非法字符"""
    # 替换 Windows/Linux 不允许的字符
    name = re.sub(r'[<>:"/\\|?*]', '', name)
    name = re.sub(r'\s+', ' ', name).strip()
    name = name.rstrip('.')
    return name[:200]  # 限制长度


def get_codec_label(codec: str) -> str:
    """获取编码标签用于文件名"""
    codec_map = {
        "vp9": "VP9",
        "vp09": "VP9",
        "av1": "AV1",
        "av01": "AV1",
        "avc1": "H264",
        "h264": "H264",
        "avc": "H264",
        "hevc": "HEVC",
        "h265": "HEVC",
        "hev1": "HEVC",
        "hvc1": "HEVC",
    }
    return codec_map.get(codec.lower(), codec.upper())


def build_movie_path(
    base_dir: str,
    category: str,
    title: str,
    year: str,
    codec: str = "",
    ext: str = ".mp4",
) -> dict:
    """
    构建电影模式的文件路径
    返回: {video, nfo, thumb, subtitle_dir}

    示例: Emby/YouTube/视频标题 (2024)/视频标题 (2024) - [VP9].webm
    """
    safe_title = sanitize_filename(title)
    display_name = safe_title
    codec_label = get_codec_label(codec) if codec else ""

    folder = os.path.join(base_dir, category, display_name)

    if codec_label:
        filename_base = f"{display_name} - [{codec_label}]"
    else:
        filename_base = display_name

    return {
        "folder": folder,
        "video": os.path.join(folder, f"{filename_base}{ext}"),
        "nfo": os.path.join(folder, f"{filename_base}.nfo"),
        "thumb": os.path.join(folder, f"{filename_base}-thumb.jpg"),
        "subtitle_dir": folder,
        "filename_base": filename_base,
    }


def build_tvshow_path(
    base_dir: str,
    category: str,
    show_title: str,
    year: str,
    season: int,
    episode: int,
    episode_title: str = "",
    codec: str = "",
    ext: str = ".mp4",
) -> dict:
    """
    构建电视剧模式（追番）的文件路径
    示例: Emby/动漫/番名 (2024)/Season 01/番名 - S01E01 - 标题.mp4
    """
    safe_show = sanitize_filename(show_title)
    safe_ep_title = sanitize_filename(episode_title) if episode_title else ""
    display_name = f"{safe_show} ({year})" if year else safe_show
    codec_label = get_codec_label(codec) if codec else ""

    show_dir = os.path.join(base_dir, category, display_name)
    season_dir = os.path.join(show_dir, f"Season {season:02d}")

    ep_name = f"{safe_show} - S{season:02d}E{episode:02d}"
    if safe_ep_title:
        ep_name += f" - {safe_ep_title}"
    if codec_label:
        ep_name += f" - [{codec_label}]"

    return {
        "show_dir": show_dir,
        "season_dir": season_dir,
        "video": os.path.join(season_dir, f"{ep_name}{ext}"),
        "nfo": os.path.join(season_dir, f"{ep_name}.nfo"),
        "thumb": os.path.join(season_dir, f"{ep_name}-thumb.jpg"),
        "tvshow_nfo": os.path.join(show_dir, "tvshow.nfo"),
        "poster": os.path.join(show_dir, "poster.jpg"),
        "subtitle_dir": season_dir,
        "filename_base": ep_name,
    }


def build_channel_path(
    base_dir: str,
    category: str,
    channel_name: str,
    title: str,
    year: str,
    org_mode: str = "by_year",
    playlist_name: str = "",
    codec: str = "",
    ext: str = ".mp4",
) -> dict:
    """
    构建频道订阅的文件路径（电影模式存储，按组织模式分子目录）
    """
    safe_channel = sanitize_filename(channel_name)
    safe_title = sanitize_filename(title)
    codec_label = get_codec_label(codec) if codec else ""

    display_name = safe_title

    if codec_label:
        filename_base = f"{display_name} - [{codec_label}]"
    else:
        filename_base = display_name

    # 根据组织模式确定子目录
    if org_mode == "by_year":
        item_dir = os.path.join(base_dir, category, display_name)
    elif org_mode == "by_playlist":
        safe_playlist = sanitize_filename(playlist_name or "未分类")
        item_dir = os.path.join(base_dir, category, safe_playlist, display_name)
    elif org_mode == "flat":
        item_dir = os.path.join(base_dir, category, display_name)
    else:
        item_dir = os.path.join(base_dir, category, display_name)

    return {
        "folder": item_dir,
        "video": os.path.join(item_dir, f"{filename_base}{ext}"),
        "nfo": os.path.join(item_dir, f"{filename_base}.nfo"),
        "thumb": os.path.join(item_dir, f"{filename_base}-thumb.jpg"),
        "subtitle_dir": item_dir,
        "filename_base": filename_base,
    }


def ensure_dirs(paths: dict):
    """确保路径中的目录都存在"""
    for key, path in paths.items():
        if key.endswith("_dir"):
            os.makedirs(path, exist_ok=True)
        elif path and os.path.dirname(path):
            os.makedirs(os.path.dirname(path), exist_ok=True)
