from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.models import Asset, JobStep, ProcessingJob

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.post("")
def create_job(request: Request, payload: dict) -> dict:
    asset_id = payload.get("assetId")
    if not asset_id:
        raise HTTPException(400, "assetId 必填")
    with Session(request.app.state.database_engine) as session:
        if session.get(Asset, asset_id) is None:
            raise HTTPException(404, "素材不存在")
        job = ProcessingJob(id=uuid.uuid4().hex, asset_id=asset_id, status="pending", attempts=0, max_attempts=3)
        session.add(job)
        for position, step in enumerate(payload.get("steps", [])):
            session.add(JobStep(id=uuid.uuid4().hex, job_id=job.id, position=position, kind=step.get("kind", "encode"), params_json=json.dumps(step.get("params", {}), ensure_ascii=False)))
        session.commit()
        return {"id": job.id, "assetId": job.asset_id, "status": job.status, "attempts": job.attempts}


@router.get("")
def list_jobs(request: Request) -> list[dict]:
    with Session(request.app.state.database_engine) as session:
        return [{"id": job.id, "assetId": job.asset_id, "status": job.status, "attempts": job.attempts} for job in session.scalars(select(ProcessingJob).order_by(ProcessingJob.created_at.desc())).all()]
