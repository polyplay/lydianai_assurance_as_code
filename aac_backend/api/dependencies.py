from collections.abc import Callable
from dataclasses import dataclass

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.database import get_session
from aac_backend.models.access import User
from aac_backend.services.auth_service import decode_access_token, user_roles


@dataclass(frozen=True)
class CurrentUser:
    user: User
    global_roles: list[str]


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1]
    try:
        payload = decode_access_token(token)
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc
    user = await session.get(User, payload["sub"])
    if user is None or user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")
    roles = await user_roles(session, user.user_id)
    return CurrentUser(user=user, global_roles=roles)


async def require_project_roles(
    project_id: str,
    current: CurrentUser,
    session: AsyncSession,
    allowed_roles: set[str],
) -> None:
    roles = await user_roles(session, current.user.user_id, project_id)
    if "admin" in current.global_roles or "admin" in roles:
        return
    if allowed_roles.intersection(roles):
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


def project_role_dependency(*allowed_roles: str) -> Callable:
    async def dependency(
        project_id: str,
        current: CurrentUser = Depends(get_current_user),
        session: AsyncSession = Depends(get_session),
    ) -> CurrentUser:
        await require_project_roles(session=session, project_id=project_id, current=current, allowed_roles=set(allowed_roles))
        return current

    return dependency


def global_role_dependency(*allowed_roles: str) -> Callable:
    async def dependency(current: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if set(allowed_roles).intersection(current.global_roles):
            return current
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")

    return dependency
