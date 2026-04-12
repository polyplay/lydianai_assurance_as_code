from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import TimestampMixin, id_column


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    project_id: Mapped[str] = id_column("PROJ")
    project_key: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(240))
    description: Mapped[str] = mapped_column(Text, default="")
    active_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="active")


class ProjectConfiguration(TimestampMixin, Base):
    __tablename__ = "project_configurations"

    project_config_id: Mapped[str] = id_column("PCFG")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    version_update_mode: Mapped[str] = mapped_column(String(80), default="ask_user")
    sphinx_source_root: Mapped[str | None] = mapped_column(String(500), nullable=True)
    baseline_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    validation_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    reporting_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)


class AssuranceProfile(TimestampMixin, Base):
    __tablename__ = "assurance_profiles"

    profile_id: Mapped[str] = id_column("PROF")
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), nullable=True)
    name: Mapped[str] = mapped_column(String(240))
    classification: Mapped[str] = mapped_column(String(40))
    inherits_from_profile_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    profile_payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="active")


class TailoringDecision(Base):
    __tablename__ = "tailoring_decisions"

    tailoring_decision_id: Mapped[str] = id_column("TAIL")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    scope_type: Mapped[str] = mapped_column(String(80))
    scope_id: Mapped[str] = mapped_column(String(120))
    target_kind: Mapped[str] = mapped_column(String(80))
    target_id: Mapped[str] = mapped_column(String(120))
    previous_applicability: Mapped[str] = mapped_column(String(80))
    tailored_applicability: Mapped[str] = mapped_column(String(80))
    rationale: Mapped[str] = mapped_column(Text)
    evidence_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    approved_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="draft")
