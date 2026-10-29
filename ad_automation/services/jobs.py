from __future__ import annotations

from ad_automation.models import ProcessingJob


class InvalidJobTransition(ValueError):
    pass


ALLOWED = {
    "pending": {"running"},
    "running": {"succeeded", "failed"},
    "failed": set(),
    "succeeded": set(),
    "dead_letter": set(),
}


def transition_job(job: ProcessingJob, target: str) -> None:
    if target not in ALLOWED.get(job.status, set()):
        raise InvalidJobTransition(f"不允许从 {job.status} 迁移到 {target}")
    if target == "running":
        job.attempts += 1
    job.status = target


def retry_failed_job(job: ProcessingJob) -> None:
    if job.status != "failed":
        raise InvalidJobTransition("只有 failed 任务可以重试")
    job.status = "pending" if job.attempts < job.max_attempts else "dead_letter"
