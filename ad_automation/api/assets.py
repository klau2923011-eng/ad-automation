from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import Asset
from ad_automation.services.assets import store_asset

router = APIRouter(prefix="/api/assets", tags=["assets"])


def _payload(asset: Asset) -> dict:
    return {
        "id": asset.id,
        "filename": asset.filename,
        "mediaType": asset.media_type,
        "sizeBytes": asset.size_bytes,
        "sha256": asset.sha256,
        "perceptualHash": asset.perceptual_hash,
        "status": asset.status,
        "probeStatus": asset.probe_status,
        "durationSeconds": asset.duration_seconds,
        "width": asset.width,
        "height": asset.height,
        "createdAt": asset.created_at,
    }


@router.post("")
async def upload_asset(request: Request, file: UploadFile = File(...)) -> dict:
    try:
        with Session(request.app.state.database_engine) as session:
            asset = store_asset(
                session,
                request.app.state.settings.data_dir,
                file.filename or "",
                file.content_type or "",
                file.file,
            )
            return _payload(asset)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("")
def list_assets(request: Request) -> list[dict]:
    with Session(request.app.state.database_engine) as session:
        assets = session.scalars(select(Asset).order_by(Asset.created_at.desc())).all()
        return [_payload(asset) for asset in assets]
