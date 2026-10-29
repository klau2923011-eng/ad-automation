from __future__ import annotations

import hashlib
import uuid
from pathlib import Path
from typing import BinaryIO

from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.media.probe import probe_video
from ad_automation.models import Asset


ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}
MAX_UPLOAD_BYTES = 500 * 1024 * 1024
CHUNK_SIZE = 1024 * 1024


def store_asset(
    session: Session,
    data_dir: Path,
    filename: str,
    media_type: str,
    source: BinaryIO,
) -> Asset:
    safe_filename = Path(filename).name
    suffix = Path(safe_filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("仅支持 MP4、MOV、WEBM 视频")

    assets_dir = data_dir / "assets"
    assets_dir.mkdir(parents=True, exist_ok=True)
    asset_id = uuid.uuid4().hex
    target = assets_dir / f"{asset_id}{suffix}"
    digest = hashlib.sha256()
    size_bytes = 0
    try:
        with target.open("xb") as destination:
            while chunk := source.read(CHUNK_SIZE):
                size_bytes += len(chunk)
                if size_bytes > MAX_UPLOAD_BYTES:
                    raise ValueError("视频文件不能超过 500 MB")
                digest.update(chunk)
                destination.write(chunk)
        if size_bytes == 0:
            raise ValueError("视频文件不能为空")

        sha256 = digest.hexdigest()
        duplicate = session.scalar(select(Asset.id).where(Asset.sha256 == sha256))
        metadata = probe_video(target)
        asset = Asset(
            id=asset_id,
            filename=safe_filename[:255],
            path=str(target),
            media_type=media_type or "application/octet-stream",
            size_bytes=size_bytes,
            sha256=sha256,
            status="duplicate" if duplicate else "ready",
            probe_status="available" if metadata else "unavailable",
            duration_seconds=metadata["duration_seconds"] if metadata else None,
            width=metadata["width"] if metadata else None,
            height=metadata["height"] if metadata else None,
        )
        session.add(asset)
        session.commit()
        session.refresh(asset)
        return asset
    except Exception:
        target.unlink(missing_ok=True)
        session.rollback()
        raise
