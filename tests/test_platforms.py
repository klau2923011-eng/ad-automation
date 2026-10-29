import hashlib
import hmac
import json
from fastapi.testclient import TestClient
from ad_automation.app import create_app
from ad_automation.config import Settings

from ad_automation.platforms.mock import MockPlatform


def test_mock_upload_and_status_flow(tmp_path):
    platform = MockPlatform("secret")
    result = platform.upload_asset(str(tmp_path / "clip.mp4"), "asset-1")

    assert result.remote_id == "mock-asset-1"
    assert platform.get_asset_status(result.remote_id).status == "pending_review"


def test_mock_callback_signature_and_normalization():
    platform = MockPlatform("secret")
    payload = b'{"event_id":"evt-1","remote_id":"mock-a","status":"approved"}'
    signature = hmac.new(b"secret", payload, hashlib.sha256).hexdigest()

    assert platform.verify_callback(payload, {"x-signature": signature})
    event = platform.normalize_callback({"event_id": "evt-1", "remote_id": "mock-a", "status": "approved"}, {})
    assert event.status == "approved"


def test_spi_updates_binding_and_rejects_bad_signature(tmp_path, video_bytes):
    app = create_app(Settings(data_dir=tmp_path))
    with TestClient(app) as client:
        asset = client.post("/api/assets", files={"file": ("clip.mp4", video_bytes, "video/mp4")}).json()
        sync = client.post("/api/platforms/mock/sync", json={"assetId": asset["id"]})
        assert sync.status_code == 200
        binding = sync.json()
        body = json.dumps({"event_id": "evt-1", "remote_id": binding["remoteId"], "status": "approved"}, separators=(",", ":")).encode()
        signature = hmac.new(b"dev-secret", body, hashlib.sha256).hexdigest()
        good = client.post("/api/spi/mock", content=body, headers={"x-signature": signature})
        bad = client.post("/api/spi/mock", content=body, headers={"x-signature": "bad"})
    assert good.status_code == 200
    assert good.json()["status"] == "approved"
    assert bad.status_code == 401
