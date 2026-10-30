from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import Asset, PlatformBinding
from ad_automation.platforms.mock import MockPlatform
from ad_automation.services.sync import apply_callback

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.post("/{platform}/sync")
def sync_asset(request: Request, platform: str, payload: dict) -> dict:
    if platform != "mock":
        raise HTTPException(400, "MVP 仅支持 mock 平台")
    with Session(request.app.state.database_engine) as session:
        asset = session.get(Asset, payload.get("assetId"))
        if asset is None:
            raise HTTPException(404, "素材不存在")
        existing = session.scalar(select(PlatformBinding).where(PlatformBinding.asset_id == asset.id, PlatformBinding.platform == platform))
        if existing is not None:
            return {"id": existing.id, "assetId": asset.id, "platform": platform, "remoteId": existing.remote_id, "status": existing.status}
        result = MockPlatform(request.app.state.settings.spi_secret).upload_asset(asset.path, asset.id)
        binding = PlatformBinding(id=uuid.uuid4().hex, asset_id=asset.id, platform=platform, remote_id=result.remote_id, status=result.status, raw_json=json.dumps(result.raw))
        session.add(binding)
        session.commit()
        return {"id": binding.id, "assetId": asset.id, "platform": platform, "remoteId": result.remote_id, "status": result.status}


@router.get("")
def list_bindings(request: Request) -> list[dict]:
    with Session(request.app.state.database_engine) as session:
        return [{"id": b.id, "assetId": b.asset_id, "platform": b.platform, "remoteId": b.remote_id, "status": b.status} for b in session.scalars(select(PlatformBinding).order_by(PlatformBinding.created_at.desc())).all()]


@router.post("/mock/{binding_id}/simulate")
def simulate_callback(request: Request, binding_id: str, payload: dict) -> dict:
    status = payload.get("status")
    if status not in {"approved", "rejected"}:
        raise HTTPException(400, "状态必须是 approved 或 rejected")
    with Session(request.app.state.database_engine) as session:
        binding = session.get(PlatformBinding, binding_id)
        if binding is None:
            raise HTTPException(404, "平台绑定不存在")
        adapter = MockPlatform(request.app.state.settings.spi_secret)
        event_body = json.dumps({"event_id": payload.get("event_id") or uuid.uuid4().hex, "remote_id": binding.remote_id, "status": status}, separators=(",", ":")).encode()
        event = adapter.normalize_callback(json.loads(event_body), {})
        applied = apply_callback(session, "mock", event)
        session.commit()
        return {"id": binding.id, "status": status, "eventId": event.external_event_id, "duplicate": not applied}
