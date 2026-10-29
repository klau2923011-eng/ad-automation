from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from ad_automation.models import Asset, PlatformBinding
from ad_automation.platforms.mock import MockPlatform

router = APIRouter(prefix="/api/platforms", tags=["platforms"])


@router.post("/{platform}/sync")
def sync_asset(request: Request, platform: str, payload: dict) -> dict:
    if platform != "mock":
        raise HTTPException(400, "MVP 仅支持 mock 平台")
    with Session(request.app.state.database_engine) as session:
        asset = session.get(Asset, payload.get("assetId"))
        if asset is None:
            raise HTTPException(404, "素材不存在")
        result = MockPlatform().upload_asset(asset.path, asset.id)
        binding = PlatformBinding(id=uuid.uuid4().hex, asset_id=asset.id, platform=platform, remote_id=result.remote_id, status=result.status, raw_json=json.dumps(result.raw))
        session.add(binding)
        session.commit()
        return {"id": binding.id, "assetId": asset.id, "platform": platform, "remoteId": result.remote_id, "status": result.status}
