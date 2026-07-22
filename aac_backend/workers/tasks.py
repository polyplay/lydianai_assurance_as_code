import logging
from datetime import UTC, datetime

import aac_backend.models.all_models  # noqa: F401
from arq import Retry

from aac_backend.repositories.unit_of_work import unit_of_work
from aac_backend.schemas.domain import BaselineCreate, ReleaseGateRun
from aac_backend.services.baseline_service import create_baseline, run_release_gate
from aac_backend.services.event_dispatcher import dispatch_pending_events
from aac_backend.services.import_service import (
    mark_import_failed,
    mark_import_interrupted,
    process_import_run,
)
from aac_backend.services.impact_service import analyze_impact
from aac_backend.services.observability import job_log_fields, structured_log
from aac_backend.services.repository_integration_service import run_repository_scan
from aac_backend.services.request_context import establish_request_context
from aac_backend.services.validation_service import run_validation

IMPORT_MAX_TRIES = 5
LOGGER = logging.getLogger(__name__)


async def outbox_dispatch_job(ctx) -> int:
    return await dispatch_pending_events()


async def import_sphinx_job(ctx, job_id: str, import_run_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.imports import ImportRun
        from aac_backend.models.jobs import Job
        from aac_backend.services.auth_service import user_roles

        job = await session.get(Job, job_id)
        import_run = await session.get(ImportRun, import_run_id)
        if import_run is None:
            raise ValueError("Import run not found")
        _establish_job_context(job)
        if job:
            job.state = "running"
            if job.cancellation_requested:
                import_run.cancellation_requested = True
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="import",
                    project_id=import_run.project_id,
                    actor_user_id=import_run.submitted_by,
                    state="running",
                ),
            )
        try:
            roles = set(
                await user_roles(
                    session,
                    import_run.submitted_by,
                    import_run.project_id,
                )
            )
            run = await process_import_run(
                session,
                import_run,
                import_run.submitted_by,
                actor_roles=roles,
                job=job,
            )
        except Exception as exc:
            structured_log(
                LOGGER,
                logging.ERROR,
                "job.failed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="import",
                    project_id=import_run.project_id,
                    actor_user_id=import_run.submitted_by,
                    state="failed",
                    error=exc,
                ),
            )
            job_try = int((ctx or {}).get("job_try", 1))
            if job_try < IMPORT_MAX_TRIES:
                await mark_import_interrupted(
                    session,
                    import_run_id=import_run_id,
                    job_id=job_id,
                    actor_user_id=import_run.submitted_by,
                    error=exc,
                    attempt=job_try,
                )
                raise Retry(defer=min(2**job_try, 30)) from exc
            await mark_import_failed(
                session,
                import_run_id=import_run_id,
                job_id=job_id,
                actor_user_id=import_run.submitted_by,
                error=exc,
            )
            raise
        if job:
            if run.state.startswith("completed"):
                job.state = "completed"
            else:
                job.state = run.state
            job.progress_percent = 100 if job.state == "completed" else job.progress_percent
            job.result_ref_json = {"resource_type": "ImportRun", "resource_id": run.import_run_id}
        return run.import_run_id


async def validation_job(
    ctx,
    job_id: str,
    project_id: str,
    actor_user_id: str,
    scope: dict | None = None,
) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        _establish_job_context(job)
        if job:
            job.state = "running"
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="validation",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="running",
                ),
            )
        try:
            run = await run_validation(session, project_id, actor_user_id, scope=scope)
        except Exception as exc:
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
            structured_log(
                LOGGER,
                logging.ERROR,
                "job.failed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="validation",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="failed",
                    error=exc,
                ),
            )
            await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {"resource_type": "ValidationRun", "resource_id": run.validation_run_id}
            structured_log(
                LOGGER,
                logging.INFO,
                "job.completed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="validation",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="completed",
                    result_ref=job.result_ref_json,
                ),
            )
        return run.validation_run_id


