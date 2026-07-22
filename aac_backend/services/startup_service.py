from aac_backend.database import AsyncSessionLocal
from aac_backend.config import get_settings
from aac_backend.services.profile_service import seed_default_profiles
from aac_backend.services.schema_version_service import assert_database_schema_current
from aac_backend.services.validation_service import seed_rule_catalog


async def initialize_application_state() -> None:
    get_settings().validate_runtime_configuration()
    await assert_database_schema_current()
    async with AsyncSessionLocal() as session:
        await seed_default_profiles(session)
        await seed_rule_catalog(session)
        await session.commit()
