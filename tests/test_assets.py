import subprocess

import pytest
from fastapi.testclient import TestClient

from ad_automation.app import create_app
from ad_automation.config import Settings
from ad_automation.media.fingerprint import perceptual_fingerprint


def _video_bytes(tmp_path):
    ffmpeg = Settings(data_dir=tmp_path).ffmpeg_path
    if not ffmpeg:
        pytest.skip("FFmpeg is required to generate a valid test video")
    output = tmp_path / "fixture.mp4"
    subprocess.run(
        [ffmpeg, "-f", "lavfi", "-i", "color=c=blue:s=32x32:d=0.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output)],
        check=True,
        capture_output=True,
    )
    return output.read_bytes()


def test_uploads_video_and_marks_exact_duplicate(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    content = _video_bytes(tmp_path)

    with TestClient(app) as client:
        first = client.post("/api/assets", files={"file": ("creative.mp4", content, "video/mp4")})
        second = client.post("/api/assets", files={"file": ("creative-copy.mp4", content, "video/mp4")})

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "ready"
    assert second.json()["status"] == "duplicate"
    assert first.json()["sha256"] == second.json()["sha256"]
    assert len(first.json()["perceptualHash"]) == 16
    assert first.json()["perceptualHash"] == second.json()["perceptualHash"]
    assert first.json()["probeStatus"] == "available"
    assert first.json()["width"] == 32
    assert first.json()["height"] == 32
    assert first.json()["durationSeconds"] > 0


def test_rejects_non_video_upload(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        response = client.post("/api/assets", files={"file": ("notes.txt", b"no", "text/plain")})
    assert response.status_code == 400


def test_rejects_invalid_video_bytes(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        response = client.post(
            "/api/assets",
            files={"file": ("fake.mp4", b"not an mp4", "video/mp4")},
        )
    assert response.status_code == 400


def test_perceptual_fingerprint_is_stable_for_same_video(tmp_path):
    video = tmp_path / "clip.mp4"
    video.write_bytes(_video_bytes(tmp_path))

    first = perceptual_fingerprint(video)
    second = perceptual_fingerprint(video)

    assert len(first) == 16
    assert first == second
