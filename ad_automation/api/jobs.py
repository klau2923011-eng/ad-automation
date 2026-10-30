from __future__ import annotations

import json
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ad_automation.media.ffmpeg import process_step
from ad_automation.models import Asset, JobStep, ProcessingJob
from ad_automation.services.jobs import transition_job, retry_failed_job
from ad_automation.media.fingerprint import perceptual_fingerprint, sha256_file
from ad_automation.media.probe import probe_video
from ad_automation.services.alerts import create_alert

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


def _execute_job(request: Request, job_id: str) -> None:
    with Session(request.app.state.database_engine) as session:
        job = session.get(ProcessingJob, job_id)
        if job is None:
            return
        active_step: JobStep | None = None
        try:
            transition_job(job, "running")
            current = Path(session.get(Asset, job.asset_id).path)
            steps = session.scalars(select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.position)).all()
            for step in steps:
                active_step = step
                output = request.app.state.settings.data_dir / "outputs" / job.id / f"{step.position}.mp4"
                process_step(current, output, step.kind, json.loads(step.params_json), request.app.state.settings.ffmpeg_path or "ffmpeg", request.app.state.settings.ffprobe_path or "ffprobe")
                step.status = "succeeded"
                step.output_path = str(output)
                step.error_summary = None
                current = output
                active_step = None
            if steps:
                metadata = probe_video(current) or {}
                output_asset = Asset(id=uuid.uuid4().hex, parent_id=job.asset_id, filename=f"{job.id}.mp4", path=str(current), media_type="video/mp4", size_bytes=current.stat().st_size, sha256=sha256_file(current), perceptual_hash=perceptual_fingerprint(current), status="ready", probe_status="available", duration_seconds=metadata.get("duration_seconds"), width=metadata.get("width"), height=metadata.get("height"))
                session.add(output_asset)
                job.output_asset_id = output_asset.id
            transition_job(job, "succeeded")
        except Exception as exc:
            job.status = "failed"
            job.error_summary = str(exc)
            if active_step is not None:
                active_step.status = "failed"
                active_step.error_summary = str(exc)
            create_alert(session, "job", job.id, str(exc))
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


@router.post("/{job_id}/retry")
def retry_job(request: Request, background_tasks: BackgroundTasks, job_id: str) -> dict:
    with Session(request.app.state.database_engine) as session:
        job = session.get(ProcessingJob, job_id)
        if job is None:
            raise HTTPException(404, "任务不存在")
        try:
            steps = session.scalars(select(JobStep).where(JobStep.job_id == job.id).order_by(JobStep.position)).all()
            retry_failed_job(job, steps)
        except ValueError as exc:
            raise HTTPException(409, str(exc)) from exc
        attempts = job.attempts
        session.commit()
    background_tasks.add_task(_execute_job, request, job_id)
    return {"id": job_id, "status": "pending", "attempts": attempts}
