"""
yt-dlp 下载器封装
"""
import asyncio
import json
import os
import tempfile
from typing import Optional, Callable
from concurrent.futures import ThreadPoolExecutor


# yt-dlp 在线程池中运行（非 async）
_executor = ThreadPoolExecutor(max_workers=4)


def _get_base_opts(
    proxy: str = "",
    cookies_file: str = "",
) -> dict:
    """基础 yt-dlp 选项"""
    opts = {
        "quiet": True,
        "no_warnings": True,
        "noprogress": True,
        "ignoreerrors": False,
        "retries": 5,
        "fragment_retries": 5,
    }
    if proxy:
        opts["proxy"] = proxy
    if cookies_file and os.path.exists(cookies_file):
        opts["cookiefile"] = cookies_file
    return opts


def extract_info(url: str, proxy: str = "", cookies_file: str = "") -> dict:
    """
    获取视频/频道/播放列表信息
    返回 yt-dlp info_dict
    """
    import yt_dlp

    opts = _get_base_opts(proxy, cookies_file)
    opts["extract_flat"] = False

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def extract_flat(url: str, proxy: str = "", cookies_file: str = "") -> dict:
    """
    获取频道/播放列表中的视频列表（不下载详情）
    """
    import yt_dlp

    opts = _get_base_opts(proxy, cookies_file)
    opts["extract_flat"] = True
    opts["playlistend"] = None

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=False)
        return ydl.sanitize_info(info)


def get_available_formats(url: str, proxy: str = "", cookies_file: str = "") -> list:
    """
    获取可用的视频格式列表
    返回: [{format_id, ext, resolution, vcodec, acodec, filesize, ...}]
    """
    info = extract_info(url, proxy, cookies_file)
    formats = info.get("formats", [])

    result = []
    for f in formats:
        vcodec = f.get("vcodec", "none")
        if vcodec == "none":
            continue  # 跳过纯音频

        result.append({
            "format_id": f.get("format_id", ""),
            "ext": f.get("ext", ""),
            "resolution": f.get("resolution", ""),
            "width": f.get("width", 0),
            "height": f.get("height", 0),
            "fps": f.get("fps", 0),
            "vcodec": vcodec,
            "acodec": f.get("acodec", "none"),
            "filesize": f.get("filesize", 0) or f.get("filesize_approx", 0) or 0,
            "tbr": f.get("tbr", 0),
            "format_note": f.get("format_note", ""),
        })

    return sorted(result, key=lambda x: (x["height"], x["tbr"]), reverse=True)


def filter_formats_by_codec(formats: list, codec: str) -> list:
    """按编码过滤格式"""
    codec_patterns = {
        "vp9": ["vp9", "vp09"],
        "av1": ["av1", "av01"],
        "h264": ["avc1", "h264", "avc"],
        "hevc": ["hevc", "h265", "hev1", "hvc1"],
    }
    patterns = codec_patterns.get(codec.lower(), [codec.lower()])
    return [f for f in formats if any(p in f["vcodec"].lower() for p in patterns)]


def build_format_string(codec: str, max_resolution: str = "") -> str:
    """
    构建 yt-dlp format 选择字符串
    使用 vcodec*= 包含匹配，兜底链保证不会全部失败
    """
    # codec 名 → yt-dlp vcodec 过滤关键字
    codec_patterns = {
        "vp9": "vp0?9",     # 匹配 vp9, vp09
        "av1": "av0?1",     # 匹配 av1, av01
        "h264": "avc",      # 匹配 avc1 等
        "hevc": "hev|hevc", # 匹配 hev1, hevc
    }
    vcodec_re = codec_patterns.get(codec.lower(), codec.lower())

    height_limit = ""
    if max_resolution:
        h = max_resolution.replace("p", "").replace("k", "")
        if h == "4" or h == "2160":
            height_limit = "[height<=2160]"
        elif h == "1080":
            height_limit = "[height<=1080]"
        elif h == "720":
            height_limit = "[height<=720]"

    # 优先级：指定编码+限分辨率 → 指定编码不限 → 不限编码限分辨率 → 全自动
    primary = f"bestvideo[vcodec~='{vcodec_re}']{height_limit}+bestaudio/best"
    no_height = f"bestvideo[vcodec~='{vcodec_re}']+bestaudio/best" if height_limit else ""
    secondary = f"bestvideo{height_limit}+bestaudio/best" if height_limit else ""
    fallback = "bestvideo+bestaudio/best"
    parts = [p for p in [primary, no_height, secondary, fallback] if p]
    return "/".join(parts)


