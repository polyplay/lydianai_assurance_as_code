from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from aac_backend.services.request_context import current_correlation_id, current_request_id


def structured_log(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    message: str | None = None,
    **fields: Any,
) -> None:
    payload: dict[str, Any] = {
        "timestamp_utc": datetime.now(UTC).isoformat(),
        "event": event,
        "message": message or event,
        "request_id": current_request_id(),
        "correlation_id": current_correlation_id(),
    }
    payload.update(_clean_fields(fields))
    logger.log(level, json.dumps(payload, sort_keys=True, default=str))


def request_log_fields(
    *,
    method: str,
    path: str,
    status_code: int | None = None,
    duration_ms: float | None = None,
    client_host: str | None = None,
    path_params: dict[str, Any] | None = None,
    query_string: str | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "method": method,
        "path": path,
        "status_code": status_code,
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        "client_host": client_host,
        "path_params": path_params or {},
        "query_string": query_string or "",
    }
    return _clean_fields(fields)


def job_log_fields(
    *,
    job_id: str,
    job_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    state: str | None = None,
    duration_ms: float | None = None,
    error: Exception | str | None = None,
    result_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "job_id": job_id,
        "job_type": job_type,
        "project_id": project_id,
        "actor_user_id": actor_user_id,
        "state": state,
        "duration_ms": round(duration_ms, 2) if duration_ms is not None else None,
        "error_type": type(error).__name__ if isinstance(error, Exception) else None,
        "error_message": str(error) if error else None,
        "result_ref": result_ref or None,
    }
    return _clean_fields(fields)


def event_log_fields(
    *,
    event_type: str,
    project_id: str | None = None,
    actor_user_id: str | None = None,
    operation: str | None = None,
    affected_artefact_ids: list[str] | None = None,
    affected_relationship_ids: list[str] | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    fields: dict[str, Any] = {
        "event_type": event_type,
        "project_id": project_id,
        "actor_user_id": actor_user_id,
        "operation": operation or event_type,
        "affected_artefact_ids": affected_artefact_ids or [],
        "affected_relationship_ids": affected_relationship_ids or [],
        "payload_keys": sorted(payload.keys()) if payload else [],
    }
    return _clean_fields(fields)


def _clean_fields(fields: dict[str, Any]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, dict):
            cleaned[key] = {k: v for k, v in value.items() if v is not None}
            continue
        if isinstance(value, list):
            cleaned[key] = [item for item in value if item is not None]
            continue
        cleaned[key] = value
    return cleaned
