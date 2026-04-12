from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.access import Role, User
from aac_backend.schemas.auth import UserCreate
from aac_backend.services.auth_service import hash_password
from aac_backend.services.event_service import record_event

DEFAULT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


async def seed_roles(session: AsyncSession) -> None:
    for role_name in DEFAULT_ROLES:
        existing = await session.scalar(select(Role).where(Role.role_name == role_name))
        if not existing:
            session.add(Role(role_name=role_name))


async def create_user(session: AsyncSession, data: UserCreate, actor_user_id: str | None) -> User:
    await seed_roles(session)
    existing = await session.scalar(select(User).where(User.username == data.username))
    if existing:
        raise ValueError("username already exists")
    user = User(
        username=data.username,
        display_name=data.display_name,
        email=data.email,
        status="active",
        global_roles_json=data.roles,
        password_hash=hash_password(data.password),
        password_updated_at=datetime.now(UTC),
    )
    session.add(user)
    await session.flush()
    await record_event(
        session,
        event_type="user.created",
        actor_user_id=actor_user_id,
        payload={"username": user.username, "roles": data.roles},
    )
    return user
