import hashlib
import json
from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, ArtefactRevision, Relationship, RelationshipRevision
from aac_backend.models.projects import ProjectConfiguration
from aac_backend.repositories.domain import (
    ArtefactRepository,
    has_project_update_lock,
)
from aac_backend.schemas.domain import ArtefactCreate, ArtefactUpdate, RelationshipCreate
from aac_backend.services.artefact_schema_service import validate_artefact_payload
from aac_backend.services.event_service import record_event
from aac_backend.services.impact_service import propagate_suspects
from aac_backend.services.validation_service import relationship_type_allowed_for_types

ALLOWED_STATUS_TRANSITIONS = {
    "draft": {"under_review", "obsolete"},
    "under_review": {"reviewed", "draft", "obsolete"},
    "reviewed": {"approved", "draft", "obsolete"},
    "approved": {"released", "obsolete"},
    "released": {"obsolete"},
    "obsolete": set(),
}

ASIL_RANK = {"QM": 0, "ASIL_A": 1, "ASIL_B": 2, "ASIL_C": 3, "ASIL_D": 4}


def fingerprint(payload: dict) -> str:
    normalized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


async def ensure_project_writable(session: AsyncSession, project_id: str) -> None:
    if await has_project_update_lock(session, project_id):
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail={"message": "Project update lock is active", "retry_after": 30},
        )


