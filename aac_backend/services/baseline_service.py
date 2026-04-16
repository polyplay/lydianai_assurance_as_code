from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.database import AsyncSessionLocal
from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import (
    Baseline,
    BaselineArtefactRevision,
    BaselineRelationshipRevision,
    ReleaseGateResult,
)
from aac_backend.models.jobs import Job, ProjectUpdateLock
from aac_backend.models.projects import ProjectConfiguration
from aac_backend.models.validation import ValidationIssue
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.schemas.domain import BaselineCreate
from aac_backend.services.event_service import record_event
from aac_backend.services.impact_service import open_suspects_for_project
from aac_backend.services.validation_service import run_validation


async def create_baseline(
    session: AsyncSession,
    project_id: str,
    data: BaselineCreate,
    actor_user_id: str,
    job: Job | None = None,
) -> Baseline:
    if job is None:
        job = Job(
            project_id=project_id,
            job_type="baseline_create",
            state="running",
            submitted_by=actor_user_id,
            submitted_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        session.add(job)
        await session.flush()
    await session.flush()
    await session.commit()
    await _acquire_project_update_lock(project_id, job.job_id, actor_user_id)
    try:
        validation_run = await run_validation(
            session,
            project_id,
            actor_user_id,
            scope={"type": "project", "trigger": "baseline_eligibility"},
        )
        open_issues = list(
            await session.scalars(
                select(ValidationIssue).where(
                    ValidationIssue.project_id == project_id,
                    ValidationIssue.status == "open",
                )
            )
        )
        blocking_issues = [
            issue for issue in open_issues if "baseline" in issue.blocking_contexts_json
        ]
        open_suspects = await open_suspects_for_project(session, project_id)
        eligibility_result = {
            "validation_run_id": validation_run.validation_run_id,
            "passed": not blocking_issues and not open_suspects,
            "blocking_issue_ids": [issue.validation_issue_id for issue in blocking_issues],
            "open_suspect_state_ids": [suspect.suspect_state_id for suspect in open_suspects],
            "blocking_issue_count": len(blocking_issues),
            "open_suspect_count": len(open_suspects),
        }
        if blocking_issues or open_suspects:
            job.state = "failed"
            job.completed_at = datetime.now(UTC)
            job.error_json = eligibility_result
            raise ValueError("baseline eligibility failed")

        baseline = Baseline(
            project_id=project_id,
            name=data.name,
            description=data.description,
            state="creating_snapshot",
            created_by=actor_user_id,
            created_at=datetime.now(UTC),
            profile_id=data.profile_id,
            eligibility_result_json=eligibility_result,
        )
        session.add(baseline)
        await session.flush()

        artefacts = list(
            await session.scalars(
                select(Artefact).where(Artefact.project_id == project_id, Artefact.deleted_at.is_(None))
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
        for artefact in artefacts:
            if artefact.current_revision_id:
                session.add(
                    BaselineArtefactRevision(
                        baseline_id=baseline.baseline_id,
                        artefact_id=artefact.artefact_id,
                        artefact_revision_id=artefact.current_revision_id,
                        artefact_type=artefact.artefact_type,
                    )
                )
        for relationship in relationships:
            if relationship.current_revision_id:
                session.add(
                    BaselineRelationshipRevision(
                        baseline_id=baseline.baseline_id,
                        relationship_id=relationship.relationship_id,
                        relationship_revision_id=relationship.current_revision_id,
                        relationship_type=relationship.relationship_type,
                    )
                )
        baseline.state = "created"
        baseline.summary_json = {
            "artefact_count": len(artefacts),
            "relationship_count": len(relationships),
            "validation_summary": validation_run.summary_json,
            "suspect_summary": {"open_suspect_count": len(open_suspects)},
            "release_gate_status": baseline.release_gate_status,
        }
        job.state = "completed"
        job.completed_at = datetime.now(UTC)
        await record_event(
            session,
            event_type="baseline.created",
            project_id=project_id,
            actor_user_id=actor_user_id,
            payload=baseline.summary_json,
        )
    except SQLAlchemyError:
        await session.rollback()
        await _release_project_update_lock_in_new_session(project_id)
        raise
    except Exception:
        await _release_project_update_lock_in_new_session(project_id)
        raise
    else:
        await _release_project_update_lock_in_new_session(project_id)
        return baseline


async def run_release_gate(
    session: AsyncSession,
    project_id: str,
    baseline: Baseline,
    actor_user_id: str,
) -> ReleaseGateResult:
    existing_count = await session.scalar(
        select(ReleaseGateResult.evaluation_number).where(
            ReleaseGateResult.baseline_id == baseline.baseline_id
        ).order_by(ReleaseGateResult.evaluation_number.desc())
    )
    evaluation_number = int(existing_count or 0) + 1
    validation_run = await run_validation(
        session,
        project_id,
        actor_user_id,
        scope={
            "type": "baseline",
            "trigger": "release_gate",
            "baseline_id": baseline.baseline_id,
        },
    )
    issues = list(
        await session.scalars(
            select(ValidationIssue).where(
                ValidationIssue.project_id == project_id,
                ValidationIssue.status == "open",
            )
        )
    )
    baseline_artefact_ids = await _baseline_artefact_ids(session, baseline.baseline_id)
    scoped_issues = [
        issue
        for issue in issues
        if _issue_applies_to_baseline(issue, baseline_artefact_ids)
    ]
    open_suspects = await open_suspects_for_project(session, project_id)
    blocking = [
        {
            "issue_id": issue.validation_issue_id,
            "rule_id": issue.rule_id,
            "severity": issue.severity,
            "summary": issue.message,
        }
        for issue in scoped_issues
        if "release_gate" in issue.blocking_contexts_json
    ]
    passed = not blocking
    suspect_blocks = [
        {
            "suspect_state_id": suspect.suspect_state_id,
            "artefact_id": suspect.artefact_id,
            "trigger_artefact_id": suspect.trigger_artefact_id,
        }
        for suspect in open_suspects
    ]
    passed = passed and not suspect_blocks
    validation_policy = await _validation_policy_for_project(session, project_id)
    evaluated_rules_count = _rule_count_for_mode("release_gate", validation_policy)
    blocking_rule_count = len({issue["rule_id"] for issue in blocking})
    result = ReleaseGateResult(
        project_id=project_id,
        baseline_id=baseline.baseline_id,
        evaluation_number=evaluation_number,
        triggered_by=actor_user_id,
        status="passed" if passed else "failed",
        result="pass" if passed else "fail",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        evaluated_rules_count=evaluated_rules_count,
        passed_rules_count=max(evaluated_rules_count - blocking_rule_count, 0),
        blocking_issues_json=blocking,
        open_suspect_states_json=suspect_blocks,
    )
    session.add(result)
    baseline.release_gate_status = result.status
    await record_event(
        session,
        event_type="release_gate.completed",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload={
            "result": result.result,
            "blocking_issue_count": len(blocking),
            "validation_run_id": validation_run.validation_run_id,
        },
    )
    return result


async def _baseline_artefact_ids(session: AsyncSession, baseline_id: str) -> set[str]:
    return set(
        await session.scalars(
            select(BaselineArtefactRevision.artefact_id).where(
                BaselineArtefactRevision.baseline_id == baseline_id
            )
        )
    )


def _issue_applies_to_baseline(issue: ValidationIssue, baseline_artefact_ids: set[str]) -> bool:
    affected = set(issue.affected_artefact_ids_json or [])
    return not affected or bool(affected & baseline_artefact_ids)


async def _release_project_update_lock(session: AsyncSession, project_id: str) -> None:
    lock = await session.get(ProjectUpdateLock, project_id)
    if lock:
        await session.delete(lock)
        await session.flush()


async def _acquire_project_update_lock(project_id: str, job_id: str, actor_user_id: str) -> None:
    async with AsyncSessionLocal() as lock_session:
        lock_session.add(
            ProjectUpdateLock(
                project_id=project_id,
                lock_owner_job_id=job_id,
                acquired_by=actor_user_id,
                acquired_at=datetime.now(UTC),
            )
        )
        try:
            await lock_session.commit()
        except IntegrityError as exc:
            await lock_session.rollback()
            raise ValueError("project update lock is already active") from exc


async def _release_project_update_lock_in_new_session(project_id: str) -> None:
    async with AsyncSessionLocal() as cleanup_session:
        lock = await cleanup_session.get(ProjectUpdateLock, project_id)
        if lock:
            await cleanup_session.delete(lock)
            await cleanup_session.commit()


async def _validation_policy_for_project(session: AsyncSession, project_id: str) -> dict:
    config = await session.scalar(
        select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
    )
    return config.validation_policy_json if config else {}


def _rule_count_for_mode(mode: str, validation_policy: dict | None = None) -> int:
    return sum(
        1
        for rule_id, rule in RULE_CATALOG.items()
        if mode in rule.execution_modes and not _rule_disabled(rule_id, validation_policy)
    )


def _rule_disabled(rule_id: str, validation_policy: dict | None) -> bool:
    rule_cfg = ((validation_policy or {}).get("rules") or {}).get(rule_id, {})
    return rule_cfg.get("enabled") is False or rule_cfg.get("severity") == "disabled"


async def approve_baseline(
    session: AsyncSession,
    baseline: Baseline,
    actor_user_id: str,
) -> Baseline:
    if baseline.state != "created":
        raise ValueError("baseline must be created before approval")
    if baseline.release_gate_status != "passed":
        raise ValueError("baseline release gate must pass before approval")
    baseline.state = "approved"
    baseline.approved_by = actor_user_id
    baseline.approved_at = datetime.now(UTC)
    await record_event(
        session,
        event_type="baseline.approved",
        project_id=baseline.project_id,
        actor_user_id=actor_user_id,
        payload={"baseline_id": baseline.baseline_id},
    )
    return baseline


async def release_baseline(
    session: AsyncSession,
    baseline: Baseline,
    actor_user_id: str,
) -> Baseline:
    if baseline.state != "approved":
        raise ValueError("baseline must be approved before release")
    baseline.state = "released"
    baseline.released_by = actor_user_id
    baseline.released_at = datetime.now(UTC)
    await record_event(
        session,
        event_type="baseline.released",
        project_id=baseline.project_id,
        actor_user_id=actor_user_id,
        payload={"baseline_id": baseline.baseline_id},
    )
    return baseline


async def obsolete_baseline(
    session: AsyncSession,
    baseline: Baseline,
    actor_user_id: str,
) -> Baseline:
    baseline.state = "obsolete"
    await record_event(
        session,
        event_type="baseline.obsoleted",
        project_id=baseline.project_id,
        actor_user_id=actor_user_id,
        payload={"baseline_id": baseline.baseline_id},
    )
    return baseline
