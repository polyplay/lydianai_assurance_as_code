from alembic.runtime.migration import MigrationContext

from aac_backend.database import engine

EXPECTED_SCHEMA_REVISION = "0004_repo_approval_contract"


async def assert_database_schema_current() -> None:
    async with engine.connect() as connection:
        current_revision = await connection.run_sync(_current_revision)
    if current_revision != EXPECTED_SCHEMA_REVISION:
        raise RuntimeError(
            "database schema revision mismatch: "
            f"expected {EXPECTED_SCHEMA_REVISION}, got {current_revision or 'unversioned'}"
        )


def _current_revision(sync_connection) -> str | None:
    context = MigrationContext.configure(sync_connection)
    return context.get_current_revision()
