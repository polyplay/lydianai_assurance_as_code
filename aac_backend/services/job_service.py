from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.jobs import Job
from aac_backend.services.event_service import record_event


async def create_job(
    session: AsyncSession,
    *,
    project_id: str | None,
    job_type: str,
    submitted_by: str | None,
    result_ref: dict | None = None,
) -> Job:
    job = Job(
        project_id=project_id,
        job_type=job_type,
        state="queued",
        submitted_by=submitted_by,
        submitted_at=datetime.now(UTC),
        result_ref_json=result_ref or {},
    )
    session.add(job)
    await session.flush()
    await record_event(
        session,
        event_type="job.created",
        project_id=project_id,
        actor_user_id=submitted_by,
        payload={"job_id": job.job_id, "job_type": job_type},
    )
    return job


async def run_tracked_job(
    session: AsyncSession,
    *,
    project_id: str | None,
    job_type: str,
    submitted_by: str | None,
    operation: Callable[[Job], Awaitable[Any]],
) -> tuple[Job, Any]:
    job = await create_job(
        session,
        project_id=project_id,
        job_type=job_type,
        submitted_by=submitted_by,
    )
    job.state = "running"
    job.started_at = datetime.now(UTC)
    try:
        result = await operation(job)
    except Exception as exc:
        job.state = "failed"
        job.completed_at = datetime.now(UTC)
        job.error_json = {"error": type(exc).__name__, "message": str(exc)}
        await record_event(
            session,
            event_type="job.failed",
            project_id=project_id,
            actor_user_id=submitted_by,
            payload={"job_id": job.job_id, "error": job.error_json},
        )
        raise
    job.state = "completed" if job.state not in {"waiting_for_user", "cancelled"} else job.state
    job.completed_at = None if job.state == "waiting_for_user" else datetime.now(UTC)
    job.progress_percent = 100 if job.state == "completed" else job.progress_percent
    await record_event(
        session,
        event_type="job.completed" if job.state == "completed" else f"job.{job.state}",
        project_id=project_id,
        actor_user_id=submitted_by,
        payload={"job_id": job.job_id, "job_type": job_type, "state": job.state},
    )
    return job, result


def job_data(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "job_type": job.job_type,
        "state": job.state,
        "progress_percent": job.progress_percent,
        "result_ref": job.result_ref_json,
        "error": job.error_json,
    }
