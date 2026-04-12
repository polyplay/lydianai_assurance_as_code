from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import (
    Baseline,
    BaselineArtefactRevision,
    BaselineRelationshipRevision,
    ReleaseGateResult,
)
from aac_backend.models.jobs import Job, ProjectUpdateLock
from aac_backend.models.validation import ValidationIssue
from aac_backend.schemas.domain import BaselineCreate
from aac_backend.services.event_service import record_event
from aac_backend.services.impact_service import open_suspects_for_project


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
    session.add(
        ProjectUpdateLock(
            project_id=project_id,
            lock_owner_job_id=job.job_id,
            acquired_by=actor_user_id,
            acquired_at=datetime.now(UTC),
        )
    )
    await session.flush()
    try:
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
        if blocking_issues or open_suspects:
            job.state = "failed"
            job.completed_at = datetime.now(UTC)
            job.error_json = {
                "blocking_issue_count": len(blocking_issues),
                "open_suspect_count": len(open_suspects),
            }
            raise ValueError("baseline eligibility failed")

        baseline = Baseline(
            project_id=project_id,
            name=data.name,
            description=data.description,
            state="creating_snapshot",
            created_by=actor_user_id,
            created_at=datetime.now(UTC),
            profile_id=data.profile_id,
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
        return baseline
    finally:
        lock = await session.get(ProjectUpdateLock, project_id)
        if lock:
            await session.delete(lock)


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
    issues = list(
        await session.scalars(
            select(ValidationIssue).where(
                ValidationIssue.project_id == project_id,
                ValidationIssue.status == "open",
            )
        )
    )
    open_suspects = await open_suspects_for_project(session, project_id)
    blocking = [
        {
            "issue_id": issue.validation_issue_id,
            "rule_id": issue.rule_id,
            "severity": issue.severity,
            "summary": issue.message,
        }
        for issue in issues
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
    result = ReleaseGateResult(
        project_id=project_id,
        baseline_id=baseline.baseline_id,
        evaluation_number=evaluation_number,
        triggered_by=actor_user_id,
        status="passed" if passed else "failed",
        result="pass" if passed else "fail",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        evaluated_rules_count=1,
        passed_rules_count=1 if passed else 0,
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
        payload={"result": result.result, "blocking_issue_count": len(blocking)},
    )
    return result


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
