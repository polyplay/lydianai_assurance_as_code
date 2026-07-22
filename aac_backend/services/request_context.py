from contextvars import ContextVar
from uuid import uuid4

_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)
_correlation_id: ContextVar[str | None] = ContextVar("correlation_id", default=None)


def establish_request_context(
    *,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> tuple[str, str]:
    effective_request_id = request_id or f"REQ_{uuid4().hex}"
    effective_correlation_id = correlation_id or f"CORR_{uuid4().hex}"
    _request_id.set(effective_request_id)
    _correlation_id.set(effective_correlation_id)
    return effective_request_id, effective_correlation_id


def current_request_id() -> str:
    request_id = _request_id.get()
    if request_id is None:
        request_id, _ = establish_request_context()
    return request_id


def current_correlation_id() -> str:
    correlation_id = _correlation_id.get()
    if correlation_id is None:
        _, correlation_id = establish_request_context()
    return correlation_id
