"""revision integrity and schema version persistence

Revision ID: 0006_revision_integrity
Revises: 0005_blocker_remediation
Create Date: 2026-06-13
"""

from alembic import op
import sqlalchemy as sa


revision = "0006_revision_integrity"
down_revision = "0005_blocker_remediation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    _add_column(
        "artefact_revisions",
        sa.Column("previous_revision_id", sa.String(length=64), nullable=True),
    )
    _add_column(
        "artefact_revisions",
        sa.Column("schema_version", sa.String(length=40), nullable=False, server_default="1.0"),
    )
    _add_column(
        "relationship_revisions",
        sa.Column("previous_revision_id", sa.String(length=64), nullable=True),
    )

    op.execute(
        """
        WITH predecessors AS (
            SELECT artefact_revision_id,
                   lag(artefact_revision_id) OVER (
                       PARTITION BY artefact_id ORDER BY revision_number
                   ) AS previous_revision_id
            FROM artefact_revisions
        )
        UPDATE artefact_revisions AS current
        SET previous_revision_id = predecessors.previous_revision_id
        FROM predecessors
        WHERE current.artefact_revision_id = predecessors.artefact_revision_id
        """
    )
    op.execute(
        """
        WITH predecessors AS (
            SELECT relationship_revision_id,
                   lag(relationship_revision_id) OVER (
                       PARTITION BY relationship_id ORDER BY revision_number
                   ) AS previous_revision_id
            FROM relationship_revisions
        )
        UPDATE relationship_revisions AS current
        SET previous_revision_id = predecessors.previous_revision_id
        FROM predecessors
        WHERE current.relationship_revision_id = predecessors.relationship_revision_id
        """
    )

    if not _has_foreign_key("artefact_revisions", ["previous_revision_id"]):
        op.create_foreign_key(
            "fk_artefact_revisions_previous",
            "artefact_revisions",
            "artefact_revisions",
            ["previous_revision_id"],
            ["artefact_revision_id"],
        )
    if not _has_foreign_key("relationship_revisions", ["previous_revision_id"]):
        op.create_foreign_key(
            "fk_relationship_revisions_previous",
            "relationship_revisions",
            "relationship_revisions",
            ["previous_revision_id"],
            ["relationship_revision_id"],
        )


def downgrade() -> None:
    _drop_foreign_key("relationship_revisions", ["previous_revision_id"])
    _drop_foreign_key("artefact_revisions", ["previous_revision_id"])
    _drop_column("relationship_revisions", "previous_revision_id")
    _drop_column("artefact_revisions", "schema_version")
    _drop_column("artefact_revisions", "previous_revision_id")


def _add_column(table_name: str, column: sa.Column) -> None:
    if not _has_column(table_name, column.name):
        op.add_column(table_name, column)


def _drop_column(table_name: str, column_name: str) -> None:
    if _has_column(table_name, column_name):
        op.drop_column(table_name, column_name)


def _has_column(table_name: str, column_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _has_foreign_key(table_name: str, constrained_columns: list[str]) -> bool:
    inspector = sa.inspect(op.get_bind())
    return any(
        foreign_key["constrained_columns"] == constrained_columns
        for foreign_key in inspector.get_foreign_keys(table_name)
    )


def _drop_foreign_key(table_name: str, constrained_columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    for foreign_key in inspector.get_foreign_keys(table_name):
        if foreign_key["constrained_columns"] == constrained_columns and foreign_key["name"]:
            op.drop_constraint(foreign_key["name"], table_name, type_="foreignkey")
