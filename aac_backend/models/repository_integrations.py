from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aac_backend.database import Base
from aac_backend.models.types import TimestampMixin, id_column


class ConnectorSecret(TimestampMixin, Base):
    __tablename__ = "connector_secrets"

    connector_secret_id: Mapped[str] = id_column("CSEC")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    secret_type: Mapped[str] = mapped_column(String(80))
    encrypted_payload: Mapped[str] = mapped_column(Text)
    key_id: Mapped[str] = mapped_column(String(120), default="default")
    status: Mapped[str] = mapped_column(String(40), default="active")
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    last_rotated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class RepositoryConnector(TimestampMixin, Base):
    __tablename__ = "repository_connectors"
    __table_args__ = (
        UniqueConstraint("project_id", "provider", "owner", "repository"),
    )

    repository_connector_id: Mapped[str] = id_column("RCON")
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    provider: Mapped[str] = mapped_column(String(40), default="github", index=True)
    name: Mapped[str] = mapped_column(String(240))
    owner: Mapped[str] = mapped_column(String(240))
    repository: Mapped[str] = mapped_column(String(240))
    repository_url: Mapped[str] = mapped_column(String(1000))
    default_branch: Mapped[str] = mapped_column(String(240), default="main")
    auth_mode: Mapped[str] = mapped_column(String(80), default="github_app")
    app_id: Mapped[str] = mapped_column(String(120))
    installation_id: Mapped[str] = mapped_column(String(120))
    access_token_secret_id: Mapped[str | None] = mapped_column(
        ForeignKey("connector_secrets.connector_secret_id"),
        nullable=True,
    )
    private_key_secret_id: Mapped[str | None] = mapped_column(
        ForeignKey("connector_secrets.connector_secret_id"),
        nullable=True,
    )
    webhook_secret_id: Mapped[str | None] = mapped_column(
        ForeignKey("connector_secrets.connector_secret_id"),
        nullable=True,
    )
    scan_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    mapping_policy_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(40), default="active", index=True)
    last_scan_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    last_revision_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)


class RepositoryRevision(Base):
    __tablename__ = "repository_revisions"
    __table_args__ = (UniqueConstraint("repository_connector_id", "commit_sha"),)

    repository_revision_id: Mapped[str] = id_column("RREV")
    repository_connector_id: Mapped[str] = mapped_column(
        ForeignKey("repository_connectors.repository_connector_id"),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    scan_run_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    commit_sha: Mapped[str] = mapped_column(String(120), index=True)
    branch: Mapped[str | None] = mapped_column(String(240), nullable=True)
    tag: Mapped[str | None] = mapped_column(String(240), nullable=True)
    commit_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    author_name: Mapped[str | None] = mapped_column(String(240), nullable=True)
    author_email: Mapped[str | None] = mapped_column(String(320), nullable=True)
    message: Mapped[str] = mapped_column(Text, default="")
    tree_sha: Mapped[str | None] = mapped_column(String(120), nullable=True)
    mapping_fingerprint: Mapped[str | None] = mapped_column(String(128), nullable=True)
    status: Mapped[str] = mapped_column(String(40), default="scanned")
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)


class RepositoryScanRun(Base):
    __tablename__ = "repository_scan_runs"

    repository_scan_run_id: Mapped[str] = id_column("RSCAN")
    repository_connector_id: Mapped[str] = mapped_column(
        ForeignKey("repository_connectors.repository_connector_id"),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    job_id: Mapped[str | None] = mapped_column(ForeignKey("jobs.job_id"), nullable=True)
    trigger: Mapped[str] = mapped_column(String(80), default="manual")
    state: Mapped[str] = mapped_column(String(80), default="queued", index=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    commit_sha: Mapped[str | None] = mapped_column(String(120), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(240), nullable=True)
    pull_request_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    summary_json: Mapped[dict] = mapped_column(JSON, default=dict)
    diagnostics_json: Mapped[dict] = mapped_column(JSON, default=dict)


class RepositoryWebhookDelivery(Base):
    __tablename__ = "repository_webhook_deliveries"
    __table_args__ = (UniqueConstraint("repository_connector_id", "delivery_id"),)

    repository_webhook_delivery_id: Mapped[str] = id_column("RWH")
    repository_connector_id: Mapped[str] = mapped_column(
        ForeignKey("repository_connectors.repository_connector_id"),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    delivery_id: Mapped[str] = mapped_column(String(160))
    event_type: Mapped[str] = mapped_column(String(120))
    action: Mapped[str | None] = mapped_column(String(120), nullable=True)
    signature_valid: Mapped[bool] = mapped_column(Boolean, default=False)
    state: Mapped[str] = mapped_column(String(80), default="received")
    payload_hash: Mapped[str] = mapped_column(String(128))
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    diagnostics_json: Mapped[dict] = mapped_column(JSON, default=dict)


class RepositoryCheckRun(TimestampMixin, Base):
    __tablename__ = "repository_check_runs"

    repository_check_run_id: Mapped[str] = id_column("RCHK")
    repository_connector_id: Mapped[str] = mapped_column(
        ForeignKey("repository_connectors.repository_connector_id"),
        index=True,
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.project_id"), index=True)
    validation_run_id: Mapped[str | None] = mapped_column(
        ForeignKey("validation_runs.validation_run_id"),
        nullable=True,
    )
    release_gate_result_id: Mapped[str | None] = mapped_column(
        ForeignKey("release_gate_results.release_gate_result_id"),
        nullable=True,
    )
    commit_sha: Mapped[str] = mapped_column(String(120), index=True)
    github_check_run_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    status: Mapped[str] = mapped_column(String(80), default="queued")
    conclusion: Mapped[str | None] = mapped_column(String(80), nullable=True)
    details_url: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    summary: Mapped[str] = mapped_column(Text, default="")
    check_type: Mapped[str] = mapped_column(String(80), default="github_check_run")
    baseline_id: Mapped[str | None] = mapped_column(ForeignKey("baselines.baseline_id"), nullable=True)
    requested_by: Mapped[str | None] = mapped_column(ForeignKey("users.user_id"), nullable=True)
    error_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class BaselineRepositoryRevision(Base):
    __tablename__ = "baseline_repository_revisions"

    baseline_id: Mapped[str] = mapped_column(ForeignKey("baselines.baseline_id"), primary_key=True)
    repository_connector_id: Mapped[str] = mapped_column(
        ForeignKey("repository_connectors.repository_connector_id"),
        primary_key=True,
    )
    repository_revision_id: Mapped[str] = mapped_column(
        ForeignKey("repository_revisions.repository_revision_id")
    )
    commit_sha: Mapped[str] = mapped_column(String(120))
