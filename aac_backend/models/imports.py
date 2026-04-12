from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import id_column


class ImportRun(Base):
    __tablename__ = "import_runs"

    import_run_id: Mapped[str] = id_column("IMP")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    source_tool: Mapped[str] = mapped_column(String(120), default="sphinx-needs")
    source_root: Mapped[str] = mapped_column(String(500), default="")
    state: Mapped[str] = mapped_column(String(80), default="created", index=True)
    version_update_mode: Mapped[str] = mapped_column(String(80), default="ask_user")
    submitted_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnostics_json: Mapped[list] = mapped_column(JSON, default=list)


class ImportRunItem(Base):
    __tablename__ = "import_run_items"

    import_run_item_id: Mapped[str] = id_column("IMPITEM")
    import_run_id: Mapped[str] = mapped_column(ForeignKey("import_runs.import_run_id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    source_object_id: Mapped[str] = mapped_column(String(240), index=True)
    source_document: Mapped[str] = mapped_column(String(500), default="")
    artefact_type: Mapped[str] = mapped_column(String(120))
    artefact_id: Mapped[str | None] = mapped_column(ForeignKey("artefacts.artefact_id"), nullable=True)
    detected_change_type: Mapped[str] = mapped_column(String(80))
    current_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    proposed_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    proposed_payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    new_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    decision_status: Mapped[str] = mapped_column(String(80), default="not_required")
    decision_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    decision_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
