from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import Alert

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


def _payload(alert: Alert) -> dict:
    return {"id": alert.id, "source": alert.source, "objectId": alert.object_id, "level": alert.level, "message": alert.message, "status": alert.status, "createdAt": alert.created_at}


@router.get("")
def list_alerts(request: Request) -> list[dict]:
    with Session(request.app.state.database_engine) as session:
        return [_payload(alert) for alert in session.scalars(select(Alert).order_by(Alert.created_at.desc())).all()]


@router.post("/{alert_id}/ack")
def acknowledge_alert(request: Request, alert_id: str) -> dict:
    with Session(request.app.state.database_engine) as session:
        alert = session.get(Alert, alert_id)
        if alert is None:
            raise HTTPException(404, "告警不存在")
        alert.status = "acknowledged"
        session.commit()
        return _payload(alert)
