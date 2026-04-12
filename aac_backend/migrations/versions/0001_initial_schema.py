"""initial logical schema

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-04-12
"""

from alembic import op

from aac_backend.database import Base
from aac_backend.models import all_models  # noqa: F401

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
