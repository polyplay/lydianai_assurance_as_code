from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, get_current_user, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.jobs import Job
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.event_service import record_event
from aac_backend.services.presentation_policy import job_allowed_actions

router = APIRouter(tags=["jobs"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/jobs/{job_id}", response_model=ApiEnvelope)
async def get_job(
    job_id: str,
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.submitted_by != current.user.user_id and "admin" not in current.global_roles:
        raise HTTPException(status_code=403, detail="Only requester or admin can read job")
    return ApiEnvelope(
        data=_job_data(
            job,
            include_sensitive=True,
            actor_user_id=current.user.user_id,
            global_roles=current.global_roles,
        )
    )


@router.get("/projects/{project_id}/jobs", response_model=ApiEnvelope)
async def list_project_jobs(
    project_id: str,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    jobs = list(await session.scalars(select(Job).where(Job.project_id == project_id)))
    return ApiEnvelope(
        data=[
            _job_data(
                job,
                include_sensitive=(
                    job.submitted_by == current.user.user_id
                    or "admin" in current.global_roles
                ),
                actor_user_id=current.user.user_id,
                global_roles=current.global_roles,
            )
            for job in jobs
        ]
    )


@router.post("/jobs/{job_id}/cancel", response_model=ApiEnvelope)
async def cancel_job(
    job_id: str,
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.submitted_by != current.user.user_id and "admin" not in current.global_roles:
        raise HTTPException(status_code=403, detail="Only requester or admin can cancel job")
    if job.state not in {"queued", "running", "waiting_for_user", "blocked"}:
        raise HTTPException(status_code=409, detail="Job cannot be cancelled")
    job.cancellation_requested = True
    if job.state in {"queued", "waiting_for_user", "blocked"}:
        job.state = "cancelled"
    await record_event(
        session,
        event_type="job.cancellation_requested",
        project_id=job.project_id,
        actor_user_id=current.user.user_id,
        payload={
            "job_id": job.job_id,
            "state": job.state,
            "committed_effects": job.committed_effects_json,
        },
    )
    await session.commit()
    return ApiEnvelope(
        data=_job_data(
            job,
            include_sensitive=True,
            actor_user_id=current.user.user_id,
            global_roles=current.global_roles,
        )
    )


def _job_data(
    job: Job,
    *,
    include_sensitive: bool,
    actor_user_id: str | None = None,
    global_roles: list[str] = (),
) -> dict:
    data = {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "job_type": job.job_type,
        "state": job.state,
        "progress_percent": job.progress_percent,
        "cancellation_requested": job.cancellation_requested,
        "committed_effects": job.committed_effects_json,
        "last_committed_unit": job.last_committed_unit,
    }
    if include_sensitive:
        data["result_ref"] = job.result_ref_json
        data["error"] = job.error_json
    if actor_user_id is not None:
        data["allowed_actions"] = job_allowed_actions(
            job,
            actor_user_id=actor_user_id,
            global_roles=global_roles,
        )
    return data
