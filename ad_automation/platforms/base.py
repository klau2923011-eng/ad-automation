from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Protocol


@dataclass(frozen=True)
class UploadResult:
    remote_id: str
    status: str
    raw: dict


@dataclass(frozen=True)
class RemoteAssetStatus:
    remote_id: str
    status: str
    raw: dict


@dataclass(frozen=True)
class CallbackEvent:
    external_event_id: str
    remote_id: str
    status: str
    raw: dict


class PlatformAdapter(Protocol):
    def upload_asset(self, asset_path: str, asset_id: str) -> UploadResult: ...
    def get_asset_status(self, remote_id: str) -> RemoteAssetStatus: ...
    def verify_callback(self, payload: bytes, headers: Mapping[str, str]) -> bool: ...
    def normalize_callback(self, payload: dict, headers: Mapping[str, str]) -> CallbackEvent: ...
