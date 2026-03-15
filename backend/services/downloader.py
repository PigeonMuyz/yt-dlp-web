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
    """
    codec_patterns = {
        "vp9": "vp9",
        "av1": "av01",
        "h264": "avc1",
        "hevc": "hev1",
    }
    vcodec_filter = codec_patterns.get(codec.lower(), codec.lower())

    height_limit = ""
    if max_resolution:
        h = max_resolution.replace("p", "").replace("k", "")
        if h == "4" or h == "2160":
            height_limit = "[height<=2160]"
        elif h == "1080":
            height_limit = "[height<=1080]"
        elif h == "720":
            height_limit = "[height<=720]"

    # 带 codec 过滤的首选 + 不限 codec 但限分辨率的次选 + 最终兜底
    primary = f"bestvideo[vcodec^={vcodec_filter}]{height_limit}+bestaudio"
    secondary = f"bestvideo{height_limit}+bestaudio" if height_limit else ""
    fallback = "bestvideo+bestaudio/best"
    parts = [p for p in [primary, secondary, fallback] if p]
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

    # 输出路径
    output_dir = os.path.dirname(output_path)
    output_name = os.path.basename(output_path)
    base_name = os.path.splitext(output_name)[0]

    opts.update({
        "format": format_string,
        "outtmpl": os.path.join(output_dir, f"{base_name}.%(ext)s"),
        "merge_output_format": merge_format or None,
        # 字幕
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": subtitle_langs.split(",") if subtitle_langs else [],
        "subtitlesformat": "vtt/srt/best",
        # 缩略图
        "writethumbnail": True,
        # 元数据
        "writedescription": True,
        "writeinfojson": True,
    })

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
