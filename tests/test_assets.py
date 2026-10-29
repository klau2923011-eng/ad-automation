from fastapi.testclient import TestClient

from ad_automation.app import create_app
from ad_automation.config import Settings


def test_uploads_video_and_marks_exact_duplicate(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    content = b"demo-video-bytes"

    with TestClient(app) as client:
        first = client.post(
            "/api/assets",
            files={"file": ("creative.mp4", content, "video/mp4")},
        )
        second = client.post(
            "/api/assets",
            files={"file": ("creative-copy.mp4", content, "video/mp4")},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["status"] == "ready"
    assert second.json()["status"] == "duplicate"
    assert first.json()["sha256"] == second.json()["sha256"]


def test_rejects_non_video_upload(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))

    with TestClient(app) as client:
        response = client.post(
            "/api/assets",
            files={"file": ("notes.txt", b"no", "text/plain")},
        )

    assert response.status_code == 400
