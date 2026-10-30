from __future__ import annotations

import json

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy.orm import Session

from ad_automation.models import PlatformBinding
from ad_automation.services.alerts import create_alert
from ad_automation.services.sync import apply_callback
from ad_automation.platforms.mock import MockPlatform

router = APIRouter(prefix="/api/spi", tags=["spi"])


@router.post("/{platform}")
async def receive_spi(request: Request, platform: str) -> dict:
    if platform != "mock":
        raise HTTPException(400, "当前 MVP 仅支持 mock 平台")
    body = await request.body()
    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise HTTPException(400, "SPI JSON 无效") from exc
    adapter = MockPlatform(request.app.state.settings.spi_secret)
    if not adapter.verify_callback(body, request.headers):
        with Session(request.app.state.database_engine) as session:
            create_alert(session, "spi", "signature", "SPI 签名无效")
            session.commit()
        raise HTTPException(401, "SPI 签名无效")
    event = adapter.normalize_callback(payload, request.headers)
    with Session(request.app.state.database_engine) as session:
        try:
            applied = apply_callback(session, platform, event)
        except LookupError as exc:
            raise HTTPException(404, str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        session.commit()
    return {"accepted": True, "duplicate": not applied, "eventId": event.external_event_id, "status": event.status}
