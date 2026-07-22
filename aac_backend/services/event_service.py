from datetime import UTC, datetime
import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.audit import AuditEvent
from aac_backend.models.baselines import Baseline
from aac_backend.models.events import DomainEventOutbox
from aac_backend.schemas.context import CommandContext
from aac_backend.services.event_policy import is_blocking_relevant_event_type
from aac_backend.services.observability import event_log_fields, structured_log
from aac_backend.services.request_context import current_correlation_id, current_request_id

LOGGER = logging.getLogger(__name__)


async def append_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    payload: dict | None = None,
    affected_artefact_ids: list[str] | None = None,
    affected_relationship_ids: list[str] | None = None,
    context: CommandContext | None = None,
    operation: str | None = None,
) -> AuditEvent:
    role_at_time = context.role_at_time if context else await _role_at_time(
        session,
        actor_user_id,
        project_id,
    )
    event = AuditEvent(
        project_id=project_id,
        event_type=event_type,
        actor_user_id=actor_user_id,
        actor_type="user" if actor_user_id else "system",
        role_at_time_of_action=role_at_time,
        operation=operation or event_type,
        request_id=context.request_id if context else current_request_id(),
        correlation_id=context.correlation_id if context else current_correlation_id(),
        causation_id=context.causation_id if context else None,
        payload_json=payload or {},
        affected_artefact_ids_json=affected_artefact_ids or [],
        affected_relationship_ids_json=affected_relationship_ids or [],
        created_at=datetime.now(UTC),
    )
    session.add(event)
    structured_log(
        LOGGER,
        logging.INFO,
        "audit.event.appended",
        event_type=event_type,
        project_id=project_id,
        actor_user_id=actor_user_id,
        operation=operation or event_type,
        request_id=event.request_id,
        correlation_id=event.correlation_id,
    )
    return event


async def append_domain_event(
    session: AsyncSession,
    *,
    event_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    payload: dict | None = None,
    context: CommandContext | None = None,
    idempotency_key: str | None = None,
) -> DomainEventOutbox:
    await _lock_release_candidates(session, project_id, event_type)
    effective_idempotency_key = idempotency_key or (
        context.idempotency_key if context else None
    )
    if effective_idempotency_key:
        existing = await session.scalar(
            select(DomainEventOutbox).where(
                DomainEventOutbox.idempotency_key == effective_idempotency_key
            )
        )
        if isinstance(existing, DomainEventOutbox):
            return existing

    now = datetime.now(UTC)
    event = DomainEventOutbox(
        event_type=event_type,
        project_id=project_id,
        actor_user_id=actor_user_id,
        correlation_id=context.correlation_id if context else current_correlation_id(),
        causation_id=context.causation_id if context else None,
        idempotency_key=effective_idempotency_key,
        payload_json=payload or {},
        status="pending",
        attempts=0,
        occurred_at=now,
        available_at=now,
    )
    session.add(event)
    return event


async def _lock_release_candidates(
    session: AsyncSession,
    project_id: str | None,
    event_type: str,
) -> None:
    if not project_id or not is_blocking_relevant_event_type(event_type):
        return
    scalars = getattr(session, "scalars", None)
    if scalars is None:
        return
    list(
        await scalars(
            select(Baseline.baseline_id)
            .where(
                Baseline.project_id == project_id,
                Baseline.state.in_(("created", "approved")),
                Baseline.release_gate_status == "passed",
            )
            .with_for_update()
        )
    )


async def record_event(
    session: AsyncSession,
    *,
    event_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    payload: dict | None = None,
    affected_artefact_ids: list[str] | None = None,
    affected_relationship_ids: list[str] | None = None,
    context: CommandContext | None = None,
    operation: str | None = None,
    idempotency_key: str | None = None,
) -> AuditEvent:
    audit = await append_audit_event(
        session,
        event_type=event_type,
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=payload,
        affected_artefact_ids=affected_artefact_ids,
        affected_relationship_ids=affected_relationship_ids,
        context=context,
        operation=operation,
    )
    event_payload = {
        **(payload or {}),
        "affected_artefact_ids": affected_artefact_ids or [],
        "affected_relationship_ids": affected_relationship_ids or [],
    }
    await append_domain_event(
        session,
        event_type=event_type,
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=event_payload,
        context=context,
        idempotency_key=idempotency_key,
    )
    structured_log(
        LOGGER,
        logging.INFO,
        "audit.event.recorded",
        **event_log_fields(
            event_type=event_type,
            project_id=project_id,
            actor_user_id=actor_user_id,
            operation=operation,
            affected_artefact_ids=affected_artefact_ids,
            affected_relationship_ids=affected_relationship_ids,
            payload=payload,
        ),
    )
    return audit


async def latest_event_sequence(session: AsyncSession, project_id: str | None = None) -> int:
    statement = select(func.max(DomainEventOutbox.event_sequence))
    if project_id is not None:
        statement = statement.where(DomainEventOutbox.project_id == project_id)
    return int(await session.scalar(statement) or 0)


async def _role_at_time(
    session: AsyncSession,
    actor_user_id: str | None,
    project_id: str | None,
) -> str:
    if actor_user_id is None:
        return "system"
    try:
        from aac_backend.services.auth_service import user_roles

        roles = await user_roles(session, actor_user_id, project_id)
    except Exception:
        return "unknown"
    return ",".join(roles) if roles else "user"
