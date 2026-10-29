from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.media.ffmpeg import process_step
from ad_automation.models import Asset, JobStep, ProcessingJob
from ad_automation.services.jobs import transition_job

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _execute_job(request: Request, job_id: str) -> None:
    with Session(request.app.state.database_engine) as session:
        job = session.get(ProcessingJob, job_id)
        if job is None:
            return
        try:
            transition_job(job, "running")
            current = Path(session.get(Asset, job.asset_id).path)
            steps = session.scalars(select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.position)).all()
            for step in steps:
                output = request.app.state.settings.data_dir / "outputs" / job.id / f"{step.position}.mp4"
                process_step(current, output, step.kind, json.loads(step.params_json), request.app.state.settings.ffmpeg_path or "ffmpeg", request.app.state.settings.ffprobe_path or "ffprobe")
                step.status = "succeeded"
                step.output_path = str(output)
                current = output
            if steps:
                output_asset = Asset(id=uuid.uuid4().hex, parent_id=job.asset_id, filename=f"{job.id}.mp4", path=str(current), media_type="video/mp4", size_bytes=current.stat().st_size, sha256="", status="ready", probe_status="available")
                session.add(output_asset)
                job.output_asset_id = output_asset.id
            transition_job(job, "succeeded")
        except Exception as exc:
            job.status = "failed"
            job.error_summary = str(exc)
        session.commit()


@router.post("")
def create_job(request: Request, background_tasks: BackgroundTasks, payload: dict) -> dict:
    asset_id = payload.get("assetId")
    if not asset_id:
        raise HTTPException(400, "assetId 必填")
    with Session(request.app.state.database_engine) as session:
        if session.get(Asset, asset_id) is None:
            raise HTTPException(404, "素材不存在")
        job = ProcessingJob(id=uuid.uuid4().hex, asset_id=asset_id, status="pending", attempts=0, max_attempts=3)
        job_id = job.id
        session.add(job)
        for position, step in enumerate(payload.get("steps", [])):
            session.add(JobStep(id=uuid.uuid4().hex, job_id=job.id, position=position, kind=step.get("kind", "encode"), params_json=json.dumps(step.get("params", {}), ensure_ascii=False)))
        session.commit()
    background_tasks.add_task(_execute_job, request, job_id)
    return {"id": job_id, "assetId": asset_id, "status": "pending", "attempts": 0}


@router.get("")
def list_jobs(request: Request) -> list[dict]:
    with Session(request.app.state.database_engine) as session:
        return [{"id": job.id, "assetId": job.asset_id, "status": job.status, "attempts": job.attempts} for job in session.scalars(select(ProcessingJob).order_by(ProcessingJob.created_at.desc())).all()]


@router.get("/{job_id}")
def get_job(request: Request, job_id: str) -> dict:
    with Session(request.app.state.database_engine) as session:
        job = session.get(ProcessingJob, job_id)
        if job is None:
            raise HTTPException(404, "任务不存在")
        steps = session.scalars(select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.position)).all()
        return {"id": job.id, "assetId": job.asset_id, "status": job.status, "attempts": job.attempts, "outputAssetId": job.output_asset_id, "error": job.error_summary, "steps": [{"kind": s.kind, "status": s.status, "outputPath": s.output_path, "error": s.error_summary} for s in steps]}