async def baseline_job(ctx, job_id: str, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        _establish_job_context(job)
        if job:
            job.state = "running"
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="baseline",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="running",
                ),
            )
        try:
            baseline = await create_baseline(session, project_id, BaselineCreate(**payload), actor_user_id, job=job)
        except Exception as exc:
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
            structured_log(
                LOGGER,
                logging.ERROR,
                "job.failed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="baseline",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="failed",
                    error=exc,
                ),
            )
            await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {"resource_type": "Baseline", "resource_id": baseline.baseline_id}
            structured_log(
                LOGGER,
                logging.INFO,
                "job.completed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="baseline",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="completed",
                    result_ref=job.result_ref_json,
                ),
            )
        return baseline.baseline_id


async def impact_job(ctx, job_id: str, project_id: str, artefact_id: str, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        _establish_job_context(job)
        if job:
            job.state = "running"
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="impact",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="running",
                ),
            )
        run = await analyze_impact(
            session,
            project_id=project_id,
            artefact_id=artefact_id,
            actor_user_id=actor_user_id,
        )
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {"resource_type": "ImpactAnalysisRun", "resource_id": run.impact_analysis_id}
            structured_log(
                LOGGER,
                logging.INFO,
                "job.completed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="impact",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="completed",
                    result_ref=job.result_ref_json,
                ),
            )
        return run.impact_analysis_id


async def release_gate_job(ctx, job_id: str, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.baselines import Baseline
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        _establish_job_context(job)
        if job:
            job.state = "running"
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="release_gate",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="running",
                ),
            )
        try:
            body = ReleaseGateRun(**payload)
            baseline = await session.get(Baseline, body.baseline_id)
            if baseline is None:
                raise ValueError("Baseline not found")
            result = await run_release_gate(session, project_id, baseline, actor_user_id)
        except Exception as exc:
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
            structured_log(
                LOGGER,
                logging.ERROR,
                "job.failed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="release_gate",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="failed",
                    error=exc,
                ),
            )
            await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {
                "resource_type": "ReleaseGateResult",
                "resource_id": result.release_gate_result_id,
            }
            structured_log(
                LOGGER,
                logging.INFO,
                "job.completed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="release_gate",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="completed",
                    result_ref=job.result_ref_json,
                ),
            )
        return result.release_gate_result_id


async def repository_scan_job(
    ctx,
    job_id: str,
    project_id: str,
    connector_id: str,
    actor_user_id: str | None,
    payload: dict,
) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        _establish_job_context(job)
        if job:
            job.state = "running"
            structured_log(
                LOGGER,
                logging.INFO,
                "job.running",
                **job_log_fields(
                    job_id=job_id,
                    job_type="repository_scan",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="running",
                ),
            )
        try:
            scan_run = await run_repository_scan(
                session,
                project_id=project_id,
                connector_id=connector_id,
                actor_user_id=actor_user_id,
                payload=payload,
                job=job,
            )
        except Exception as exc:
            await session.rollback()
            job = await session.get(Job, job_id)
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
            structured_log(
                LOGGER,
                logging.ERROR,
                "job.failed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="repository_scan",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="failed",
                    error=exc,
                ),
            )
            await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.completed_at = datetime.now(UTC)
            job.result_ref_json = {
                "resource_type": "RepositoryScanRun",
                "resource_id": scan_run.repository_scan_run_id,
            }
            structured_log(
                LOGGER,
                logging.INFO,
                "job.completed",
                **job_log_fields(
                    job_id=job_id,
                    job_type="repository_scan",
                    project_id=project_id,
                    actor_user_id=actor_user_id,
                    state="completed",
                    result_ref=job.result_ref_json,
                ),
            )
        return scan_run.repository_scan_run_id


def _establish_job_context(job) -> None:
    establish_request_context(
        request_id=f"REQ_{job.job_id}" if job else None,
        correlation_id=job.correlation_id if job else None,
    )