def download_video(
    url: str,
    output_path: str,
    format_string: str = "bestvideo+bestaudio/best",
    subtitle_langs: str = "zh-Hans,en,ja",
    proxy: str = "",
    cookies_file: str = "",
    progress_callback: Optional[Callable] = None,
    merge_format: str = "",
) -> dict:
    """
    下载视频
    返回下载结果信息
    """
    import yt_dlp

    opts = _get_base_opts(proxy, cookies_file)

    # 限速
    from config import settings as _settings
    if _settings.rate_limit > 0:
        opts["ratelimit"] = _settings.rate_limit * 1024  # KB/s → B/s

    # 输出路径
    output_dir = os.path.dirname(output_path)
    output_name = os.path.basename(output_path)
    base_name = os.path.splitext(output_name)[0]

    opts.update({
        "format": format_string,
        "outtmpl": os.path.join(output_dir, f"{base_name}.%(ext)s"),
        "merge_output_format": merge_format or None,
        # 字幕 — 忽略字幕下载错误（429 限流等）
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": subtitle_langs.split(",") if subtitle_langs else [],
        "subtitlesformat": "vtt/srt/best",
        "ignore_no_formats_error": True,
        # 缩略图
        "writethumbnail": True,
        # 元数据
        "writedescription": True,
        "writeinfojson": True,
    })
    # 字幕下载失败不应中断整个任务
    opts["ignoreerrors"] = "only_download"  # 只忽略非核心下载错误

    # 进度回调
    if progress_callback:
        def hook(d):
            if d["status"] == "downloading":
                progress_callback({
                    "status": "downloading",
                    "progress": d.get("_percent_str", "0%").strip(),
                    "speed": d.get("_speed_str", ""),
                    "eta": d.get("_eta_str", ""),
                    "downloaded": d.get("downloaded_bytes", 0),
                    "total": d.get("total_bytes", 0) or d.get("total_bytes_estimate", 0),
                })
            elif d["status"] == "finished":
                progress_callback({
                    "status": "finished",
                    "progress": "100%",
                    "filename": d.get("filename", ""),
                })

        opts["progress_hooks"] = [hook]

    os.makedirs(output_dir, exist_ok=True)

    with yt_dlp.YoutubeDL(opts) as ydl:
        try:
            info = ydl.extract_info(url, download=True)
        except yt_dlp.utils.DownloadError as e:
            if "Requested format is not available" in str(e) and format_string != "bestvideo+bestaudio/best":
                # 指定编码不可用 → 回退到最佳格式重试
                opts["format"] = "bestvideo+bestaudio/best"
                with yt_dlp.YoutubeDL(opts) as ydl2:
                    info = ydl2.extract_info(url, download=True)
            else:
                raise

        # yt-dlp 有时不抛异常而是返回 None（如 ignoreerrors 生效时）
        if info is None and format_string != "bestvideo+bestaudio/best":
            opts["format"] = "bestvideo+bestaudio/best"
            with yt_dlp.YoutubeDL(opts) as ydl2:
                info = ydl2.extract_info(url, download=True)

        if info is None:
            raise RuntimeError(f"下载失败: {url}")

        return ydl.sanitize_info(info) if hasattr(ydl, 'sanitize_info') else info


async def async_extract_info(url: str, **kwargs) -> dict:
    """异步获取视频信息"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: extract_info(url, **kwargs))


async def async_download(url: str, **kwargs) -> dict:
    """异步下载"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(_executor, lambda: download_video(url, **kwargs))
