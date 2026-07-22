from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from arq import create_pool
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.database import AsyncSessionLocal
from aac_backend.models.events import DomainEventOutbox, EventConsumerReceipt
from aac_backend.models.jobs import Job
from aac_backend.services.gate_currency_service import (
    invalidate_project_gates_for_event,
)
from aac_backend.services.event_policy import is_blocking_relevant_event_type
from aac_backend.workers.settings_support import redis_settings

MAX_DELIVERY_ATTEMPTS = 10
CLAIM_LEASE = timedelta(minutes=5)


@dataclass(frozen=True)
class PreparedJob:
    function_name: str
    job_id: str
    args: tuple


async def dispatch_pending_events(limit: int = 50) -> int:
    event_ids = await _claim_events(limit)
    delivered = 0
    for event_id in event_ids:
        if await dispatch_event(event_id):
            delivered += 1
    return delivered


async def dispatch_event(event_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        event = await session.get(DomainEventOutbox, event_id)
        if event is None:
            return False
        consumer_names = _consumer_names_for(event.event_type)

    try:
        for consumer_name in consumer_names:
            prepared = await _prepare_consumer(event_id, consumer_name)
            if prepared is not None:
                await _enqueue_prepared(prepared)
                await _mark_receipt_processed(event_id, consumer_name)
    except Exception as exc:
        await _mark_event_retry(event_id, exc)
        return False

    async with AsyncSessionLocal() as session:
        event = await session.get(DomainEventOutbox, event_id)
        if event is None:
            return False
        event.status = "delivered"
        event.delivered_at = datetime.now(UTC)
        event.locked_at = None
        event.last_error = None
        await session.commit()
    return True


async def retry_dead_letter_event(event_id: str) -> bool:
    async with AsyncSessionLocal() as session:
        event = await session.get(DomainEventOutbox, event_id)
        if event is None or event.status != "dead_letter":
            return False
        event.status = "retry"
        event.available_at = datetime.now(UTC)
        event.last_error = None
        await session.commit()
    return True


async def _claim_events(limit: int) -> list[str]:
    now = datetime.now(UTC)
    expired_claim = now - CLAIM_LEASE
    async with AsyncSessionLocal() as session:
        events = list(
            await session.scalars(
                select(DomainEventOutbox)
                .where(
                    or_(
                        and_(
                            DomainEventOutbox.status.in_(("pending", "retry")),
                            DomainEventOutbox.available_at <= now,
                        ),
                        and_(
                            DomainEventOutbox.status == "processing",
                            DomainEventOutbox.locked_at <= expired_claim,
                        ),
                    )
                )
                .order_by(DomainEventOutbox.event_sequence)
                .limit(limit)
                .with_for_update(skip_locked=True)
            )
        )
        for event in events:
            event.status = "processing"
            event.attempts += 1
            event.locked_at = now
        await session.commit()
        return [event.event_id for event in events]


def _consumer_names_for(event_type: str) -> tuple[str, ...]:
    consumers: list[str] = []
    if is_blocking_relevant_event_type(event_type):
        consumers.append("release_gate_invalidation")
    if event_type == "import.completed":
        consumers.append("import_validation")
    return tuple(consumers)


async def _prepare_consumer(event_id: str, consumer_name: str) -> PreparedJob | None:
    async with AsyncSessionLocal() as session:
        event = await session.get(DomainEventOutbox, event_id)
        if event is None:
            return None
        receipt = await session.scalar(
            select(EventConsumerReceipt).where(
                EventConsumerReceipt.event_id == event_id,
                EventConsumerReceipt.consumer_name == consumer_name,
            )
        )
        if receipt is not None:
            if receipt.status == "processed":
                return None
            return _prepared_job_from_receipt(receipt)

        receipt = EventConsumerReceipt(
            event_id=event_id,
            consumer_name=consumer_name,
            idempotency_key=f"{event_id}:{consumer_name}",
            status="processing",
        )
        session.add(receipt)
        await session.flush()

        prepared: PreparedJob | None = None
        if consumer_name == "release_gate_invalidation":
            invalidated = await invalidate_project_gates_for_event(session, event)
            receipt.result_ref_json = {"invalidated_baseline_count": invalidated}
            receipt.status = "processed"
            receipt.processed_at = datetime.now(UTC)
        elif consumer_name == "import_validation":
            prepared = await _prepare_import_validation_job(session, event)
            receipt.status = "prepared"
            receipt.result_ref_json = {
                "function_name": prepared.function_name,
                "job_id": prepared.job_id,
                "args": list(prepared.args),
            }
        else:
            raise ValueError(f"Unknown event consumer: {consumer_name}")

        await session.commit()
        return prepared


async def _prepare_import_validation_job(
    session: AsyncSession,
    event: DomainEventOutbox,
) -> PreparedJob:
    import_run_id = event.payload_json["import_run_id"]
    idempotency_key = f"import:{import_run_id}:validation"
    job = await session.scalar(select(Job).where(Job.idempotency_key == idempotency_key))
    if job is None:
        job = Job(
            project_id=event.project_id,
            job_type="validation_run",
            state="queued",
            submitted_by=event.actor_user_id,
            submitted_at=datetime.now(UTC),
            correlation_id=event.correlation_id,
            causation_id=event.event_id,
            idempotency_key=idempotency_key,
            result_ref_json={"trigger_event_id": event.event_id},
        )
        session.add(job)
        await session.flush()
    scope = {
        "type": "project",
        "trigger": "sphinx_import",
        "import_run_id": import_run_id,
        "trigger_event_id": event.event_id,
    }
    return PreparedJob(
        function_name="validation_job",
        job_id=job.job_id,
        args=(job.job_id, event.project_id, event.actor_user_id, scope),
    )


def _prepared_job_from_receipt(receipt: EventConsumerReceipt) -> PreparedJob | None:
    payload = receipt.result_ref_json or {}
    if not payload.get("function_name"):
        return None
    return PreparedJob(
        function_name=payload["function_name"],
        job_id=payload["job_id"],
        args=tuple(payload.get("args", [])),
    )


async def _enqueue_prepared(prepared: PreparedJob) -> None:
    redis = await create_pool(redis_settings())
    try:
        await redis.enqueue_job(
            prepared.function_name,
            *prepared.args,
            _job_id=prepared.job_id,
        )
    finally:
        await redis.close()


async def _mark_receipt_processed(event_id: str, consumer_name: str) -> None:
    async with AsyncSessionLocal() as session:
        receipt = await session.scalar(
            select(EventConsumerReceipt).where(
                EventConsumerReceipt.event_id == event_id,
                EventConsumerReceipt.consumer_name == consumer_name,
            )
        )
        if receipt is not None:
            receipt.status = "processed"
            receipt.processed_at = datetime.now(UTC)
            await session.commit()


async def _mark_event_retry(event_id: str, exc: Exception) -> None:
    async with AsyncSessionLocal() as session:
        event = await session.get(DomainEventOutbox, event_id)
        if event is None:
            return
        event.status = "dead_letter" if event.attempts >= MAX_DELIVERY_ATTEMPTS else "retry"
        event.available_at = datetime.now(UTC) + timedelta(
            seconds=min(2 ** max(event.attempts, 1), 300)
        )
        event.locked_at = None
        event.last_error = f"{type(exc).__name__}: {exc}"
        await session.commit()
