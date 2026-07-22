from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from aac_backend.services.request_context import current_correlation_id, current_request_id


ApiStatus = Literal["success", "accepted", "requires_user_decision", "failed", "error"]


class ApiMessage(BaseModel):
    level: Literal["info", "warning", "error"] = "info"
    code: str
    text: str


class ApiEnvelope(BaseModel):
    status: ApiStatus = "success"
    request_id: str = Field(default_factory=current_request_id)
    correlation_id: str = Field(default_factory=current_correlation_id)
    messages: list[ApiMessage] = Field(default_factory=list)
    data: Any = None


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: Any = None


class ApiErrorEnvelope(BaseModel):
    status: Literal["error"] = "error"
    request_id: str = Field(default_factory=current_request_id)
    correlation_id: str = Field(default_factory=current_correlation_id)
    error: ApiErrorDetail


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def utcnow() -> datetime:
    return datetime.now(UTC)
