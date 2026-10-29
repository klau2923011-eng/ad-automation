from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path


def probe_video(path: Path) -> dict | None:
    ffprobe = shutil.which("ffprobe")
    if ffprobe is None:
        return None
    result = subprocess.run(
        [ffprobe, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    payload = json.loads(result.stdout)
    video = next((stream for stream in payload.get("streams", []) if stream.get("codec_type") == "video"), None)
    if video is None:
        raise ValueError("文件中没有可识别的视频流")
    return {
        "duration_seconds": float(payload.get("format", {}).get("duration", 0)) or None,
        "width": int(video["width"]) if video.get("width") else None,
        "height": int(video["height"]) if video.get("height") else None,
    }
