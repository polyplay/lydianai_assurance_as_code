from pydantic import BaseModel, EmailStr

from aac_backend.schemas.common import OrmModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int


class UserCreate(BaseModel):
    username: str
    display_name: str
    email: EmailStr
    password: str
    roles: list[str] = []


class UserRead(OrmModel):
    user_id: str
    username: str
    display_name: str
    email: str
    status: str


class PasswordChange(BaseModel):
    current_password: str
    new_password: str


class PasswordReset(BaseModel):
    new_password: str
