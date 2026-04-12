from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
import jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.config import get_settings
from aac_backend.models.access import ProjectMembership, Role, User


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))


def create_access_token(user: User, roles: list[str]) -> tuple[str, int]:
    settings = get_settings()
    expires = datetime.now(UTC) + timedelta(hours=settings.jwt_expiry_hours)
    payload: dict[str, Any] = {
        "sub": user.user_id,
        "username": user.username,
        "roles": roles,
        "exp": expires,
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm="HS256")
    return token, settings.jwt_expiry_hours * 3600


def decode_access_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, get_settings().jwt_secret, algorithms=["HS256"])


async def authenticate_user(session: AsyncSession, username: str, password: str) -> User | None:
    user = await session.scalar(select(User).where(User.username == username, User.status == "active"))
    if user and verify_password(password, user.password_hash):
        user.last_login_at = datetime.now(UTC)
        return user
    return None


async def user_roles(session: AsyncSession, user_id: str, project_id: str | None = None) -> list[str]:
    user = await session.get(User, user_id)
    global_roles = set(user.global_roles_json if user else [])
    if project_id is None:
        result = await session.execute(
            select(Role.role_name)
            .join(ProjectMembership, ProjectMembership.role_id == Role.role_id)
            .where(ProjectMembership.user_id == user_id)
        )
    else:
        result = await session.execute(
            select(Role.role_name)
            .join(ProjectMembership, ProjectMembership.role_id == Role.role_id)
            .where(ProjectMembership.user_id == user_id, ProjectMembership.project_id == project_id)
        )
    return sorted(global_roles.union(result.scalars().all()))
