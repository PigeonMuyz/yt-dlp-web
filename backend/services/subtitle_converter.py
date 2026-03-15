"""
字幕格式转换器
将 VTT/ASS/SSA 等格式统一转换为 SRT
"""
import os
import re
import glob


def vtt_to_srt(vtt_content: str) -> str:
    """将 WebVTT 内容转换为 SRT 格式"""
    lines = vtt_content.strip().split("\n")
    srt_blocks = []
    counter = 0
    i = 0

    # 跳过 VTT 头部
    while i < len(lines):
        if lines[i].strip() == "WEBVTT" or lines[i].strip().startswith("WEBVTT"):
            i += 1
            # 跳过头部元数据
            while i < len(lines) and lines[i].strip():
                i += 1
            break
        i += 1

    current_time = ""
    current_text = []

    while i < len(lines):
        line = lines[i].strip()

        # 时间行
        if "-->" in line:
            # 保存之前的块
            if current_time and current_text:
                counter += 1
                text = "\n".join(current_text)
                # 去重（VTT 经常有重复行）
                text = _dedup_text(text)
                if text.strip():
                    srt_blocks.append(f"{counter}\n{current_time}\n{text}")

            # 转换时间格式 00:00:01.000 --> 00:00:04.000
            current_time = line.replace(".", ",")
            # 移除位置标记
            current_time = re.sub(r'\s+align:.*$', '', current_time)
            current_time = re.sub(r'\s+position:.*$', '', current_time)
            current_time = re.sub(r'\s+line:.*$', '', current_time)
            current_text = []
        elif line and not line.isdigit():
            # 文本行，去除 HTML 标签
            cleaned = re.sub(r'<[^>]+>', '', line)
            if cleaned.strip():
                current_text.append(cleaned)
        elif not line and current_text:
            # 空行 = 块结束
            pass

        i += 1

    # 最后一个块
    if current_time and current_text:
        counter += 1
        text = "\n".join(current_text)
        text = _dedup_text(text)
        if text.strip():
            srt_blocks.append(f"{counter}\n{current_time}\n{text}")

    return "\n\n".join(srt_blocks) + "\n"


def _dedup_text(text: str) -> str:
    """去除重复的字幕行"""
    lines = text.split("\n")
    seen = []
    for line in lines:
        if line.strip() and line.strip() not in seen:
            seen.append(line.strip())
    return "\n".join(seen)


def convert_subtitle_file(input_path: str, output_path: str = None) -> str:
    """
    将字幕文件转换为 SRT 格式
    返回输出文件路径
    """
    if output_path is None:
        base = os.path.splitext(input_path)[0]
        output_path = base + ".srt"

    ext = os.path.splitext(input_path)[1].lower()

    with open(input_path, "r", encoding="utf-8") as f:
        content = f.read()

    if ext == ".vtt":
        srt_content = vtt_to_srt(content)
    elif ext == ".srt":
        # 已经是 SRT，直接复制
        srt_content = content
    else:
        # 其他格式尝试当 VTT 处理
        srt_content = vtt_to_srt(content)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(srt_content)

    return output_path


def convert_all_subtitles(directory: str, delete_original: bool = True):
    """
    将目录下所有非 SRT 字幕转换为 SRT
    """
    converted = []
    for ext in ["*.vtt", "*.ass", "*.ssa"]:
        for filepath in glob.glob(os.path.join(directory, ext)):
            srt_path = convert_subtitle_file(filepath)
            converted.append(srt_path)
            if delete_original and filepath != srt_path:
                os.remove(filepath)
    return converted
