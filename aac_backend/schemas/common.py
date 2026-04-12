from datetime import UTC, datetime
from typing import Any, Literal
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


ApiStatus = Literal["success", "accepted", "requires_user_decision", "failed"]


class ApiMessage(BaseModel):
    level: Literal["info", "warning", "error"] = "info"
    code: str
    text: str


class ApiEnvelope(BaseModel):
    status: ApiStatus = "success"
    request_id: str = Field(default_factory=lambda: f"REQ_{uuid4().hex}")
    correlation_id: str = Field(default_factory=lambda: f"CORR_{uuid4().hex}")
    messages: list[ApiMessage] = Field(default_factory=list)
    data: Any = None


class OrmModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def utcnow() -> datetime:
    return datetime.now(UTC)
