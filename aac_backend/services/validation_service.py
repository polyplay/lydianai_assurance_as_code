from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.validation import ValidationIssue, ValidationRule, ValidationRun
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.services.event_service import record_event


async def seed_rule_catalog(session: AsyncSession) -> None:
    for rule in RULE_CATALOG.values():
        existing = await session.get(ValidationRule, rule.rule_id)
        if existing:
            continue
        session.add(
            ValidationRule(
                rule_id=rule.rule_id,
                title=rule.title,
                source_basis_json=[],
                standards_refs_json=[],
                default_severity=rule.severity,
                rule_payload_json={
                    "execution_modes": list(rule.execution_modes),
                    "blocking_contexts": list(rule.blocking_contexts),
                },
                status="active",
            )
        )


async def run_validation(
    session: AsyncSession,
    project_id: str,
    actor_user_id: str,
    scope: dict | None = None,
) -> ValidationRun:
    await seed_rule_catalog(session)
    run = ValidationRun(
        project_id=project_id,
        scope_json=scope or {"type": "project", "id": project_id},
        state="running",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()

    issues: list[ValidationIssue] = []
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
    artefact_ids = {artefact.artefact_id for artefact in artefacts}

    for artefact in artefacts:
        if not artefact.title or not artefact.artefact_type or not artefact.source_object_id:
            issues.append(
                _issue(
                    run,
                    "AAC-RULE-RULE-004",
                    "Artefact required metadata is incomplete",
                    [artefact.artefact_id],
                )
            )

    seen_source_keys: set[tuple[str, str]] = set()
    for artefact in artefacts:
        key = (artefact.source_document, artefact.source_object_id)
        if key in seen_source_keys:
            issues.append(
                _issue(
                    run,
                    "AAC-RULE-RULE-003",
                    "Artefact source identity is not unique",
                    [artefact.artefact_id],
                )
            )
        seen_source_keys.add(key)

    for relationship in relationships:
        if (
            relationship.source_artefact_id not in artefact_ids
            or relationship.target_artefact_id not in artefact_ids
        ):
            issue = _issue(
                run,
                "AAC-RULE-RULE-001",
                "Relationship references a missing artefact",
                [],
            )
            issue.affected_relationship_ids_json = [relationship.relationship_id]
            issues.append(issue)

    for issue in issues:
        session.add(issue)

    run.state = "completed"
    run.completed_at = datetime.now(UTC)
    run.summary_json = {"issue_count": len(issues)}
    await record_event(
        session,
        event_type="validation.run_completed",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=run.summary_json,
    )
    return run


def _issue(
    run: ValidationRun,
    rule_id: str,
    message: str,
    affected_artefact_ids: list[str],
) -> ValidationIssue:
    rule = RULE_CATALOG[rule_id]
    return ValidationIssue(
        project_id=run.project_id,
        validation_run_id=run.validation_run_id,
        rule_id=rule_id,
        severity=rule.severity,
        status="open",
        message=message,
        affected_artefact_ids_json=affected_artefact_ids,
        affected_relationship_ids_json=[],
        blocking_contexts_json=list(rule.blocking_contexts),
        remediation_hint="Correct the artefact or relationship and rerun validation.",
        created_at=datetime.now(UTC),
    )
