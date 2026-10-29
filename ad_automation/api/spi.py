from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from ad_automation.models import PlatformBinding
from ad_automation.platforms.mock import MockPlatform

router = APIRouter(prefix="/api/spi", tags=["spi"])


@router.post("/{platform}")
async def receive_spi(request: Request, platform: str) -> dict:
    body = await request.body()
    payload = json.loads(body)
    adapter = MockPlatform()
    if platform != "mock" or not adapter.verify_callback(body, request.headers):
        raise HTTPException(401, "SPI 签名无效")
    event = adapter.normalize_callback(payload, request.headers)
    with Session(request.app.state.database_engine) as session:
        binding = session.query(PlatformBinding).filter_by(platform=platform, remote_id=event.remote_id).first()
        if binding is None:
            raise HTTPException(404, "平台素材不存在")
        binding.status = event.status
        session.commit()
    return {"accepted": True, "eventId": event.external_event_id, "status": event.status}
