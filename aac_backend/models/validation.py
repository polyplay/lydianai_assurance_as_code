from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class ValidationRule(Base):
    __tablename__ = "validation_rules"

    rule_id: Mapped[str] = mapped_column(String(80), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    source_basis_json: Mapped[list] = mapped_column(JSON, default=list)
    standards_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    default_severity: Mapped[str] = mapped_column(String(40), default="major")
    rule_payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="active")


class ValidationRun(Base):
    __tablename__ = "validation_runs"

    validation_run_id: Mapped[str] = id_column("VRUN")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("baselines.baseline_id"), nullable=True)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    state: Mapped[str] = mapped_column(String(80), default="queued")
    trigger_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    validation_issue_id: Mapped[str] = id_column("VISS")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    validation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("validation_runs.validation_run_id"),
        nullable=True,
    )
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("baselines.baseline_id"), nullable=True)
    rule_id: Mapped[str] = mapped_column(ForeignKey("validation_rules.rule_id"))
    severity: Mapped[str] = mapped_column(String(40))
    status: Mapped[str] = mapped_column(String(40), default="open")
    message: Mapped[str] = mapped_column(Text)
    affected_artefact_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    affected_relationship_ids_json: Mapped[list] = mapped_column(JSON, default=list)
    blocking_contexts_json: Mapped[list] = mapped_column(JSON, default=list)
    remediation_hint: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    suppressed_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    suppression_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
