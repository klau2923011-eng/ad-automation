from __future__ import annotations

import hashlib
import hmac
import os
import json
from typing import Mapping

from ad_automation.platforms.base import CallbackEvent, RemoteAssetStatus, UploadResult


class MockPlatform:
    def __init__(self, secret: str | None = None):
        self.secret = (secret or os.getenv("AD_AUTOMATION_SPI_SECRET", "dev-secret")).encode()
        self.statuses: dict[str, str] = {}

    def upload_asset(self, asset_path: str, asset_id: str) -> UploadResult:
        remote_id = f"mock-{asset_id}"
        self.statuses[remote_id] = "pending_review"
        return UploadResult(remote_id, "pending_review", {"id": remote_id, "asset_id": asset_id})

    def get_asset_status(self, remote_id: str) -> RemoteAssetStatus:
        return RemoteAssetStatus(remote_id, self.statuses.get(remote_id, "unknown"), {"id": remote_id})

    def verify_callback(self, payload: bytes, headers: Mapping[str, str]) -> bool:
        provided = headers.get("x-signature", "")
        expected = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        return hmac.compare_digest(provided, expected)

    def normalize_callback(self, payload: dict, headers: Mapping[str, str]) -> CallbackEvent:
        return CallbackEvent(str(payload["event_id"]), str(payload["remote_id"]), str(payload["status"]), payload)

    def sign_callback(self, body: bytes) -> str:
        return hmac.new(self.secret, body, hashlib.sha256).hexdigest()
