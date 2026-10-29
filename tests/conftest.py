import subprocess

import pytest

from ad_automation.config import Settings


@pytest.fixture
def video_bytes(tmp_path):
    ffmpeg = Settings(data_dir=tmp_path).ffmpeg_path
    if not ffmpeg:
        pytest.skip("FFmpeg is required to generate a valid test video")
    output = tmp_path / "fixture.mp4"
    subprocess.run([ffmpeg, "-f", "lavfi", "-i", "testsrc2=size=64x48:rate=10:duration=0.4", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output)], check=True, capture_output=True)
    return output.read_bytes()
