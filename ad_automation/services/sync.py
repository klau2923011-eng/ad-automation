from __future__ import annotations

import json
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import PlatformBinding, PlatformEvent
from ad_automation.platforms.base import CallbackEvent
from ad_automation.services.alerts import create_alert


VALID_STATUSES = {"pending_review", "approved", "rejected"}


def apply_callback(session: Session, platform: str, event: CallbackEvent) -> bool:
    existing = session.scalar(select(PlatformEvent).where(PlatformEvent.platform == platform, PlatformEvent.external_event_id == event.external_event_id))
    if existing:
        return False
    if event.status not in VALID_STATUSES:
        raise ValueError("回调状态无效")
    binding = session.scalar(select(PlatformBinding).where(PlatformBinding.platform == platform, PlatformBinding.remote_id == event.remote_id))
    if binding is None:
        raise LookupError("平台素材不存在")
    binding.status = event.status
    session.add(PlatformEvent(id=uuid.uuid4().hex, platform=platform, external_event_id=event.external_event_id, binding_id=binding.id, status=event.status, raw_json=json.dumps(event.raw, ensure_ascii=False)))
    if event.status == "rejected":
        create_alert(session, "platform", binding.id, "模拟平台拒绝了素材")
    return True
