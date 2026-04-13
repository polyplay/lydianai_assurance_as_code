from aac_backend.database import AsyncSessionLocal
from aac_backend.services.schema_version_service import assert_database_schema_current
from aac_backend.services.validation_service import seed_rule_catalog


async def initialize_application_state() -> None:
    await assert_database_schema_current()
    async with AsyncSessionLocal() as session:
        await seed_rule_catalog(session)
        await session.commit()
