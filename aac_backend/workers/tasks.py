import aac_backend.models.all_models  # noqa: F401
from aac_backend.repositories.unit_of_work import unit_of_work
from aac_backend.schemas.domain import BaselineCreate, ImportStart, ReleaseGateRun
from aac_backend.services.baseline_service import create_baseline, run_release_gate
from aac_backend.services.import_service import import_sphinx_needs
from aac_backend.services.impact_service import analyze_impact
from aac_backend.services.repository_integration_service import run_repository_scan
from aac_backend.services.validation_service import run_validation


async def import_sphinx_job(ctx, job_id: str, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
        try:
            run = await import_sphinx_needs(session, project_id, ImportStart(**payload), actor_user_id)
        except Exception as exc:
            if job:
                job.state = "failed"
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
                await session.commit()
            raise
        if job:
            job.state = "completed" if run.state != "waiting_for_user" else "waiting_for_user"
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
        from datetime import UTC, datetime

        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
        try:
            run = await run_validation(session, project_id, actor_user_id, scope=scope)
        except Exception as exc:
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
                await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {"resource_type": "ValidationRun", "resource_id": run.validation_run_id}
        return run.validation_run_id


async def baseline_job(ctx, job_id: str, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from datetime import UTC, datetime

        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
        try:
            baseline = await create_baseline(session, project_id, BaselineCreate(**payload), actor_user_id, job=job)
        except Exception as exc:
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
                await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {"resource_type": "Baseline", "resource_id": baseline.baseline_id}
        return baseline.baseline_id


async def impact_job(ctx, job_id: str, project_id: str, artefact_id: str, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
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
        return run.impact_analysis_id


async def release_gate_job(ctx, job_id: str, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from datetime import UTC, datetime

        from aac_backend.models.baselines import Baseline
        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
        try:
            body = ReleaseGateRun(**payload)
            baseline = await session.get(Baseline, body.baseline_id)
            if baseline is None:
                raise ValueError("Baseline not found")
            result = await run_release_gate(session, project_id, baseline, actor_user_id)
        except Exception as exc:
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
                await session.commit()
            raise
        if job:
            job.state = "completed"
            job.progress_percent = 100
            job.result_ref_json = {
                "resource_type": "ReleaseGateResult",
                "resource_id": result.release_gate_result_id,
            }
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
        from datetime import UTC, datetime

        from aac_backend.models.jobs import Job

        job = await session.get(Job, job_id)
        if job:
            job.state = "running"
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
            if job:
                job.state = "failed"
                job.completed_at = datetime.now(UTC)
                job.error_json = {"error": type(exc).__name__, "message": str(exc)}
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
        return scan_run.repository_scan_run_id
