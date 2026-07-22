from arq import create_pool
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import (
    CurrentUser,
    get_current_user,
    project_role_dependency,
    require_project_roles,
)
from aac_backend.database import get_session
from aac_backend.config import get_settings
from aac_backend.models.imports import ImportRun, ImportRunItem
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import ImportDecisionSubmit, ImportStart
from aac_backend.services.event_service import record_event
from aac_backend.services.import_service import (
    apply_import_decisions,
    create_import_run,
    mark_import_failed,
    process_import_run,
)
from aac_backend.services.job_service import create_job, job_data
from aac_backend.services.presentation_policy import import_allowed_actions
from aac_backend.workers.settings_support import redis_settings

router = APIRouter(tags=["imports"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


async def _bounded_sphinx_import_payload(request: Request) -> ImportStart:
    content_type = request.headers.get("content-type", "").split(";", 1)[0].strip().lower()
    if content_type != "application/json" and not content_type.endswith("+json"):
        raise HTTPException(status_code=415, detail="Sphinx imports require JSON content")
    limit = get_settings().max_import_bytes
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            declared_size = int(content_length)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid Content-Length header") from exc
        if declared_size > limit:
            raise HTTPException(status_code=413, detail=f"Import payload exceeds {limit} bytes")
    body = bytearray()
    async for chunk in request.stream():
        body.extend(chunk)
        if len(body) > limit:
            raise HTTPException(status_code=413, detail=f"Import payload exceeds {limit} bytes")
    try:
        return ImportStart.model_validate_json(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": "The import payload is invalid.", "errors": exc.errors()},
        ) from exc


@router.post("/projects/{project_id}/imports/sphinx", response_model=ApiEnvelope)
async def start_sphinx_import(
    project_id: str,
    payload: ImportStart = Depends(_bounded_sphinx_import_payload),
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await create_import_run(
        session,
        project_id,
        payload,
        current.user.user_id,
    )
    job = await create_job(
        session,
        project_id=project_id,
        job_type="sphinx_import",
        submitted_by=current.user.user_id,
        result_ref={
            "resource_type": "ImportRun",
            "resource_id": import_run.import_run_id,
        },
    )
    await session.commit()

    queued = False
    try:
        redis = await create_pool(redis_settings())
        try:
            await redis.enqueue_job(
                "import_sphinx_job",
                job.job_id,
                import_run.import_run_id,
                _job_id=job.job_id,
            )
            queued = True
        finally:
            await redis.close()
    except Exception:
        job.error_json = {"queue_fallback": "redis_unavailable_inline_execution"}

    if not queued:
        roles = await _current_project_roles(session, current, project_id)
        job.state = "running"
        job.started_at = import_run.submitted_at
        try:
            import_run = await process_import_run(
                session,
                import_run,
                current.user.user_id,
                actor_roles=roles,
                job=job,
            )
        except Exception as exc:
            failed_run, failed_job = await mark_import_failed(
                session,
                import_run_id=import_run.import_run_id,
                job_id=job.job_id,
                actor_user_id=current.user.user_id,
                error=exc,
            )
            if failed_run is None or failed_job is None:
                raise
            return ApiEnvelope(
                status="failed",
                data={
                    "job": job_data(failed_job),
                    "import_run": _import_run_data(failed_run),
                },
            )
        job.state = (
            "waiting_for_user"
            if import_run.state == "waiting_for_user"
            else import_run.state
        )
        if import_run.state.startswith("completed"):
            job.state = "completed"
            job.progress_percent = 100
            job.completed_at = import_run.completed_at
    await session.commit()
    effective_roles = await _current_project_roles(session, current, project_id)
    return ApiEnvelope(
        status="requires_user_decision" if import_run.state == "waiting_for_user" else "accepted",
        data={
            "job": job_data(job),
            "import_run": _import_run_data(
                import_run,
                actor_user_id=current.user.user_id,
                effective_roles=effective_roles,
                global_roles=current.global_roles,
            ),
        },
    )


@router.get("/projects/{project_id}/imports", response_model=ApiEnvelope)
async def list_imports(
    project_id: str,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    runs = list(
        await session.scalars(select(ImportRun).where(ImportRun.project_id == project_id))
    )
    effective_roles = await _current_project_roles(session, current, project_id)
    return ApiEnvelope(
        data=[
            _import_run_data(
                run,
                actor_user_id=current.user.user_id,
                effective_roles=effective_roles,
                global_roles=current.global_roles,
            )
            for run in runs
        ]
    )


@router.get("/projects/{project_id}/imports/{import_run_id}", response_model=ApiEnvelope)
async def get_import(
    project_id: str,
    import_run_id: str,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    items = list(
        await session.scalars(select(ImportRunItem).where(ImportRunItem.import_run_id == import_run_id))
    )
    effective_roles = await _current_project_roles(session, current, project_id)
    data = _import_run_data(
        import_run,
        actor_user_id=current.user.user_id,
        effective_roles=effective_roles,
        global_roles=current.global_roles,
    )
    data["items"] = [_import_item_data(item) for item in items]
    return ApiEnvelope(data=data)


@router.post("/projects/{project_id}/imports/{import_run_id}/decisions", response_model=ApiEnvelope)
async def import_decisions(
    project_id: str,
    import_run_id: str,
    payload: ImportDecisionSubmit,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    if import_run.submitted_by != current.user.user_id:
        await require_project_roles(
            session=session,
            project_id=project_id,
            current=current,
            allowed_roles={"admin", "quality_engineer"},
        )
    project_roles = await _current_project_roles(session, current, project_id)
    try:
        import_run = await apply_import_decisions(
            session,
            import_run,
            [decision.model_dump() for decision in payload.decisions],
            current.user.user_id,
            actor_roles=project_roles,
        )
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(
        data=_import_run_data(
            import_run,
            actor_user_id=current.user.user_id,
            effective_roles=project_roles,
            global_roles=current.global_roles,
        )
    )


@router.post("/projects/{project_id}/imports/{import_run_id}/cancel", response_model=ApiEnvelope)
async def cancel_import(
    project_id: str,
    import_run_id: str,
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    import_run = await _get_import_or_404(session, project_id, import_run_id)
    if import_run.submitted_by != current.user.user_id and "admin" not in current.global_roles:
        raise HTTPException(status_code=403, detail="Only requester or admin can cancel import")
    if import_run.state in {"completed", "completed_with_errors", "completed_no_changes_applied", "failed", "cancelled"}:
        raise HTTPException(status_code=409, detail="Import run cannot be cancelled")
    import_run.cancellation_requested = True
    if import_run.state in {"created", "payload_received", "waiting_for_user"}:
        import_run.state = "cancelled"
    await record_event(
        session,
        event_type="import.cancellation_requested",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={
            "import_run_id": import_run.import_run_id,
            "state": import_run.state,
            "committed_effects": import_run.committed_effects_json,
        },
    )
    await session.commit()
    effective_roles = await _current_project_roles(session, current, project_id)
    return ApiEnvelope(
        data=_import_run_data(
            import_run,
            actor_user_id=current.user.user_id,
            effective_roles=effective_roles,
            global_roles=current.global_roles,
        )
    )


async def _get_import_or_404(
    session: AsyncSession,
    project_id: str,
    import_run_id: str,
) -> ImportRun:
    import_run = await session.get(ImportRun, import_run_id)
    if not import_run or import_run.project_id != project_id:
        raise HTTPException(status_code=404, detail="Import run not found")
    return import_run


def _import_run_data(
    import_run: ImportRun,
    *,
    actor_user_id: str | None = None,
    effective_roles: set[str] | list[str] = (),
    global_roles: list[str] = (),
) -> dict:
    data = {
        "import_run_id": import_run.import_run_id,
        "project_id": import_run.project_id,
        "state": import_run.state,
        "version_update_mode": import_run.version_update_mode,
        "summary": import_run.summary_json,
        "diagnostics": import_run.diagnostics_json,
        "cancellation_requested": import_run.cancellation_requested,
        "committed_effects": import_run.committed_effects_json,
        "last_committed_batch_index": import_run.last_committed_batch_index,
    }
    if actor_user_id is not None:
        data["allowed_actions"] = import_allowed_actions(
            import_run,
            actor_user_id=actor_user_id,
            effective_roles=effective_roles,
            global_roles=global_roles,
        )
    return data


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


async def _current_project_roles(
    session: AsyncSession,
    current: CurrentUser,
    project_id: str,
) -> set[str]:
    from aac_backend.services.auth_service import user_roles

    return set(await user_roles(session, current.user.user_id, project_id))
