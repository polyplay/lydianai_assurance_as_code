from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser
from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import Baseline
from aac_backend.models.imports import ImportRun
from aac_backend.models.impact import SuspectState
from aac_backend.models.jobs import Job, ProjectUpdateLock
from aac_backend.models.projects import Project
from aac_backend.models.validation import ValidationIssue
from aac_backend.services.auth_service import user_roles
from aac_backend.services.presentation_policy import (
    ACTIVE_JOB_STATES,
    baseline_allowed_actions,
    project_capabilities,
)


async def workspace_projection(
    session: AsyncSession,
    *,
    project_id: str,
    current: CurrentUser,
) -> dict:
    project = await session.get(Project, project_id)
    if project is None:
        raise ValueError("Project not found")

    effective_roles = await user_roles(session, current.user.user_id, project_id)
    global_roles = sorted(set(current.global_roles))
    project_roles = sorted(set(effective_roles) - set(global_roles))

    artefacts = list(
        await session.scalars(
            select(Artefact).where(
                Artefact.project_id == project_id,
                Artefact.deleted_at.is_(None),
            )
        )
    )
    relationships = list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
    )
    imports = list(
        await session.scalars(select(ImportRun).where(ImportRun.project_id == project_id))
    )
    issues = list(
        await session.scalars(
            select(ValidationIssue).where(ValidationIssue.project_id == project_id)
        )
    )
    suspects = list(
        await session.scalars(select(SuspectState).where(SuspectState.project_id == project_id))
    )
    jobs = list(await session.scalars(select(Job).where(Job.project_id == project_id)))
    baselines = list(
        await session.scalars(select(Baseline).where(Baseline.project_id == project_id))
    )
    project_locked = await session.get(ProjectUpdateLock, project_id) is not None

    open_issues = [issue for issue in issues if issue.status == "open"]
    blocking_issues = [
        issue
        for issue in open_issues
        if set(issue.blocking_contexts_json).intersection({"baseline", "release_gate"})
    ]
    open_suspects = [suspect for suspect in suspects if suspect.status == "open"]
    active_jobs = [job for job in jobs if job.state in ACTIVE_JOB_STATES]
    waiting_imports = [run for run in imports if run.state == "waiting_for_user"]
    active_imports = [
        run
        for run in imports
        if run.state
        not in {
            "completed",
            "completed_with_errors",
            "completed_no_changes_applied",
            "failed",
            "cancelled",
        }
    ]
    latest_baseline = _latest_baseline(baselines)
    latest_baseline_data = (
        {
            "baseline_id": latest_baseline.baseline_id,
            "name": latest_baseline.name,
            "state": latest_baseline.state,
            "release_gate_status": latest_baseline.release_gate_status,
            "allowed_actions": baseline_allowed_actions(
                latest_baseline,
                roles=effective_roles,
            ),
        }
        if latest_baseline
        else None
    )
    readiness = _release_readiness(
        latest_baseline_data=latest_baseline_data,
        blocking_issue_count=len(blocking_issues),
        open_suspect_count=len(open_suspects),
        project_locked=project_locked,
    )
    actionable_work = _actionable_work(
        waiting_import_count=len(waiting_imports),
        blocking_issue_count=len(blocking_issues),
        open_issue_count=len(open_issues),
        open_suspect_count=len(open_suspects),
        active_job_count=len(active_jobs),
        readiness=readiness,
    )

    return {
        "project": {
            "project_id": project.project_id,
            "project_key": project.project_key,
            "name": project.name,
            "description": project.description,
            "status": project.status,
            "active_profile_id": project.active_profile_id,
            "locked": project_locked,
        },
        "actor": {
            "user_id": current.user.user_id,
            "username": current.user.username,
            "display_name": current.user.display_name,
            "global_roles": global_roles,
            "project_roles": project_roles,
            "effective_roles": effective_roles,
        },
        "capabilities": project_capabilities(effective_roles),
        "summary": {
            "artefacts": {
                "total": len(artefacts),
                "by_status": _count_by(artefacts, "status"),
            },
            "relationships": {"total": len(relationships)},
            "imports": {
                "total": len(imports),
                "active": len(active_imports),
                "waiting_for_user": len(waiting_imports),
            },
            "validation": {
                "open": len(open_issues),
                "critical_open": len(
                    [issue for issue in open_issues if issue.severity == "critical"]
                ),
                "release_blocking": len(blocking_issues),
            },
            "suspects": {"open": len(open_suspects)},
            "jobs": {
                "active": len(active_jobs),
                "mine_active": len(
                    [
                        job
                        for job in active_jobs
                        if job.submitted_by == current.user.user_id
                    ]
                ),
            },
            "baselines": {
                "total": len(baselines),
                "latest": latest_baseline_data,
            },
        },
        "release_readiness": readiness,
        "actionable_work": actionable_work,
    }


