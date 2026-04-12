from sqlalchemy import ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import TimestampMixin, id_column


class StandardsReference(TimestampMixin, Base):
    __tablename__ = "standards_references"

    standards_reference_id: Mapped[str] = id_column("STD")
    standard: Mapped[str] = mapped_column(String(80))
    edition: Mapped[str] = mapped_column(String(80))
    part_or_process: Mapped[str] = mapped_column(String(120))
    clause_or_process_id: Mapped[str] = mapped_column(String(120))
    title: Mapped[str] = mapped_column(Text)
    reference_type: Mapped[str] = mapped_column(String(80))
    source_access: Mapped[str] = mapped_column(String(80), default="public")
    review_status: Mapped[str] = mapped_column(String(80), default="draft_public_reference")


class ArtefactStandardMapping(Base):
    __tablename__ = "artefact_standard_mappings"

    artefact_type: Mapped[str] = mapped_column(String(120), primary_key=True)
    standards_reference_id: Mapped[str] = mapped_column(
        ForeignKey("standards_references.standards_reference_id"),
        primary_key=True,
    )
    required_content_json: Mapped[dict] = mapped_column(JSON, default=dict)
    review_expectation: Mapped[str] = mapped_column(String(80), default="required")
    independence_expectation: Mapped[str] = mapped_column(String(80), default="required_by_profile")
    verification_method_expectation: Mapped[list] = mapped_column(JSON, default=list)
