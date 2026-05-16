"""repository integration support

Revision ID: 0003_repository_integrations
Revises: 0002_impact_suspect_jobs
Create Date: 2026-04-19
"""

from alembic import op

from aac_backend.models.repository_integrations import (
    BaselineRepositoryRevision,
    ConnectorSecret,
    RepositoryCheckRun,
    RepositoryConnector,
    RepositoryRevision,
    RepositoryScanRun,
    RepositoryWebhookDelivery,
)

revision = "0003_repository_integrations"
down_revision = "0002_impact_suspect_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in (
        ConnectorSecret.__table__,
        RepositoryConnector.__table__,
        RepositoryScanRun.__table__,
        RepositoryRevision.__table__,
        RepositoryWebhookDelivery.__table__,
        RepositoryCheckRun.__table__,
        BaselineRepositoryRevision.__table__,
    ):
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in (
        BaselineRepositoryRevision.__table__,
        RepositoryCheckRun.__table__,
        RepositoryWebhookDelivery.__table__,
        RepositoryRevision.__table__,
        RepositoryScanRun.__table__,
        RepositoryConnector.__table__,
        ConnectorSecret.__table__,
    ):
        table.drop(bind=bind, checkfirst=True)
