from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Identity, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class DomainEventOutbox(Base):
    __tablename__ = "domain_event_outbox"

    event_id: Mapped[str] = id_column("EVT")
    event_sequence: Mapped[int] = mapped_column(
        BigInteger,
        Identity(),
        unique=True,
        nullable=False,
        index=True,
    )
    event_type: Mapped[str] = mapped_column(String(160), index=True)
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), nullable=True, index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    causation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(240), nullable=True, unique=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="pending", index=True)
    attempts: Mapped[int] = mapped_column(default=0)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    available_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    locked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delivered_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)


class EventConsumerReceipt(Base):
    __tablename__ = "event_consumer_receipts"
    __table_args__ = (UniqueConstraint("event_id", "consumer_name"),)

    event_consumer_receipt_id: Mapped[str] = id_column("EVTRCPT")
    event_id: Mapped[str] = mapped_column(ForeignKey("domain_event_outbox.event_id"), index=True)
    consumer_name: Mapped[str] = mapped_column(String(160))
    idempotency_key: Mapped[str] = mapped_column(String(240), unique=True)
    status: Mapped[str] = mapped_column(String(40), default="processing")
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    result_ref_json: Mapped[dict] = mapped_column(JSON, default=dict)
