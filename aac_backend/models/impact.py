from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class ImpactAnalysisRun(Base):
    __tablename__ = "impact_analysis_runs"

    impact_analysis_id: Mapped[str] = id_column("IMPACT")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    state: Mapped[str] = mapped_column(String(80), default="queued")
    trigger_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    scope_json: Mapped[dict] = mapped_column(JSON, default=dict)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)


class ImpactAnalysisItem(Base):
    __tablename__ = "impact_analysis_items"

    impact_item_id: Mapped[str] = id_column("IITEM")
    impact_analysis_id: Mapped[str] = mapped_column(
        ForeignKey("impact_analysis_runs.impact_analysis_id"),
        index=True,
    )
    impacted_artefact_id: Mapped[str | None] = mapped_column(
        ForeignKey("artefacts.artefact_id"),
        nullable=True,
    )
    impacted_relationship_id: Mapped[str | None] = mapped_column(
        ForeignKey("relationships.relationship_id"),
        nullable=True,
    )
    impact_type: Mapped[str] = mapped_column(String(80))
    reason_path_json: Mapped[list] = mapped_column(JSON, default=list)
    retest_recommendation_json: Mapped[dict] = mapped_column(JSON, default=dict)


class SuspectState(Base):
    __tablename__ = "suspect_states"

    suspect_state_id: Mapped[str] = id_column("SUSP")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), index=True)
    trigger_artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), index=True)
    trigger_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trigger_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trigger_event_type: Mapped[str] = mapped_column(String(160))
    propagation_depth: Mapped[int] = mapped_column(default=1)
    propagation_path_json: Mapped[list] = mapped_column(JSON, default=list)
    reason: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="open", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cleared_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    clearing_method: Mapped[str | None] = mapped_column(String(80), nullable=True)
    clearing_evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    clearance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class TestResultRecord(Base):
    __tablename__ = "test_result_records"

    test_result_record_id: Mapped[str] = id_column("TRES")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    artefact_id: Mapped[str | None] = mapped_column(ForeignKey("artefacts.artefact_id"), nullable=True)
    test_specification_id: Mapped[str | None] = mapped_column(
        ForeignKey("artefacts.artefact_id"),
        nullable=True,
    )
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("baselines.baseline_id"), nullable=True)
    build_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    environment_ref: Mapped[str | None] = mapped_column(String(240), nullable=True)
    verdict: Mapped[str] = mapped_column(String(40))
    executed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
