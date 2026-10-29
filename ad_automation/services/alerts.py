from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import Alert


def create_alert(session: Session, source: str, object_id: str, message: str) -> Alert:
    existing = session.scalar(select(Alert).where(Alert.source == source, Alert.object_id == object_id, Alert.status == "open"))
    if existing:
        return existing
    alert = Alert(id=uuid.uuid4().hex, source=source, object_id=object_id, message=message, level="error", status="open")
    session.add(alert)
    session.flush()
    return alert
