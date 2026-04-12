from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import TimestampMixin, id_column


class Artefact(TimestampMixin, Base):
    __tablename__ = "artefacts"
    __table_args__ = (UniqueConstraint("project_id", "source_document", "source_object_id"),)

    artefact_id: Mapped[str] = id_column("ART")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    artefact_type: Mapped[str] = mapped_column(String(120), index=True)
    title: Mapped[str] = mapped_column(String(500))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(40), default="draft", index=True)
    owner_user_id: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    current_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_kind: Mapped[str] = mapped_column(String(40), default="api")
    source_tool: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_object_id: Mapped[str] = mapped_column(String(240))
    source_document: Mapped[str] = mapped_column(String(500), default="")
    current_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    standards_refs_json: Mapped[list] = mapped_column(JSON, default=list)
    work_product_kind: Mapped[str | None] = mapped_column(String(160), nullable=True)
    review_expectation: Mapped[str] = mapped_column(String(80), default="none")
    independence_expectation: Mapped[str] = mapped_column(String(80), default="none")
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class ArtefactRevision(Base):
    __tablename__ = "artefact_revisions"
    __table_args__ = (UniqueConstraint("artefact_id", "revision_number"),)

    artefact_revision_id: Mapped[str] = id_column("AREV")
    artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    revision_number: Mapped[int]
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)
    content_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    change_reason: Mapped[str] = mapped_column(Text, default="")
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    import_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_set_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)


class Relationship(TimestampMixin, Base):
    __tablename__ = "relationships"

    relationship_id: Mapped[str] = id_column("REL")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(120), index=True)
    source_artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), index=True)
    target_artefact_id: Mapped[str] = mapped_column(ForeignKey("artefacts.artefact_id"), index=True)
    status: Mapped[str] = mapped_column(String(40), default="active")
    current_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RelationshipRevision(Base):
    __tablename__ = "relationship_revisions"
    __table_args__ = (UniqueConstraint("relationship_id", "revision_number"),)

    relationship_revision_id: Mapped[str] = id_column("RREV")
    relationship_id: Mapped[str] = mapped_column(ForeignKey("relationships.relationship_id"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    revision_number: Mapped[int]
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    changed_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    changed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    import_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    change_set_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    audit_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
