from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.repositories.domain import BaselineRepository
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import BaselineCreate, ReleaseGateRun
from aac_backend.services.baseline_service import (
    approve_baseline,
    create_baseline,
    obsolete_baseline,
    release_baseline,
    run_release_gate,
)
from aac_backend.services.job_service import job_data, run_tracked_job

router = APIRouter(tags=["baselines"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.post("/projects/{project_id}/baselines", response_model=ApiEnvelope)
async def create_baseline_endpoint(
    project_id: str,
    payload: BaselineCreate,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    async def operation(job):
        baseline = await create_baseline(session, project_id, payload, current.user.user_id, job=job)
        job.result_ref_json = {"resource_type": "Baseline", "resource_id": baseline.baseline_id}
        return baseline

    job, baseline = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="baseline_create",
        submitted_by=current.user.user_id,
        operation=operation,
    )
    await session.commit()
    return ApiEnvelope(status="accepted", data={"job": job_data(job), "baseline": _baseline_data(baseline)})


@router.get("/projects/{project_id}/baselines", response_model=ApiEnvelope)
async def list_baselines(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baselines = await BaselineRepository(session).list_for_project(project_id)
    return ApiEnvelope(data=[_baseline_data(baseline) for baseline in baselines])


@router.get("/projects/{project_id}/baselines/{baseline_id}", response_model=ApiEnvelope)
async def get_baseline(
    project_id: str,
    baseline_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await session.get(Baseline, baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return ApiEnvelope(data=_baseline_data(baseline))


@router.get("/projects/{project_id}/baselines/{baseline_id}/status", response_model=ApiEnvelope)
async def get_baseline_status(
    project_id: str,
    baseline_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await _get_baseline_or_404(session, project_id, baseline_id)
    return ApiEnvelope(
        data={
            "baseline_id": baseline.baseline_id,
            "state": baseline.state,
            "release_gate_status": baseline.release_gate_status,
            "summary": baseline.summary_json,
        }
    )


@router.post("/projects/{project_id}/baselines/compare", response_model=ApiEnvelope)
async def compare_baselines(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    left = await _get_baseline_or_404(session, project_id, payload["left_baseline_id"])
    right = await _get_baseline_or_404(session, project_id, payload["right_baseline_id"])
    return ApiEnvelope(
        data={
            "left_baseline_id": left.baseline_id,
            "right_baseline_id": right.baseline_id,
            "same_summary": left.summary_json == right.summary_json,
            "left_summary": left.summary_json,
            "right_summary": right.summary_json,
        }
    )


@router.post("/projects/{project_id}/release-gate/run", response_model=ApiEnvelope)
async def release_gate(
    project_id: str,
    payload: ReleaseGateRun,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await session.get(Baseline, payload.baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline not found")

    async def operation(job):
        result = await run_release_gate(session, project_id, baseline, current.user.user_id)
        job.result_ref_json = {
            "resource_type": "ReleaseGateResult",
            "resource_id": result.release_gate_result_id,
        }
        return result

    job, result = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="release_gate_evaluation",
        submitted_by=current.user.user_id,
        operation=operation,
    )
    await session.commit()
    return ApiEnvelope(
        status="accepted",
        data={"job": job_data(job), "release_gate_result": _release_gate_data(result)},
    )


@router.get(
    "/projects/{project_id}/baselines/{baseline_id}/release-gate/results",
    response_model=ApiEnvelope,
)
async def release_gate_results(
    project_id: str,
    baseline_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    results = list(
        await session.scalars(
            select(ReleaseGateResult).where(
                ReleaseGateResult.project_id == project_id,
                ReleaseGateResult.baseline_id == baseline_id,
            )
        )
    )
    return ApiEnvelope(data=[_release_gate_data(result) for result in results])


@router.get(
    "/projects/{project_id}/baselines/{baseline_id}/release-gate/results/latest",
    response_model=ApiEnvelope,
)
async def latest_release_gate_result(
    project_id: str,
    baseline_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    result = await session.scalar(
        select(ReleaseGateResult)
        .where(ReleaseGateResult.project_id == project_id, ReleaseGateResult.baseline_id == baseline_id)
        .order_by(ReleaseGateResult.evaluation_number.desc())
        .limit(1)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Release gate result not found")
    return ApiEnvelope(data=_release_gate_data(result))


@router.get(
    "/projects/{project_id}/baselines/{baseline_id}/release-gate/results/{result_id}",
    response_model=ApiEnvelope,
)
async def get_release_gate_result(
    project_id: str,
    baseline_id: str,
    result_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    result = await session.get(ReleaseGateResult, result_id)
    if not result or result.project_id != project_id or result.baseline_id != baseline_id:
        raise HTTPException(status_code=404, detail="Release gate result not found")
    return ApiEnvelope(data=_release_gate_data(result))


@router.post("/projects/{project_id}/baselines/{baseline_id}/approve", response_model=ApiEnvelope)
async def approve_baseline_endpoint(
    project_id: str,
    baseline_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await _get_baseline_or_404(session, project_id, baseline_id)
    try:
        baseline = await approve_baseline(session, baseline, current.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=_baseline_data(baseline))


@router.post("/projects/{project_id}/baselines/{baseline_id}/release", response_model=ApiEnvelope)
async def release_baseline_endpoint(
    project_id: str,
    baseline_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await _get_baseline_or_404(session, project_id, baseline_id)
    try:
        baseline = await release_baseline(session, baseline, current.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=_baseline_data(baseline))


@router.post("/projects/{project_id}/baselines/{baseline_id}/obsolete", response_model=ApiEnvelope)
async def obsolete_baseline_endpoint(
    project_id: str,
    baseline_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await _get_baseline_or_404(session, project_id, baseline_id)
    baseline = await obsolete_baseline(session, baseline, current.user.user_id)
    await session.commit()
    return ApiEnvelope(data=_baseline_data(baseline))


async def _get_baseline_or_404(
    session: AsyncSession,
    project_id: str,
    baseline_id: str,
) -> Baseline:
    baseline = await session.get(Baseline, baseline_id)
    if not baseline or baseline.project_id != project_id:
        raise HTTPException(status_code=404, detail="Baseline not found")
    return baseline


def _baseline_data(baseline: Baseline) -> dict:
    return {
        "baseline_id": baseline.baseline_id,
        "project_id": baseline.project_id,
        "name": baseline.name,
        "state": baseline.state,
        "release_gate_status": baseline.release_gate_status,
        "summary": baseline.summary_json,
    }


def _release_gate_data(result: ReleaseGateResult) -> dict:
    return {
        "release_gate_result_id": result.release_gate_result_id,
        "baseline_id": result.baseline_id,
        "status": result.status,
        "result": result.result,
        "blocking_issues": result.blocking_issues_json,
    }
