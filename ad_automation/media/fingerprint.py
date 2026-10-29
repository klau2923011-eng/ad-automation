from __future__ import annotations

import hashlib
import subprocess
from ad_automation.config import find_media_binary
from pathlib import Path


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def perceptual_fingerprint(path: Path) -> str:
    """使用视频首帧 8x8 灰度 aHash 生成可比较的感知指纹。"""
    ffmpeg = find_media_binary("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("未找到 ffmpeg，无法计算感知指纹")
    result = subprocess.run(
        [ffmpeg, "-v", "error", "-i", str(path), "-frames:v", "1", "-vf", "scale=8:8,format=gray", "-f", "rawvideo", "pipe:1"],
        check=True,
        capture_output=True,
        timeout=30,
    )
    pixels = result.stdout
    if len(pixels) != 64:
        raise ValueError("无法从视频提取首帧")
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if value >= average else "0" for value in pixels)
    return f"{int(bits, 2):016x}"
