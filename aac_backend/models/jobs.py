from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class Job(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = id_column("JOB")
    project_id: Mapped[str | None] = mapped_column(ForeignKey("projects.project_id"), nullable=True)
    job_type: Mapped[str] = mapped_column(String(120), index=True)
    state: Mapped[str] = mapped_column(String(80), default="queued", index=True)
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    progress_percent: Mapped[int] = mapped_column(default=0)
    cancellation_requested: Mapped[bool] = mapped_column(default=False)
    correlation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    causation_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(240), nullable=True, unique=True)
    committed_effects_json: Mapped[dict] = mapped_column(JSON, default=dict)
    last_committed_unit: Mapped[str | None] = mapped_column(String(240), nullable=True)
    result_ref_json: Mapped[dict] = mapped_column(JSON, default=dict)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class ProjectUpdateLock(Base):
    __tablename__ = "project_update_locks"

    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), primary_key=True)
    lock_owner_job_id: Mapped[str] = mapped_column(ForeignKey("jobs.job_id"))
    lock_reason: Mapped[str] = mapped_column(String(120), default="baseline_creation")
    acquired_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    acquired_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
