from collections.abc import Awaitable, Callable
from datetime import UTC, datetime
import logging
from typing import Any

from arq import create_pool
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.jobs import Job
from aac_backend.services.event_service import record_event
from aac_backend.services.observability import job_log_fields, structured_log
from aac_backend.services.request_context import current_correlation_id
from aac_backend.workers.settings_support import redis_settings

LOGGER = logging.getLogger(__name__)


async def create_job(
    session: AsyncSession,
    *,
    project_id: str | None,
    job_type: str,
    submitted_by: str | None,
    result_ref: dict | None = None,
    correlation_id: str | None = None,
    causation_id: str | None = None,
    idempotency_key: str | None = None,
) -> Job:
    job = Job(
        project_id=project_id,
        job_type=job_type,
        state="queued",
        submitted_by=submitted_by,
        submitted_at=datetime.now(UTC),
        correlation_id=correlation_id or current_correlation_id(),
        causation_id=causation_id,
        idempotency_key=idempotency_key,
        committed_effects_json={"exists": False, "last_committed_unit": None},
        result_ref_json=result_ref or {},
    )
    session.add(job)
    await session.flush()
    structured_log(
        LOGGER,
        logging.INFO,
        "job.created",
        **job_log_fields(
            job_id=job.job_id,
            job_type=job_type,
            project_id=project_id,
            actor_user_id=submitted_by,
            state=job.state,
            result_ref=result_ref,
        ),
    )
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
    arq_job_name: str | None = None,
    arq_args: tuple = (),
) -> tuple[Job, Any]:
    job = await create_job(
        session,
        project_id=project_id,
        job_type=job_type,
        submitted_by=submitted_by,
    )
    if arq_job_name:
        try:
            redis = await create_pool(redis_settings())
            arq_job = await redis.enqueue_job(arq_job_name, job.job_id, *arq_args)
            await redis.close()
        except Exception:
            job.error_json = {"queue_fallback": "redis_unavailable_inline_execution"}
            structured_log(
                LOGGER,
                logging.WARNING,
                "job.queue_fallback",
                **job_log_fields(
                    job_id=job.job_id,
                    job_type=job_type,
                    project_id=project_id,
                    actor_user_id=submitted_by,
                    state=job.state,
                    error="redis_unavailable_inline_execution",
                ),
            )
        else:
            job.state = "queued"
            job.result_ref_json = {"arq_job_id": arq_job.job_id if arq_job else None}
            structured_log(
                LOGGER,
                logging.INFO,
                "job.queued",
                **job_log_fields(
                    job_id=job.job_id,
                    job_type=job_type,
                    project_id=project_id,
                    actor_user_id=submitted_by,
                    state=job.state,
                    result_ref=job.result_ref_json,
                ),
            )
            await record_event(
                session,
                event_type="job.queued",
                project_id=project_id,
                actor_user_id=submitted_by,
                payload={"job_id": job.job_id, "job_type": job_type, "arq_job_name": arq_job_name},
            )
            return job, None
    job.state = "running"
    job.started_at = datetime.now(UTC)
    structured_log(
        LOGGER,
        logging.INFO,
        "job.running",
        **job_log_fields(
            job_id=job.job_id,
            job_type=job_type,
            project_id=project_id,
            actor_user_id=submitted_by,
            state=job.state,
        ),
    )
    try:
        result = await operation(job)
    except Exception as exc:
        job.state = "failed"
        job.completed_at = datetime.now(UTC)
        job.error_json = {"error": type(exc).__name__, "message": str(exc)}
        structured_log(
            LOGGER,
            logging.ERROR,
            "job.failed",
            **job_log_fields(
                job_id=job.job_id,
                job_type=job_type,
                project_id=project_id,
                actor_user_id=submitted_by,
                state=job.state,
                error=exc,
            ),
        )
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
    structured_log(
        LOGGER,
        logging.INFO,
        "job.completed",
        **job_log_fields(
            job_id=job.job_id,
            job_type=job_type,
            project_id=project_id,
            actor_user_id=submitted_by,
            state=job.state,
            result_ref=job.result_ref_json,
        ),
    )
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
        "cancellation_requested": job.cancellation_requested,
        "committed_effects": job.committed_effects_json,
        "last_committed_unit": job.last_committed_unit,
        "result_ref": job.result_ref_json,
        "error": job.error_json,
    }
