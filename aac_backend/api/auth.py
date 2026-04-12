from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, get_current_user, global_role_dependency
from aac_backend.database import get_session
from aac_backend.models.access import User
from aac_backend.schemas.auth import (
    LoginRequest,
    PasswordChange,
    PasswordReset,
    TokenResponse,
    UserCreate,
    UserRead,
)
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.auth_service import (
    authenticate_user,
    create_access_token,
    hash_password,
    user_roles,
    verify_password,
)
from aac_backend.services.user_service import create_user

router = APIRouter(tags=["auth"])


@router.post("/auth/login", response_model=ApiEnvelope)
async def login(payload: LoginRequest, session: AsyncSession = Depends(get_session)) -> ApiEnvelope:
    user = await authenticate_user(session, payload.username, payload.password)
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid username or password")
    roles = await user_roles(session, user.user_id)
    token, expires = create_access_token(user, roles)
    await session.commit()
    return ApiEnvelope(data=TokenResponse(access_token=token, expires_in_seconds=expires))


@router.post("/auth/logout", response_model=ApiEnvelope)
async def logout(_: CurrentUser = Depends(get_current_user)) -> ApiEnvelope:
    return ApiEnvelope(data={"logged_out": True})


@router.get("/users/me", response_model=ApiEnvelope)
async def me(current: CurrentUser = Depends(get_current_user)) -> ApiEnvelope:
    return ApiEnvelope(data={"user": UserRead.model_validate(current.user), "roles": current.global_roles})


@router.get("/users", response_model=ApiEnvelope)
async def list_users(
    _: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    users = list(await session.scalars(select(User)))
    return ApiEnvelope(data=[UserRead.model_validate(user) for user in users])


@router.post("/users", response_model=ApiEnvelope)
async def create_user_endpoint(
    payload: UserCreate,
    current: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    user = await create_user(session, payload, current.user.user_id)
    await session.commit()
    return ApiEnvelope(data=UserRead.model_validate(user))


@router.put("/users/{user_id}", response_model=ApiEnvelope)
async def update_user(
    user_id: str,
    payload: dict,
    _: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.display_name = payload.get("display_name", user.display_name)
    user.email = payload.get("email", user.email)
    user.global_roles_json = payload.get("roles", user.global_roles_json)
    user.status = payload.get("status", user.status)
    await session.commit()
    return ApiEnvelope(data=UserRead.model_validate(user))


@router.put("/users/{user_id}/deactivate", response_model=ApiEnvelope)
async def deactivate_user(
    user_id: str,
    _: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.status = "inactive"
    await session.commit()
    return ApiEnvelope(data=UserRead.model_validate(user))


@router.post("/users/{user_id}/password-reset", response_model=ApiEnvelope)
async def password_reset(
    user_id: str,
    payload: PasswordReset,
    _: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    user.password_hash = hash_password(payload.new_password)
    user.password_updated_at = datetime.now(UTC)
    await session.commit()
    return ApiEnvelope(data={"user_id": user.user_id, "password_updated": True})


@router.post("/users/me/password", response_model=ApiEnvelope)
async def password_change(
    payload: PasswordChange,
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    user = await session.get(User, current.user.user_id)
    if not user or not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=403, detail="Current password is invalid")
    user.password_hash = hash_password(payload.new_password)
    user.password_updated_at = datetime.now(UTC)
    await session.commit()
    return ApiEnvelope(data={"user_id": user.user_id, "password_updated": True})
