from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.models.events import DomainEventOutbox
from aac_backend.services.event_service import append_audit_event
from aac_backend.services.event_policy import is_blocking_relevant_event_type


async def invalidate_project_gates_for_event(
    session: AsyncSession,
    event: DomainEventOutbox,
) -> int:
    if not event.project_id or not is_blocking_relevant_event_type(event.event_type):
        return 0
    baselines = list(
        await session.scalars(
            select(Baseline).where(
                Baseline.project_id == event.project_id,
                Baseline.state.in_(("created", "approved")),
                Baseline.release_gate_status == "passed",
            )
        )
    )
    invalidated = 0
    for baseline in baselines:
        result = await latest_gate_result(session, baseline.baseline_id)
        if result is None or event.event_sequence <= result.evaluation_cutoff_sequence:
            continue
        was_approved = baseline.state == "approved"
        baseline.release_gate_status = "stale"
        baseline.gate_stale_event_sequence = event.event_sequence
        if was_approved:
            baseline.state = "created"
        await append_audit_event(
            session,
            event_type="release_gate.invalidated",
            project_id=baseline.project_id,
            actor_user_id=None,
            operation="invalidate_release_gate",
            payload={
                "baseline_id": baseline.baseline_id,
                "trigger_event_id": event.event_id,
                "trigger_event_type": event.event_type,
                "trigger_event_sequence": event.event_sequence,
                "approval_invalidated": was_approved,
                "invalidated_at": datetime.now(UTC).isoformat(),
            },
        )
        invalidated += 1
    return invalidated


async def latest_gate_result(
    session: AsyncSession,
    baseline_id: str,
) -> ReleaseGateResult | None:
    return await session.scalar(
        select(ReleaseGateResult)
        .where(
            ReleaseGateResult.baseline_id == baseline_id,
            ReleaseGateResult.status.in_(("passed", "failed")),
        )
        .order_by(ReleaseGateResult.evaluation_number.desc())
        .limit(1)
    )


async def later_blocking_event(
    session: AsyncSession,
    *,
    project_id: str,
    cutoff_sequence: int,
) -> DomainEventOutbox | None:
    candidates = list(
        await session.scalars(
            select(DomainEventOutbox)
            .where(
                DomainEventOutbox.project_id == project_id,
                DomainEventOutbox.event_sequence > cutoff_sequence,
            )
            .order_by(DomainEventOutbox.event_sequence)
        )
    )
    return next(
        (
            event
            for event in candidates
            if is_blocking_relevant_event_type(event.event_type)
        ),
        None,
    )
