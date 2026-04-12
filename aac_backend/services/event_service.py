from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.audit import AuditEvent


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    payload: dict | None = None,
    affected_artefact_ids: list[str] | None = None,
    affected_relationship_ids: list[str] | None = None,
) -> AuditEvent:
    event = AuditEvent(
        project_id=project_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        payload_json=payload or {},
        affected_artefact_ids_json=affected_artefact_ids or [],
        affected_relationship_ids_json=affected_relationship_ids or [],
        created_at=datetime.now(UTC),
    )
    session.add(event)
    return event
