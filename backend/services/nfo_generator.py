"""
NFO 文件生成器
支持 movie.nfo（通用视频）和 tvshow.nfo + episode.nfo（追番）
"""
import os
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom.minidom import parseString
from typing import Optional


def _prettify(elem: Element) -> str:
    """格式化 XML 输出"""
    raw = tostring(elem, encoding="unicode")
    dom = parseString(raw)
    return dom.toprettyxml(indent="  ", encoding=None)


def generate_movie_nfo(
    title: str,
    plot: str = "",
    year: str = "",
    premiered: str = "",
    studio: str = "",
    director: str = "",
    tags: list[str] = None,
    video_url: str = "",
    video_id: str = "",
    platform: str = "",
    thumb_filename: str = "",
    fanart_filename: str = "",
    duration_seconds: int = 0,
) -> str:
    """
    生成 movie.nfo（电影模式，用于所有单品视频）
    包含发布者信息和原视频链接
    """
    movie = Element("movie")

    SubElement(movie, "title").text = title
    if plot:
        SubElement(movie, "plot").text = plot
        SubElement(movie, "outline").text = plot[:200]
    if year:
        SubElement(movie, "year").text = year
    if premiered:
        SubElement(movie, "premiered").text = premiered

    # 发布者信息
    if studio:
        SubElement(movie, "studio").text = studio
    if director:
        SubElement(movie, "director").text = director

    # 原视频链接
    if video_url:
        SubElement(movie, "website").text = video_url

    # 平台标识 ID
    if video_id and platform:
        uid = SubElement(movie, "uniqueid")
        uid.set("type", platform)
        uid.set("default", "true")
        uid.text = video_id

    # 标签
    if tags:
        for tag in tags:
            SubElement(movie, "tag").text = tag
    if platform:
        SubElement(movie, "tag").text = platform.capitalize()

    # 时长（分钟）
    if duration_seconds > 0:
        SubElement(movie, "runtime").text = str(duration_seconds // 60)

    # 缩略图
    if thumb_filename:
        thumb = SubElement(movie, "thumb")
        thumb.set("aspect", "poster")
        thumb.text = thumb_filename
    if fanart_filename:
        fanart = SubElement(movie, "fanart")
        SubElement(fanart, "thumb").text = fanart_filename

    return _prettify(movie)


def generate_tvshow_nfo(
    title: str,
    plot: str = "",
    year: str = "",
    studio: str = "",
    tags: list[str] = None,
    show_url: str = "",
    show_id: str = "",
    platform: str = "",
    poster_filename: str = "",
) -> str:
    """生成 tvshow.nfo（电视剧模式，用于追番）"""
    tvshow = Element("tvshow")

    SubElement(tvshow, "title").text = title
    if plot:
        SubElement(tvshow, "plot").text = plot
    if year:
        SubElement(tvshow, "year").text = year
    if studio:
        SubElement(tvshow, "studio").text = studio
    if show_url:
        SubElement(tvshow, "website").text = show_url
    if show_id and platform:
        uid = SubElement(tvshow, "uniqueid")
        uid.set("type", platform)
        uid.set("default", "true")
        uid.text = show_id
    if tags:
        for tag in tags:
            SubElement(tvshow, "tag").text = tag
    if poster_filename:
        thumb = SubElement(tvshow, "thumb")
        thumb.set("aspect", "poster")
        thumb.text = poster_filename

    return _prettify(tvshow)


def generate_episode_nfo(
    title: str,
    season: int = 1,
    episode: int = 1,
    plot: str = "",
    aired: str = "",
    director: str = "",
    video_url: str = "",
    video_id: str = "",
    platform: str = "",
    thumb_filename: str = "",
    duration_seconds: int = 0,
) -> str:
    """生成 episode.nfo（单集信息，用于追番）"""
    ep = Element("episodedetails")

    SubElement(ep, "title").text = title
    SubElement(ep, "season").text = str(season)
    SubElement(ep, "episode").text = str(episode)
    if plot:
        SubElement(ep, "plot").text = plot
    if aired:
        SubElement(ep, "aired").text = aired
    if director:
        SubElement(ep, "director").text = director
    if video_url:
        SubElement(ep, "website").text = video_url
    if video_id and platform:
        uid = SubElement(ep, "uniqueid")
        uid.set("type", platform)
        uid.text = video_id
    if duration_seconds > 0:
        SubElement(ep, "runtime").text = str(duration_seconds // 60)
    if thumb_filename:
        thumb = SubElement(ep, "thumb")
        thumb.text = thumb_filename

    return _prettify(ep)


def save_nfo(content: str, path: str):
    """保存 NFO 文件"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
