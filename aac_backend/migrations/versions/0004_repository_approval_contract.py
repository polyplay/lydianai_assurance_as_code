"""repository approval contract

Revision ID: 0004_repo_approval_contract
Revises: 0003_repository_integrations
Create Date: 2026-04-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0004_repo_approval_contract"
down_revision = "0003_repository_integrations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if not _has_column("repository_connectors", "auth_mode"):
        op.add_column(
            "repository_connectors",
            sa.Column("auth_mode", sa.String(length=80), nullable=False, server_default="github_app"),
        )
    if not _has_column("repository_connectors", "access_token_secret_id"):
        op.add_column(
            "repository_connectors",
            sa.Column("access_token_secret_id", sa.String(length=64), nullable=True),
        )
        op.create_foreign_key(
            "fk_repository_connectors_access_token_secret_id",
            "repository_connectors",
            "connector_secrets",
            ["access_token_secret_id"],
            ["connector_secret_id"],
        )
    if not _has_column("repository_check_runs", "check_type"):
        op.add_column(
            "repository_check_runs",
            sa.Column("check_type", sa.String(length=80), nullable=False, server_default="github_check_run"),
        )
    if not _has_column("repository_check_runs", "baseline_id"):
        op.add_column(
            "repository_check_runs",
            sa.Column("baseline_id", sa.String(length=64), nullable=True),
        )
        op.create_foreign_key(
            "fk_repository_check_runs_baseline_id",
            "repository_check_runs",
            "baselines",
            ["baseline_id"],
            ["baseline_id"],
        )


def downgrade() -> None:
    if _has_fk("repository_check_runs", "fk_repository_check_runs_baseline_id"):
        op.drop_constraint("fk_repository_check_runs_baseline_id", "repository_check_runs", type_="foreignkey")
    if _has_column("repository_check_runs", "baseline_id"):
        op.drop_column("repository_check_runs", "baseline_id")
    if _has_column("repository_check_runs", "check_type"):
        op.drop_column("repository_check_runs", "check_type")
    if _has_fk("repository_connectors", "fk_repository_connectors_access_token_secret_id"):
        op.drop_constraint(
            "fk_repository_connectors_access_token_secret_id",
            "repository_connectors",
            type_="foreignkey",
        )
    if _has_column("repository_connectors", "access_token_secret_id"):
        op.drop_column("repository_connectors", "access_token_secret_id")
    if _has_column("repository_connectors", "auth_mode"):
        op.drop_column("repository_connectors", "auth_mode")


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_fk(table_name: str, fk_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(fk.get("name") == fk_name for fk in inspector.get_foreign_keys(table_name))
