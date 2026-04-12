from aac_backend.repositories.unit_of_work import unit_of_work
from aac_backend.schemas.domain import BaselineCreate, ImportStart, ReleaseGateRun
from aac_backend.services.baseline_service import create_baseline, run_release_gate
from aac_backend.services.import_service import import_sphinx_needs
from aac_backend.services.impact_service import analyze_impact
from aac_backend.services.validation_service import run_validation


async def import_sphinx_job(ctx, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        run = await import_sphinx_needs(session, project_id, ImportStart(**payload), actor_user_id)
        return run.import_run_id


async def validation_job(ctx, project_id: str, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        run = await run_validation(session, project_id, actor_user_id)
        return run.validation_run_id


async def baseline_job(ctx, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        baseline = await create_baseline(session, project_id, BaselineCreate(**payload), actor_user_id)
        return baseline.baseline_id


async def impact_job(ctx, project_id: str, artefact_id: str, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        run = await analyze_impact(
            session,
            project_id=project_id,
            artefact_id=artefact_id,
            actor_user_id=actor_user_id,
        )
        return run.impact_analysis_id


async def release_gate_job(ctx, project_id: str, payload: dict, actor_user_id: str) -> str:
    async with unit_of_work() as session:
        from aac_backend.models.baselines import Baseline

        body = ReleaseGateRun(**payload)
        baseline = await session.get(Baseline, body.baseline_id)
        if baseline is None:
            raise ValueError("Baseline not found")
        result = await run_release_gate(session, project_id, baseline, actor_user_id)
        return result.release_gate_result_id
