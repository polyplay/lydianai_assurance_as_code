from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class Baseline(Base):
    __tablename__ = "baselines"

    baseline_id: Mapped[str] = id_column("BASE")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    state: Mapped[str] = mapped_column(String(80), default="requested")
    created_by: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    released_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    profile_id: Mapped[str | None] = mapped_column(ForeignKey("assurance_profiles.profile_id"), nullable=True)
    release_gate_status: Mapped[str] = mapped_column(String(80), default="not_evaluated")
    gate_stale_event_sequence: Mapped[int | None] = mapped_column(nullable=True)
    eligibility_result_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)


class BaselineArtefactRevision(Base):
    __tablename__ = "baseline_artefact_revisions"

    baseline_id: Mapped[str] = mapped_column(ForeignKey("baselines.baseline_id"), primary_key=True)
    artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), primary_key=True)
    artefact_revision_id: Mapped[str] = mapped_column(ForeignKey("artefact_revisions.artefact_revision_id"))
    artefact_type: Mapped[str] = mapped_column(String(120))


class BaselineRelationshipRevision(Base):
    __tablename__ = "baseline_relationship_revisions"

    baseline_id: Mapped[str] = mapped_column(ForeignKey("baselines.baseline_id"), primary_key=True)
    relationship_id: Mapped[str] = mapped_column(ForeignKey("relationships.relationship_id"), primary_key=True)
    relationship_revision_id: Mapped[str] = mapped_column(
        ForeignKey("relationship_revisions.relationship_revision_id")
    )
    relationship_type: Mapped[str] = mapped_column(String(120))


class ReleaseGateResult(Base):
    __tablename__ = "release_gate_results"
    __table_args__ = (UniqueConstraint("baseline_id", "evaluation_number"),)

    release_gate_result_id: Mapped[str] = id_column("RGATE")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    baseline_id: Mapped[str] = mapped_column(ForeignKey("baselines.baseline_id"), index=True)
    evaluation_number: Mapped[int]
    triggered_by: Mapped[str] = mapped_column(ForeignKey("users.user_id"))
    job_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="running")
    result: Mapped[str | None] = mapped_column(String(40), nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evaluated_rules_count: Mapped[int] = mapped_column(default=0)
    passed_rules_count: Mapped[int] = mapped_column(default=0)
    blocking_issues_json: Mapped[list] = mapped_column(JSON, default=list)
    warning_issues_json: Mapped[list] = mapped_column(JSON, default=list)
    mandatory_artefact_gaps_json: Mapped[list] = mapped_column(JSON, default=list)
    open_suspect_states_json: Mapped[list] = mapped_column(JSON, default=list)
    evaluation_cutoff_sequence: Mapped[int] = mapped_column(default=0)
