import os
from pathlib import Path
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="session")
def postgres_database_url() -> str:
    configured_url = os.getenv("AAC_TEST_DATABASE_URL")
    if not configured_url:
        pytest.skip("AAC_TEST_DATABASE_URL is required for PostgreSQL integration tests")

    base_url = make_url(configured_url)
    database_name = f"aac_it_{uuid4().hex}"
    test_url = base_url.set(database=database_name)
    admin_url = base_url.set(drivername="postgresql+psycopg", database="postgres")
    admin_engine = create_engine(
        admin_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )

    with admin_engine.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{database_name}"'))

    migration_environment = {
        **os.environ,
        "AAC_DATABASE_URL": test_url.render_as_string(hide_password=False),
    }
    try:
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            cwd=REPOSITORY_ROOT,
            env=migration_environment,
            capture_output=True,
            text=True,
        )
        if migration.returncode != 0:
            raise RuntimeError(
                "integration database migration failed\n"
                f"stdout:\n{migration.stdout}\n"
                f"stderr:\n{migration.stderr}"
            )
        yield test_url.render_as_string(hide_password=False)
    finally:
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :database_name AND pid <> pg_backend_pid()"
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin_engine.dispose()


@pytest.fixture
async def postgres_session_factory(postgres_database_url: str):
    engine = create_async_engine(postgres_database_url, pool_pre_ping=True)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        yield session_factory
    finally:
        await engine.dispose()
