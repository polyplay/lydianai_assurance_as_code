"""impact suspect and job support

Revision ID: 0002_impact_suspect_jobs
Revises: 0001_initial_schema
Create Date: 2026-04-12
"""

from alembic import op

from aac_backend.models.impact import (
    ImpactAnalysisItem,
    ImpactAnalysisRun,
    SuspectState,
    TestResultRecord,
)

revision = "0002_impact_suspect_jobs"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        ImpactAnalysisRun.__table__,
        ImpactAnalysisItem.__table__,
        SuspectState.__table__,
        TestResultRecord.__table__,
    ):
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        TestResultRecord.__table__,
        SuspectState.__table__,
        ImpactAnalysisItem.__table__,
        ImpactAnalysisRun.__table__,
    ):
        table.drop(bind=bind, checkfirst=True)
