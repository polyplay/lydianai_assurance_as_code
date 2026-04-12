from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, get_current_user, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.jobs import Job
from aac_backend.schemas.common import ApiEnvelope

router = APIRouter(tags=["jobs"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/jobs/{job_id}", response_model=ApiEnvelope)
async def get_job(
    job_id: str,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    job = await session.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return ApiEnvelope(data=_job_data(job))


@router.get("/projects/{project_id}/jobs", response_model=ApiEnvelope)
async def list_project_jobs(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    jobs = list(await session.scalars(select(Job).where(Job.project_id == project_id)))
    return ApiEnvelope(data=[_job_data(job) for job in jobs])


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
    job.state = "cancelled"
    await session.commit()
    return ApiEnvelope(data=_job_data(job))


def _job_data(job: Job) -> dict:
    return {
        "job_id": job.job_id,
        "project_id": job.project_id,
        "job_type": job.job_type,
        "state": job.state,
        "progress_percent": job.progress_percent,
        "result_ref": job.result_ref_json,
        "error": job.error_json,
    }
