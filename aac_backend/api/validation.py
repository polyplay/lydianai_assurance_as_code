from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.validation import ValidationIssue
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.event_service import record_event
from aac_backend.services.job_service import job_data, run_tracked_job
from aac_backend.services.validation_service import run_validation

router = APIRouter(tags=["validation"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.post("/projects/{project_id}/validation/run", response_model=ApiEnvelope)
async def validation_run(
    project_id: str,
    payload: dict | None = None,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    scope = payload or {"type": "project", "mode": "baseline"}

    async def operation(job):
        run = await run_validation(session, project_id, current.user.user_id, scope=scope)
        job.result_ref_json = {"resource_type": "ValidationRun", "resource_id": run.validation_run_id}
        return run

    job, run = await run_tracked_job(
        session,
        project_id=project_id,
        job_type="validation_run",
        submitted_by=current.user.user_id,
        operation=operation,
        arq_job_name="validation_job",
        arq_args=(project_id, current.user.user_id, scope),
    )
    await session.commit()
    if run is None:
        return ApiEnvelope(status="accepted", data={"job": job_data(job)})
    return ApiEnvelope(
        status="accepted",
        data={"job": job_data(job), "validation_run_id": run.validation_run_id, "summary": run.summary_json},
    )


@router.get("/projects/{project_id}/validation/issues", response_model=ApiEnvelope)
async def validation_issues(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    issues = list(
        await session.scalars(select(ValidationIssue).where(ValidationIssue.project_id == project_id))
    )
    return ApiEnvelope(
        data=[
            _issue_data(issue)
            for issue in issues
        ]
    )


@router.get("/projects/{project_id}/validation/status", response_model=ApiEnvelope)
async def validation_status(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    issues = list(
        await session.scalars(select(ValidationIssue).where(ValidationIssue.project_id == project_id))
    )
    open_issues = [issue for issue in issues if issue.status == "open"]
    return ApiEnvelope(
        data={
            "project_id": project_id,
            "issue_count": len(issues),
            "open_issue_count": len(open_issues),
            "critical_open_issue_count": len(
                [issue for issue in open_issues if issue.severity == "critical"]
            ),
        }
    )


@router.get("/projects/{project_id}/validation/issues/{issue_id}", response_model=ApiEnvelope)
async def get_issue(
    project_id: str,
    issue_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    issue = await _get_issue_or_404(session, project_id, issue_id)
    return ApiEnvelope(data=_issue_data(issue))


@router.post("/projects/{project_id}/validation/issues/{issue_id}/suppress", response_model=ApiEnvelope)
async def suppress_issue(
    project_id: str,
    issue_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    issue = await _get_issue_or_404(session, project_id, issue_id)
    issue.status = "suppressed"
    issue.suppressed_by = current.user.user_id
    issue.suppression_reason = payload.get("reason", "suppressed by admin")
    issue.resolved_at = datetime.now(UTC)
    await record_event(
        session,
        event_type="validation.issue_suppressed",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"issue_id": issue_id, "reason": issue.suppression_reason},
    )
    await session.commit()
    return ApiEnvelope(data=_issue_data(issue))


@router.post("/projects/{project_id}/validation/issues/{issue_id}/reopen", response_model=ApiEnvelope)
async def reopen_issue(
    project_id: str,
    issue_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    issue = await _get_issue_or_404(session, project_id, issue_id)
    issue.status = "open"
    issue.suppressed_by = None
    issue.suppression_reason = None
    issue.resolved_at = None
    await record_event(
        session,
        event_type="validation.issue_reopened",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        payload={"issue_id": issue_id},
    )
    await session.commit()
    return ApiEnvelope(data=_issue_data(issue))


@router.get("/projects/{project_id}/rules", response_model=ApiEnvelope)
async def rules(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
) -> ApiEnvelope:
    return ApiEnvelope(data=[rule.__dict__ for rule in RULE_CATALOG.values()])


async def _get_issue_or_404(
    session: AsyncSession,
    project_id: str,
    issue_id: str,
) -> ValidationIssue:
    issue = await session.get(ValidationIssue, issue_id)
    if not issue or issue.project_id != project_id:
        raise HTTPException(status_code=404, detail="Validation issue not found")
    return issue


def _issue_data(issue: ValidationIssue) -> dict:
    return {
        "validation_issue_id": issue.validation_issue_id,
        "rule_id": issue.rule_id,
        "severity": issue.severity,
        "status": issue.status,
        "message": issue.message,
        "affected_artefacts": issue.affected_artefact_ids_json,
        "affected_relationships": issue.affected_relationship_ids_json,
        "blocking_contexts": issue.blocking_contexts_json,
        "remediation_hint": issue.remediation_hint,
    }
