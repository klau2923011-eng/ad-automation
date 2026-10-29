import json

from fastapi.testclient import TestClient

from ad_automation.app import create_app
from ad_automation.config import Settings


def test_failed_job_creates_acknowledgeable_alert(tmp_path, video_bytes):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("clip.mp4", video_bytes, "video/mp4")}).json()
        job = client.post("/api/jobs", json={"assetId": asset["id"], "steps": [{"kind": "bad-step", "params": {}}]}).json()
        details = client.get(f"/api/jobs/{job['id']}").json()
        alerts = client.get("/api/alerts").json()
        ack = client.post(f"/api/alerts/{alerts[0]['id']}/ack")

    assert details["status"] == "failed"
    assert alerts[0]["source"] == "job"
    assert ack.status_code == 200
    assert ack.json()["status"] == "acknowledged"


def test_invalid_spi_signature_creates_alert(tmp_path, video_bytes):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("clip.mp4", video_bytes, "video/mp4")}).json()
        binding = client.post("/api/platforms/mock/sync", json={"assetId": asset["id"]}).json()
        body = json.dumps({"event_id": "bad-1", "remote_id": binding["remoteId"], "status": "approved"})
        response = client.post("/api/spi/mock", content=body, headers={"x-signature": "invalid"})
        alerts = client.get("/api/alerts").json()

    assert response.status_code == 401
    assert any(alert["source"] == "spi" for alert in alerts)
