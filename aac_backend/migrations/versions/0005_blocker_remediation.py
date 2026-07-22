"""blocker remediation persistence

Revision ID: 0005_blocker_remediation
Revises: 0004_repo_approval_contract
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa

from aac_backend.models.events import DomainEventOutbox, EventConsumerReceipt

revision = "0005_blocker_remediation"
down_revision = "0004_repo_approval_contract"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (DomainEventOutbox.__table__, EventConsumerReceipt.__table__):
        table.create(bind=bind, checkfirst=True)

    _add_column("audit_events", sa.Column("role_at_time_of_action", sa.String(240), nullable=False, server_default="system"))
    _add_column("audit_events", sa.Column("operation", sa.String(160), nullable=False, server_default=""))
    _add_column("audit_events", sa.Column("request_id", sa.String(80), nullable=True))

    _add_column("baselines", sa.Column("gate_stale_event_sequence", sa.BigInteger(), nullable=True))
    _add_column("release_gate_results", sa.Column("evaluation_cutoff_sequence", sa.BigInteger(), nullable=False, server_default="0"))

    _add_column("import_runs", sa.Column("source_payload_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column("import_runs", sa.Column("batch_size", sa.Integer(), nullable=False, server_default="100"))
    _add_column("import_runs", sa.Column("total_batches", sa.Integer(), nullable=False, server_default="0"))
    _add_column("import_runs", sa.Column("last_committed_batch_index", sa.Integer(), nullable=False, server_default="-1"))
    _add_column("import_runs", sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column("import_runs", sa.Column("committed_effects_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column("import_runs", sa.Column("correlation_id", sa.String(80), nullable=True))

    _add_column("jobs", sa.Column("cancellation_requested", sa.Boolean(), nullable=False, server_default=sa.false()))
    _add_column("jobs", sa.Column("correlation_id", sa.String(80), nullable=True))
    _add_column("jobs", sa.Column("causation_id", sa.String(80), nullable=True))
    _add_column("jobs", sa.Column("idempotency_key", sa.String(240), nullable=True))
    _add_column("jobs", sa.Column("committed_effects_json", sa.JSON(), nullable=False, server_default=sa.text("'{}'::json")))
    _add_column("jobs", sa.Column("last_committed_unit", sa.String(240), nullable=True))
    if not _has_index("jobs", "uq_jobs_idempotency_key"):
        op.create_index("uq_jobs_idempotency_key", "jobs", ["idempotency_key"], unique=True)


def downgrade() -> None:
    if _has_index("jobs", "uq_jobs_idempotency_key"):
        op.drop_index("uq_jobs_idempotency_key", table_name="jobs")
    for column in (
        "last_committed_unit",
        "committed_effects_json",
        "idempotency_key",
        "causation_id",
        "correlation_id",
        "cancellation_requested",
    ):
        _drop_column("jobs", column)
    for column in (
        "correlation_id",
        "committed_effects_json",
        "cancellation_requested",
        "last_committed_batch_index",
        "total_batches",
        "batch_size",
        "source_payload_json",
    ):
        _drop_column("import_runs", column)
    _drop_column("release_gate_results", "evaluation_cutoff_sequence")
    _drop_column("baselines", "gate_stale_event_sequence")
    for column in ("request_id", "operation", "role_at_time_of_action"):
        _drop_column("audit_events", column)
    bind = op.get_bind()
    for table in (EventConsumerReceipt.__table__, DomainEventOutbox.__table__):
        table.drop(bind=bind, checkfirst=True)


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_index(table_name: str, index_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))
