from __future__ import annotations

from collections.abc import Collection

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import Baseline
from aac_backend.models.imports import ImportRun
from aac_backend.models.impact import SuspectState
from aac_backend.models.jobs import Job
from aac_backend.models.validation import ValidationIssue


ACTIVE_JOB_STATES = {"queued", "running", "waiting_for_user", "blocked"}
TERMINAL_IMPORT_STATES = {
    "completed",
    "completed_with_errors",
    "completed_no_changes_applied",
    "failed",
    "cancelled",
}


def project_capabilities(roles: Collection[str]) -> dict[str, bool]:
    role_set = set(roles)
    admin = "admin" in role_set
    lead = "project_lead" in role_set
    quality = "quality_engineer" in role_set
    member = bool(role_set.intersection({"admin", "project_lead", "quality_engineer", "user"}))
    return {
        "project.read": member,
        "project.configure": admin,
        "team.read": member,
        "team.manage": admin or lead,
        "artefact.read": member,
        "artefact.create": member,
        "relationship.read": member,
        "relationship.create": member,
        "import.read": member,
        "import.start": member,
        "validation.read": member,
        "validation.run": member,
        "validation.manage_issues": admin,
        "trace.read": member,
        "impact.run": member,
        "suspect.clear": admin or lead or quality,
        "baseline.read": member,
        "baseline.create": admin or lead,
        "release_gate.run": member,
        "baseline.approve": admin or lead,
        "baseline.release": admin or quality,
        "report.read": member,
        "report.generate": member,
        "report.delete": admin or quality,
        "job.read": member,
        "repository.read": member,
        "repository.manage": admin,
        "repository.scan": admin or lead,
        "repository.publish_approval": admin or lead or quality,
        "audit.read": admin or lead or quality,
        "schema.manage": admin,
    }


def artefact_allowed_actions(
    artefact: Artefact,
    *,
    actor_user_id: str,
    roles: Collection[str],
) -> list[str]:
    role_set = set(roles)
    admin = "admin" in role_set
    lead = "project_lead" in role_set
    quality = "quality_engineer" in role_set
    actions: list[str] = []
    if artefact.status != "obsolete" and (
        artefact.status != "released" or admin or quality
    ):
        actions.append("edit")
    if artefact.status == "draft" and (
        artefact.owner_user_id == actor_user_id or admin or quality
    ):
        actions.append("submit_for_review")
    if artefact.status == "under_review" and (admin or lead or quality):
        actions.extend(["mark_reviewed", "reject"])
    if artefact.status == "reviewed" and (admin or lead or quality):
        actions.append("reject")
    if artefact.status == "reviewed" and (admin or lead):
        actions.append("approve")
    if artefact.status == "approved" and (admin or quality):
        actions.append("release")
    if artefact.status != "obsolete" and admin:
        actions.append("delete")
    return actions


def relationship_allowed_actions(
    relationship: Relationship,
    *,
    roles: Collection[str],
) -> list[str]:
    if relationship.status == "obsolete":
        return []
    actions = ["edit"]
    if "admin" in roles:
        actions.append("delete")
    return actions


def baseline_allowed_actions(
    baseline: Baseline,
    *,
    roles: Collection[str],
) -> list[str]:
    role_set = set(roles)
    admin = "admin" in role_set
    lead = "project_lead" in role_set
    quality = "quality_engineer" in role_set
    actions: list[str] = []
    if baseline.state == "created":
        actions.append("run_release_gate")
    if (
        baseline.state == "created"
        and baseline.release_gate_status == "passed"
        and (admin or lead)
    ):
        actions.append("approve")
    if (
        baseline.state == "approved"
        and baseline.release_gate_status == "passed"
        and (admin or quality)
    ):
        actions.append("release")
    if baseline.state in {"requested", "creating_snapshot"} and (admin or lead):
        actions.append("cancel")
    if baseline.state == "released" and (admin or lead or quality):
        actions.append("publish_repository_approval")
    if baseline.state != "obsolete" and admin:
        actions.append("obsolete")
    return actions


def import_allowed_actions(
    import_run: ImportRun,
    *,
    actor_user_id: str,
    effective_roles: Collection[str],
    global_roles: Collection[str],
) -> list[str]:
    actions: list[str] = []
    if import_run.state == "waiting_for_user" and (
        import_run.submitted_by == actor_user_id
        or bool(set(effective_roles).intersection({"admin", "quality_engineer"}))
    ):
        actions.append("submit_decisions")
    if import_run.state not in TERMINAL_IMPORT_STATES and (
        import_run.submitted_by == actor_user_id or "admin" in global_roles
    ):
        actions.append("cancel")
    return actions


def job_allowed_actions(
    job: Job,
    *,
    actor_user_id: str,
    global_roles: Collection[str],
) -> list[str]:
    if job.state in ACTIVE_JOB_STATES and (
        job.submitted_by == actor_user_id or "admin" in global_roles
    ):
        return ["cancel"]
    return []


def validation_issue_allowed_actions(
    issue: ValidationIssue,
    *,
    roles: Collection[str],
) -> list[str]:
    if "admin" not in roles:
        return []
    if issue.status == "open":
        return ["suppress"]
    if issue.status == "suppressed":
        return ["reopen"]
    return []


def suspect_allowed_actions(
    suspect: SuspectState,
    *,
    roles: Collection[str],
) -> list[str]:
    if suspect.status == "open" and set(roles).intersection(
        {"admin", "project_lead", "quality_engineer"}
    ):
        return ["clear"]
    return []
