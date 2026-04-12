from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.imports import ImportRun, ImportRunItem
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import ImportStart
from aac_backend.services.import_service import apply_import_decisions, import_sphinx_needs
from aac_backend.services.job_service import job_data, run_tracked_job

router = APIRouter(tags=["imports"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.post("/projects/{project_id}/imports/sphinx", response_model=ApiEnvelope)
async def start_sphinx_import(
    project_id: str,
    payload: ImportStart,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    async def operation(job):
        import_run = await import_sphinx_needs(session, project_id, payload, current.user.user_id)
        job.result_ref_json = {"resource_type": "ImportRun", "resource_id": import_run.import_run_id}
        if import_run.state == "waiting_for_user":
            job.state = "waiting_for_user"
        return import_run

    job, import_run = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="sphinx_import",
        submitted_by=current.user.user_id,
        operation=operation,
    )
    await session.commit()
    return ApiEnvelope(
        status="requires_user_decision" if import_run.state == "waiting_for_user" else "accepted",
        data={"job": job_data(job), "import_run": _import_run_data(import_run)},
    )


@router.get("/projects/{project_id}/imports", response_model=ApiEnvelope)
async def list_imports(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    runs = list(
        await session.scalars(select(ImportRun).where(ImportRun.project_id == project_id))
    )
    return ApiEnvelope(data=[_import_run_data(run) for run in runs])


@router.get("/projects/{project_id}/imports/{import_run_id}", response_model=ApiEnvelope)
async def get_import(
    project_id: str,
    import_run_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    items = list(
        await session.scalars(select(ImportRunItem).where(ImportRunItem.import_run_id == import_run_id))
    )
    data = _import_run_data(import_run)
    data["items"] = [_import_item_data(item) for item in items]
    return ApiEnvelope(data=data)


@router.post("/projects/{project_id}/imports/{import_run_id}/decisions", response_model=ApiEnvelope)
async def import_decisions(
    project_id: str,
    import_run_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    import_run = await apply_import_decisions(
        session,
        import_run,
        payload.get("decisions", []),
        current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=_import_run_data(import_run))


@router.post("/projects/{project_id}/imports/{import_run_id}/cancel", response_model=ApiEnvelope)
async def cancel_import(
    project_id: str,
    import_run_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    if import_run.state not in {"created", "parsed", "waiting_for_user"}:
        raise HTTPException(status_code=409, detail="Import run cannot be cancelled")
    import_run.state = "cancelled"
    await session.commit()
    return ApiEnvelope(data=_import_run_data(import_run))


async def _get_import_or_404(
    session: AsyncSession,
    project_id: str,
    import_run_id: str,
) -> ImportRun:
    import_run = await session.get(ImportRun, import_run_id)
    if not import_run or import_run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Import run not found")
    return import_run


def _import_run_data(import_run: ImportRun) -> dict:
    return {
        "import_run_id": import_run.import_run_id,
        "project_id": import_run.project_id,
        "state": import_run.state,
        "version_update_mode": import_run.version_update_mode,
        "summary": import_run.summary_json,
        "diagnostics": import_run.diagnostics_json,
    }


def _import_item_data(item: ImportRunItem) -> dict:
    return {
        "import_run_item_id": item.import_run_item_id,
        "source_object_id": item.source_object_id,
        "source_document": item.source_document,
        "artefact_type": item.artefact_type,
        "artefact_id": item.artefact_id,
        "detected_change_type": item.detected_change_type,
        "decision_status": item.decision_status,
        "current_revision_id": item.current_revision_id,
        "new_revision_id": item.new_revision_id,
    }
