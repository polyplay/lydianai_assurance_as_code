import asyncio
import json

from fastapi.testclient import TestClient

import aac_backend.main as main_module
from aac_backend.models.audit import AuditEvent
from aac_backend.models.events import DomainEventOutbox
from aac_backend.services.event_service import record_event
from aac_backend.services.request_context import establish_request_context


class _Session:
    def __init__(self) -> None:
        self.added = []

    def add(self, value) -> None:
        self.added.append(value)

    async def scalar(self, _statement):
        return None


def test_record_event_emits_structured_log(caplog) -> None:
    establish_request_context(request_id="REQ_test", correlation_id="CORR_test")
    session = _Session()

    caplog.set_level("INFO")
    asyncio.run(
        record_event(
            session,
            event_type="artefact.revised",
            project_id="PROJ_1",
            actor_user_id="USER_1",
            payload={"summary": "changed", "secret": "redacted"},
            affected_artefact_ids=["ART_1"],
            affected_relationship_ids=["REL_1"],
        )
    )

    audit = next(value for value in session.added if isinstance(value, AuditEvent))
    outbox = next(value for value in session.added if isinstance(value, DomainEventOutbox))
    assert audit.request_id == "REQ_test"
    assert outbox.correlation_id == "CORR_test"
    payload = [json.loads(record.message) for record in caplog.records if record.name.endswith("event_service")]
    recorded = next(item for item in payload if item["event"] == "audit.event.recorded")
    assert recorded["project_id"] == "PROJ_1"
    assert recorded["actor_user_id"] == "USER_1"
    assert recorded["affected_artefact_ids"] == ["ART_1"]
    assert recorded["payload_keys"] == ["secret", "summary"]


def test_request_logging_includes_request_and_correlation_ids(monkeypatch, caplog) -> None:
    async def _noop():
        return None

    monkeypatch.setattr(main_module, "initialize_application_state", _noop)
    caplog.set_level("INFO")

    app = main_module.create_app()
    with TestClient(app) as client:
        response = client.get("/api/v1/openapi.json")

    assert response.status_code == 200
    records = [
        json.loads(record.message)
        for record in caplog.records
        if record.name.endswith("main")
    ]
    completed = next(item for item in records if item["event"] == "http.request.completed")
    assert completed["method"] == "GET"
    assert completed["path"] == "/api/v1/openapi.json"
    assert completed["duration_ms"] >= 0
    assert response.headers["X-Request-ID"].startswith("REQ_")
    assert response.headers["X-Correlation-ID"].startswith("CORR_")
