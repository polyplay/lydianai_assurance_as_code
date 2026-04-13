from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.impact import ImpactAnalysisRun, SuspectState
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.impact_service import analyze_impact, clear_suspect_state
from aac_backend.services.job_service import job_data, run_tracked_job
from aac_backend.services.traceability_service import trace_artefact

router = APIRouter(tags=["traceability"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/projects/{project_id}/trace/{artefact_id}", response_model=ApiEnvelope)
async def trace(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    return ApiEnvelope(data=await trace_artefact(session, project_id, artefact_id))


@router.get("/projects/{project_id}/trace/{artefact_id}/forward", response_model=ApiEnvelope)
async def trace_forward(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    trace_data = await trace_artefact(session, project_id, artefact_id)
    return ApiEnvelope(data={"artefact_id": artefact_id, "forward": trace_data["forward"]})


@router.get("/projects/{project_id}/trace/{artefact_id}/backward", response_model=ApiEnvelope)
async def trace_backward(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    trace_data = await trace_artefact(session, project_id, artefact_id)
    return ApiEnvelope(data={"artefact_id": artefact_id, "backward": trace_data["backward"]})


@router.get("/projects/{project_id}/traceability-matrix", response_model=ApiEnvelope)
async def traceability_matrix(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    from sqlalchemy import select

    from aac_backend.models.artefacts import Relationship

    relationships = list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
    )
    return ApiEnvelope(
        data=[
            {
                "source_artefact_id": item.source_artefact_id,
                "relationship_type": item.relationship_type,
                "target_artefact_id": item.target_artefact_id,
            }
            for item in relationships
        ]
    )


@router.post("/projects/{project_id}/impact", response_model=ApiEnvelope)
async def impact(
    project_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact_id = payload["artefact_id"]
    async def operation(job):
        run = await analyze_impact(
            session,
            project_id=project_id,
            artefact_id=artefact_id,
            actor_user_id=current.user.user_id,
        )
        job.result_ref_json = {
            "resource_type": "ImpactAnalysisRun",
            "resource_id": run.impact_analysis_id,
        }
        return run

    job, run = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="impact_analysis",
        submitted_by=current.user.user_id,
        operation=operation,
        arq_job_name="impact_job",
        arq_args=(project_id, artefact_id, current.user.user_id),
    )
    await session.commit()
    if run is None:
        return ApiEnvelope(status="accepted", data={"job": job_data(job)})
    return ApiEnvelope(status="accepted", data={"job": job_data(job), "impact": _impact_run_data(run)})


@router.get("/projects/{project_id}/impact/{impact_id}", response_model=ApiEnvelope)
async def get_impact(
    project_id: str,
    impact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    run = await session.get(ImpactAnalysisRun, impact_id)
    if not run or run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Impact analysis not found")
    return ApiEnvelope(data=_impact_run_data(run))


@router.get("/projects/{project_id}/suspect-states", response_model=ApiEnvelope)
async def list_suspect_states(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    suspects = list(
        await session.scalars(select(SuspectState).where(SuspectState.project_id == project_id))
    )
    return ApiEnvelope(data=[_suspect_data(suspect) for suspect in suspects])


@router.post("/projects/{project_id}/suspect-states/{suspect_id}/clear", response_model=ApiEnvelope)
async def clear_suspect(
    project_id: str,
    suspect_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    suspect = await session.get(SuspectState, suspect_id)
    if not suspect or suspect.project_id != project_id:
        raise HTTPException(status_code=404, detail="Suspect state not found")
    suspect = await clear_suspect_state(
        session,
        suspect_state=suspect,
        actor_user_id=current.user.user_id,
        clearing_method=payload["clearing_method"],
        evidence_refs=payload.get("evidence_refs", []),
        reason=payload.get("reason"),
    )
    await session.commit()
    return ApiEnvelope(data=_suspect_data(suspect))


def _impact_run_data(run: ImpactAnalysisRun) -> dict:
    return {
        "impact_analysis_id": run.impact_analysis_id,
        "project_id": run.project_id,
        "state": run.state,
        "scope": run.scope_json,
        "summary": run.summary_json,
    }


def _suspect_data(suspect: SuspectState) -> dict:
    return {
        "suspect_state_id": suspect.suspect_state_id,
        "artefact_id": suspect.artefact_id,
        "trigger_artefact_id": suspect.trigger_artefact_id,
        "trigger_revision_id": suspect.trigger_revision_id,
        "trigger_event_type": suspect.trigger_event_type,
        "propagation_depth": suspect.propagation_depth,
        "propagation_path": suspect.propagation_path_json,
        "status": suspect.status,
        "clearing_method": suspect.clearing_method,
        "clearing_evidence_refs": suspect.clearing_evidence_refs_json,
    }