async def create_artefact(
    session: AsyncSession,
    project_id: str,
    data: ArtefactCreate,
    actor_user_id: str,
) -> Artefact:
    await ensure_project_writable(session, project_id)
    config = await _project_config(session, project_id)
    validate_artefact_payload(data.artefact_type, data.payload, config)
    validate_asil_not_above_project(data.artefact_type, data.payload, config)
    repo = ArtefactRepository(session)
    existing = await repo.by_source_identity(
        project_id,
        data.source.source_document,
        data.source.source_object_id,
    )
    if existing:
        raise ValueError("source identity already exists")
    current_fingerprint = fingerprint(data.payload)
    artefact = Artefact(
        project_id=project_id,
        artefact_type=data.artefact_type,
        title=data.title,
        description=data.description,
        status=data.status,
        owner_user_id=data.owner_user_id or actor_user_id,
        source_kind=data.source.source_kind,
        source_tool=data.source.source_tool,
        source_object_id=data.source.source_object_id,
        source_document=data.source.source_document,
        current_fingerprint=current_fingerprint,
        standards_refs_json=data.standards_refs,
        work_product_kind=data.work_product_kind,
        payload_json=data.payload,
    )
    session.add(artefact)
    await session.flush()
    revision = ArtefactRevision(
        artefact_id=artefact.artefact_id,
        project_id=project_id,
        revision_number=1,
        payload_json=data.payload,
        metadata_json={"title": data.title, "status": data.status},
        content_fingerprint=current_fingerprint,
        change_reason="create",
        changed_by=actor_user_id,
        changed_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    artefact.current_revision_id = revision.artefact_revision_id
    await record_event(
        session,
        event_type="artefact.created",
        project_id=project_id,
        actor_user_id=actor_user_id,
        affected_artefact_ids=[artefact.artefact_id],
    )
    return artefact


async def update_artefact(
    session: AsyncSession,
    artefact: Artefact,
    data: ArtefactUpdate,
    actor_user_id: str,
) -> Artefact:
    await ensure_project_writable(session, artefact.project_id)
    previous_status = artefact.status
    if artefact.status == "obsolete":
        raise ValueError("obsolete artefacts cannot be updated")
    if data.status is not None and data.status != artefact.status:
        raise ValueError("Use lifecycle transition endpoints to change artefact status")
    if data.base_revision_id and data.base_revision_id != artefact.current_revision_id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Stale artefact revision")

    payload = data.payload if data.payload is not None else artefact.payload_json
    config = await _project_config(session, artefact.project_id)
    validate_artefact_payload(artefact.artefact_type, payload, config)
    validate_asil_not_above_project(artefact.artefact_type, payload, config)
    if data.title is not None:
        artefact.title = data.title
    if data.description is not None:
        artefact.description = data.description
    if data.status is not None:
        artefact.status = data.status
    if data.standards_refs is not None:
        artefact.standards_refs_json = data.standards_refs
    artefact.payload_json = payload
    artefact.current_fingerprint = fingerprint(payload)
    artefact.updated_at = datetime.now(UTC)

    repo = ArtefactRepository(session)
    revision = ArtefactRevision(
        artefact_id=artefact.artefact_id,
        project_id=artefact.project_id,
        revision_number=await repo.next_revision_number(artefact.artefact_id),
        payload_json=payload,
        metadata_json={"title": artefact.title, "status": artefact.status},
        content_fingerprint=artefact.current_fingerprint,
        change_reason=data.change_reason,
        changed_by=actor_user_id,
        changed_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    artefact.current_revision_id = revision.artefact_revision_id
    await record_event(
        session,
        event_type="artefact.revised",
        project_id=artefact.project_id,
        actor_user_id=actor_user_id,
        affected_artefact_ids=[artefact.artefact_id],
    )
    if previous_status == "released":
        await propagate_suspects(
            session,
            project_id=artefact.project_id,
            trigger_artefact_id=artefact.artefact_id,
            trigger_revision_id=artefact.current_revision_id,
            trigger_event_type="artefact.revised",
            actor_user_id=actor_user_id,
        )
    return artefact


async def change_artefact_status(
    session: AsyncSession,
    artefact: Artefact,
    *,
    new_status: str,
    actor_user_id: str,
    event_type: str = "artefact.status_changed",
    reason: str | None = None,
) -> Artefact:
    await ensure_project_writable(session, artefact.project_id)
    if artefact.status == "obsolete" and new_status != "obsolete":
        raise ValueError("obsolete artefacts cannot transition")
    if new_status != artefact.status and new_status not in ALLOWED_STATUS_TRANSITIONS.get(artefact.status, set()):
        raise ValueError(f"transition {artefact.status} -> {new_status} is not permitted")
    artefact.status = new_status
    artefact.updated_at = datetime.now(UTC)
    await record_event(
        session,
        event_type=event_type,
        project_id=artefact.project_id,
        actor_user_id=actor_user_id,
        affected_artefact_ids=[artefact.artefact_id],
        payload={"status": new_status, "reason": reason} if reason else {"status": new_status},
    )
    return artefact


async def obsolete_artefact(
    session: AsyncSession,
    artefact: Artefact,
    actor_user_id: str,
) -> Artefact:
    await ensure_project_writable(session, artefact.project_id)
    previous_status = artefact.status
    artefact.status = "obsolete"
    artefact.deleted_at = datetime.now(UTC)
    artefact.updated_at = datetime.now(UTC)
    await record_event(
        session,
        event_type="artefact.deleted",
        project_id=artefact.project_id,
        actor_user_id=actor_user_id,
        affected_artefact_ids=[artefact.artefact_id],
    )
    if previous_status == "released":
        await propagate_suspects(
            session,
            project_id=artefact.project_id,
            trigger_artefact_id=artefact.artefact_id,
            trigger_revision_id=artefact.current_revision_id,
            trigger_event_type="artefact.status_changed",
            actor_user_id=actor_user_id,
        )
    return artefact


async def create_relationship(
    session: AsyncSession,
    project_id: str,
    data: RelationshipCreate,
    actor_user_id: str,
) -> Relationship:
    await ensure_project_writable(session, project_id)
    source = await session.get(Artefact, data.source_artefact_id)
    target = await session.get(Artefact, data.target_artefact_id)
    if not source or not target or source.project_id != project_id or target.project_id != project_id:
        raise ValueError("relationship endpoints must exist in project")
    if not relationship_type_allowed_for_types(
        source.artefact_type,
        target.artefact_type,
        data.relationship_type,
        same_artefact=source.artefact_id == target.artefact_id,
    ):
        raise ValueError("relationship type is not permitted for the source and target artefact types")
    relationship = Relationship(
        project_id=project_id,
        relationship_type=data.relationship_type,
        source_artefact_id=data.source_artefact_id,
        target_artefact_id=data.target_artefact_id,
        payload_json=data.payload,
    )
    session.add(relationship)
    await session.flush()
    revision = RelationshipRevision(
        relationship_id=relationship.relationship_id,
        project_id=project_id,
        revision_number=1,
        payload_json=data.payload,
        changed_by=actor_user_id,
        changed_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    relationship.current_revision_id = revision.relationship_revision_id
    await record_event(
        session,
        event_type="relationship.created",
        project_id=project_id,
        actor_user_id=actor_user_id,
        affected_relationship_ids=[relationship.relationship_id],
    )
    return relationship


async def _project_config(session: AsyncSession, project_id: str) -> ProjectConfiguration | None:
    return await session.scalar(
        select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
    )


def validate_asil_not_above_project(
    artefact_type: str,
    payload: dict,
    config: ProjectConfiguration | None,
) -> None:
    _ = artefact_type
    artefact_asil = payload.get("asil_level")
    if not artefact_asil:
        return
    project_asil = (
        (((config.validation_policy_json if config else {}) or {}).get("project_assurance_configuration") or {})
        .get("asil_level")
    )
    if not project_asil:
        return
    if ASIL_RANK.get(str(artefact_asil), -1) > ASIL_RANK.get(str(project_asil), -1):
        raise ValueError(
            f"artefact ASIL level {artefact_asil} exceeds project maximum {project_asil}"
        )
