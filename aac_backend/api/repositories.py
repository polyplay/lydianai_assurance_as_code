import json

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.baselines import Baseline
from aac_backend.models.projects import Project
from aac_backend.models.repository_integrations import RepositoryCheckRun, RepositoryConnector, RepositoryScanRun
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.repositories import (
    RepositoryApprovalPublish,
    RepositoryConnectorCreate,
    RepositoryConnectorUpdate,
    RepositoryScanStart,
)
from aac_backend.services.job_service import job_data, run_tracked_job
from aac_backend.services.event_service import record_event
from aac_backend.services.repository_integration_service import (
    create_repository_connector,
    publish_release_approval_for_baseline,
    record_github_webhook_delivery,
    repository_approval_history,
    repository_check_run_data,
    repository_connector_data,
    repository_scan_run_data,
    repository_status_data,
    run_repository_scan,
    test_repository_connector,
    update_repository_connector,
)

router = APIRouter(tags=["repository-integrations"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/projects/{project_id}/repo-connectors", response_model=ApiEnvelope)
async def list_repository_connectors(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connectors = list(
        await session.scalars(
            select(RepositoryConnector).where(
                RepositoryConnector.project_id == project_id,
                RepositoryConnector.status != "deleted",
            )
        )
    )
    return ApiEnvelope(data=[repository_connector_data(connector) for connector in connectors])


@router.post("/projects/{project_id}/repo-connectors", response_model=ApiEnvelope)
async def create_repository_connector_endpoint(
    project_id: str,
    payload: RepositoryConnectorCreate,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    await _ensure_project(session, project_id)
    try:
        connector = await create_repository_connector(
            session,
            project_id=project_id,
            payload=payload.model_dump(exclude_none=True),
            actor_user_id=current.user.user_id,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Repository connector already exists") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return ApiEnvelope(data=repository_connector_data(connector))


@router.get("/projects/{project_id}/repo-connectors/{connector_id}", response_model=ApiEnvelope)
async def get_repository_connector(
    project_id: str,
    connector_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await _connector_or_404(session, project_id, connector_id)
    return ApiEnvelope(data=repository_connector_data(connector))


@router.put("/projects/{project_id}/repo-connectors/{connector_id}", response_model=ApiEnvelope)
async def update_repository_connector_endpoint(
    project_id: str,
    connector_id: str,
    payload: RepositoryConnectorUpdate,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await _connector_or_404(session, project_id, connector_id)
    try:
        await update_repository_connector(
            session,
            connector=connector,
            payload=payload.model_dump(exclude_none=True),
            actor_user_id=current.user.user_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=repository_connector_data(connector))


@router.delete("/projects/{project_id}/repo-connectors/{connector_id}", response_model=ApiEnvelope)
async def delete_repository_connector(
    project_id: str,
    connector_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await _connector_or_404(session, project_id, connector_id)
    connector.status = "deleted"
    await record_event(
        session,
        event_type="repository_connector.deleted",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"repository_connector_id": connector.repository_connector_id},
    )
    await session.commit()
    return ApiEnvelope(data=repository_connector_data(connector))


@router.post("/projects/{project_id}/repo-connectors/{connector_id}/test", response_model=ApiEnvelope)
async def test_repository_connector_endpoint(
    project_id: str,
    connector_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await _connector_or_404(session, project_id, connector_id)
    try:
        result = await test_repository_connector(session, connector)
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail={"connected": False, "error": type(exc).__name__, "message": str(exc)},
        ) from exc
    await session.commit()
    return ApiEnvelope(data=result)


@router.get("/projects/{project_id}/repo-connectors/{connector_id}/status", response_model=ApiEnvelope)
async def repository_status_endpoint(
    project_id: str,
    connector_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await _connector_or_404(session, project_id, connector_id)
    try:
        result = await repository_status_data(session, connector)
    except Exception as exc:
        raise HTTPException(
            status_code=409,
            detail={"reachable": False, "error": type(exc).__name__, "message": str(exc)},
        ) from exc
    await session.commit()
    return ApiEnvelope(data=result)


@router.post("/projects/{project_id}/repo-connectors/{connector_id}/scan", response_model=ApiEnvelope)
async def start_repository_scan(
    project_id: str,
    connector_id: str,
    payload: RepositoryScanStart,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    await _connector_or_404(session, project_id, connector_id)

    async def operation(job):
        return await run_repository_scan(
            session,
            project_id=project_id,
            connector_id=connector_id,
            actor_user_id=current.user.user_id,
            payload=payload.model_dump(exclude_none=True),
            job=job,
        )

    try:
        job, scan_run = await run_tracked_job(
            session,
            project_id=project_id,
            job_type="repository_scan",
            submitted_by=current.user.user_id,
            operation=operation,
            arq_job_name="repository_scan_job",
            arq_args=(project_id, connector_id, current.user.user_id, payload.model_dump(exclude_none=True)),
        )
    except Exception as exc:
        await session.commit()
        raise HTTPException(
            status_code=409,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    await session.commit()
    return ApiEnvelope(
        status="accepted",
        data={
            "job": job_data(job),
            "scan_run": repository_scan_run_data(scan_run) if scan_run else None,
        },
    )


@router.get(
    "/projects/{project_id}/repo-connectors/{connector_id}/scans/{scan_id}",
    response_model=ApiEnvelope,
)
async def get_repository_scan(
    project_id: str,
    connector_id: str,
    scan_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    scan_run = await session.get(RepositoryScanRun, scan_id)
    if (
        not scan_run
        or scan_run.project_id != project_id
        or scan_run.repository_connector_id != connector_id
    ):
        raise HTTPException(status_code=404, detail="Repository scan not found")
    return ApiEnvelope(data=repository_scan_run_data(scan_run))


@router.get("/projects/{project_id}/baselines/{baseline_id}/repository-approvals", response_model=ApiEnvelope)
async def repository_approvals_for_baseline(
    project_id: str,
    baseline_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    checks = await repository_approval_history(session, project_id=project_id, baseline_id=baseline_id)
    return ApiEnvelope(data=[repository_check_run_data(check) for check in checks])


@router.post("/projects/{project_id}/baselines/{baseline_id}/repository-approvals", response_model=ApiEnvelope)
async def publish_repository_approval_for_baseline_endpoint(
    project_id: str,
    baseline_id: str,
    payload: RepositoryApprovalPublish,
    current: CurrentUser = Depends(project_role_dependency("admin", "quality_engineer", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    baseline = await session.get(Baseline, baseline_id)
    if not baseline or baseline.project_id != project_id or payload.baseline_id != baseline_id:
        raise HTTPException(status_code=404, detail="Baseline not found")
    try:
        checks = await publish_release_approval_for_baseline(
            session,
            baseline=baseline,
            actor_user_id=current.user.user_id,
            details_url=payload.details_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=[repository_check_run_data(check) for check in checks])


@router.get("/projects/{project_id}/repo-checks/{check_id}", response_model=ApiEnvelope)
async def get_repository_check(
    project_id: str,
    check_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    check = await session.get(RepositoryCheckRun, check_id)
    if not check or check.project_id != project_id:
        raise HTTPException(status_code=404, detail="Repository check not found")
    return ApiEnvelope(data=repository_check_run_data(check))


@router.post("/integrations/github/webhook/{connector_id}", response_model=ApiEnvelope)
async def github_webhook(
    connector_id: str,
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    connector = await session.get(RepositoryConnector, connector_id)
    if not connector or connector.status != "active":
        raise HTTPException(status_code=404, detail="Repository connector not found")
    body = await request.body()
    event_type = request.headers.get("X-GitHub-Event", "")
    delivery_id = request.headers.get("X-GitHub-Delivery", hashlib_fallback(body))
    signature = request.headers.get("X-Hub-Signature-256")
    try:
        delivery, scan_payload = await record_github_webhook_delivery(
            session,
            connector=connector,
            event_type=event_type,
            delivery_id=delivery_id,
            signature_header=signature,
            body=body,
        )
    except json.JSONDecodeError as exc:
        await session.commit()
        raise HTTPException(status_code=409, detail="Webhook payload is not valid JSON") from exc
    if not delivery.signature_valid:
        await session.commit()
        raise HTTPException(status_code=401, detail="Invalid GitHub webhook signature")
    if scan_payload is None:
        await session.commit()
        return ApiEnvelope(status="accepted", data={"delivery_id": delivery.repository_webhook_delivery_id, "ignored": True})

    async def operation(job):
        return await run_repository_scan(
            session,
            project_id=connector.project_id,
            connector_id=connector.repository_connector_id,
            actor_user_id=None,
            payload=scan_payload,
            job=job,
        )

    try:
        job, scan_run = await run_tracked_job(
            session,
            project_id=connector.project_id,
            job_type="repository_scan",
            submitted_by=None,
            operation=operation,
            arq_job_name="repository_scan_job",
            arq_args=(connector.project_id, connector.repository_connector_id, None, scan_payload),
        )
    except Exception as exc:
        delivery.state = "failed"
        await session.commit()
        raise HTTPException(
            status_code=409,
            detail={"error": type(exc).__name__, "message": str(exc)},
        ) from exc
    delivery.state = "queued" if scan_run is None else "processed"
    delivery.processed_at = None if scan_run is None else scan_run.completed_at
    await session.commit()
    return ApiEnvelope(
        status="accepted",
        data={
            "delivery_id": delivery.repository_webhook_delivery_id,
            "job": job_data(job),
            "scan_run": repository_scan_run_data(scan_run) if scan_run else None,
        },
    )


async def _ensure_project(session: AsyncSession, project_id: str) -> Project:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


async def _connector_or_404(
    session: AsyncSession,
    project_id: str,
    connector_id: str,
) -> RepositoryConnector:
    connector = await session.get(RepositoryConnector, connector_id)
    if not connector or connector.project_id != project_id or connector.status == "deleted":
        raise HTTPException(status_code=404, detail="Repository connector not found")
    return connector


def hashlib_fallback(body: bytes) -> str:
    import hashlib

    return hashlib.sha256(body).hexdigest()
