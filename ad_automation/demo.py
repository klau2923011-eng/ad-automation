from __future__ import annotations

import argparse
import os
import subprocess
import time
import webbrowser
from pathlib import Path

from ad_automation.config import Settings


def create_demo_video(settings: Settings) -> Path:
    """Create a synthetic portrait video; it never uses or uploads user media."""
    ffmpeg = settings.ffmpeg_path
    if not ffmpeg:
        raise RuntimeError("未找到 FFmpeg，请先安装：winget install --id Gyan.FFmpeg.Shared")
    demo_dir = settings.data_dir / "demo"
    demo_dir.mkdir(parents=True, exist_ok=True)
    output = demo_dir / "demo-portrait.mp4"
    if output.is_file():
        return output
    subprocess.run(
        [
            ffmpeg,
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc2=size=720x1280:rate=24:duration=2",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:sample_rate=44100:duration=2",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(output),
        ],
        check=True,
        capture_output=True,
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(description="启动广告素材自动化本地演示")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    settings = Settings.from_env()
    video = create_demo_video(settings)
    print(f"演示视频已生成：{video}")
    import uvicorn

    url = f"http://{args.host}:{args.port}"
    if not args.no_browser:
        time.sleep(1)
        webbrowser.open(url)
    uvicorn.run("ad_automation.app:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()
