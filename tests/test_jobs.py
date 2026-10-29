import pytest
from fastapi.testclient import TestClient

from ad_automation.models import ProcessingJob
from ad_automation.services.jobs import InvalidJobTransition, retry_failed_job, transition_job
from ad_automation.app import create_app
from ad_automation.config import Settings


def test_job_can_move_from_pending_to_running_to_succeeded():
    job = ProcessingJob(id="job-1", asset_id="asset-1", status="pending", attempts=0, max_attempts=3)

    transition_job(job, "running")
    transition_job(job, "succeeded")

    assert job.status == "succeeded"
    assert job.attempts == 1


def test_job_rejects_skipping_running_state():
    job = ProcessingJob(id="job-1", asset_id="asset-1", status="pending", attempts=0, max_attempts=3)

    with pytest.raises(InvalidJobTransition):
        transition_job(job, "succeeded")


def test_retry_moves_failed_job_back_to_pending_until_limit():
    job = ProcessingJob(id="job-1", asset_id="asset-1", status="failed", attempts=1, max_attempts=3)

    retry_failed_job(job)

    assert job.status == "pending"


def test_retry_exhaustion_moves_job_to_dead_letter():
    job = ProcessingJob(id="job-1", asset_id="asset-1", status="failed", attempts=3, max_attempts=3)

    retry_failed_job(job)

    assert job.status == "dead_letter"


def test_create_job_for_uploaded_asset(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("clip.mp4", _valid_video(tmp_path), "video/mp4")}).json()
        response = client.post("/api/jobs", json={"assetId": asset["id"], "steps": []})
    assert response.status_code == 200
    assert response.json()["status"] in {"pending", "succeeded"}


def test_trim_job_produces_a_new_video_asset(tmp_path):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("clip.mp4", _valid_video(tmp_path), "video/mp4")}).json()
        created = client.post(
            "/api/jobs",
            json={"assetId": asset["id"], "steps": [{"kind": "trim", "params": {"start": 0, "end": 0.15}}]},
        )
        job_id = created.json()["id"]
        detail = client.get(f"/api/jobs/{job_id}")

    assert detail.status_code == 200
    assert detail.json()["status"] == "succeeded"
    assert detail.json()["outputAssetId"]
    assert detail.json()["steps"][0]["status"] == "succeeded"


def _valid_video(tmp_path):
    import subprocess
    ffmpeg = Settings(data_dir=tmp_path).ffmpeg_path
    output = tmp_path / "job.mp4"
    subprocess.run([ffmpeg, "-f", "lavfi", "-i", "color=c=red:s=32x32:d=0.2", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-y", str(output)], check=True, capture_output=True)
    return output.read_bytes()
