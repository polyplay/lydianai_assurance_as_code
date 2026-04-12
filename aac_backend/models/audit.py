from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class AuditEvent(Base):
    __tablename__ = "audit_events"

    audit_event_id: Mapped[str] = id_column("AUDIT")
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), nullable=True)
    event_type: Mapped[str] = mapped_column(String(160), index=True)
    actor_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    actor_type: Mapped[str] = mapped_column(String(80), default="user")
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    affected_artefact_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    affected_relationship_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EvidenceReference(Base):
    __tablename__ = "evidence_references"

    evidence_id: Mapped[str] = id_column("EVID")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    evidence_type: Mapped[str] = mapped_column(String(120))
    uri: Mapped[str] = mapped_column(String(1000))
    checksum: Mapped[str | None] = mapped_column(String(160), nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class GeneratedReport(Base):
    __tablename__ = "generated_reports"

    report_id: Mapped[str] = id_column("RPT")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("baselines.baseline_id"), nullable=True)
    report_type: Mapped[str] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(80), default="queued")
    format: Mapped[str] = mapped_column(String(40), default="json")
    uri: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    generated_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    generated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_ref_json: Mapped[dict] = mapped_column(JSON, default=dict)