def _latest_baseline(baselines: list[Baseline]) -> Baseline | None:
    if not baselines:
        return None
    return max(
        baselines,
        key=lambda baseline: (
            baseline.created_at is not None,
            baseline.created_at,
            baseline.baseline_id,
        ),
    )


def _count_by(items: list, attribute: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in items:
        value = str(getattr(item, attribute))
        counts[value] = counts.get(value, 0) + 1
    return counts


def _release_readiness(
    *,
    latest_baseline_data: dict | None,
    blocking_issue_count: int,
    open_suspect_count: int,
    project_locked: bool,
) -> dict:
    blockers = []
    if project_locked:
        blockers.append({"kind": "project_lock", "count": 1})
    if blocking_issue_count:
        blockers.append({"kind": "validation_issue", "count": blocking_issue_count})
    if open_suspect_count:
        blockers.append({"kind": "suspect_state", "count": open_suspect_count})

    if project_locked:
        state = "project_locked"
    elif blockers:
        state = "blocked"
    elif latest_baseline_data is None:
        state = "no_baseline"
    elif latest_baseline_data["state"] == "released":
        state = "released"
    elif "release" in latest_baseline_data["allowed_actions"]:
        state = "ready_to_release"
    elif "approve" in latest_baseline_data["allowed_actions"]:
        state = "ready_for_approval"
    elif "run_release_gate" in latest_baseline_data["allowed_actions"]:
        state = "ready_for_gate"
    else:
        state = "in_progress"
    return {
        "state": state,
        "ready": state in {"ready_to_release", "released"},
        "blockers": blockers,
    }


def _actionable_work(
    *,
    waiting_import_count: int,
    blocking_issue_count: int,
    open_issue_count: int,
    open_suspect_count: int,
    active_job_count: int,
    readiness: dict,
) -> list[dict]:
    work: list[dict] = []
    rows = [
        (
            waiting_import_count,
            "import_decision",
            "Import decisions",
            "#/imports",
            "warning",
        ),
        (
            blocking_issue_count,
            "release_blocker",
            "Release-blocking validation issues",
            "#/validation",
            "critical",
        ),
        (
            max(open_issue_count - blocking_issue_count, 0),
            "validation_issue",
            "Other open validation issues",
            "#/validation",
            "warning",
        ),
        (
            open_suspect_count,
            "suspect_state",
            "Open suspect states",
            "#/impact",
            "critical",
        ),
        (
            active_job_count,
            "active_job",
            "Active background jobs",
            "#/jobs",
            "info",
        ),
    ]
    for count, kind, label, route, severity in rows:
        if count:
            work.append(
                {
                    "kind": kind,
                    "count": count,
                    "label": label,
                    "route": route,
                    "severity": severity,
                }
            )
    if not work:
        work.append(
            {
                "kind": "release_readiness",
                "count": 1,
                "label": readiness["state"].replace("_", " ").title(),
                "route": "#/release",
                "severity": "success" if readiness["ready"] else "info",
            }
        )
    return work
