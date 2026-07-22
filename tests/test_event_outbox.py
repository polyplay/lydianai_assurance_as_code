import asyncio

from aac_backend.models.audit import AuditEvent
from aac_backend.models.events import DomainEventOutbox
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.context import CommandContext
from aac_backend.services.event_dispatcher import _consumer_names_for
from aac_backend.services.event_service import append_domain_event, record_event
from aac_backend.services.request_context import establish_request_context


class _Session:
    def __init__(self, scalar_result=None) -> None:
        self.added = []
        self.scalar_result = scalar_result

    def add(self, value) -> None:
        self.added.append(value)

    async def scalar(self, _statement):
        return self.scalar_result


def test_record_event_appends_audit_and_outbox_with_one_context() -> None:
    session = _Session()
    context = CommandContext(
        actor_id="USER_1",
        project_id="PROJ_1",
        roles=("quality_engineer",),
        request_id="REQ_test",
        correlation_id="CORR_test",
    )

    asyncio.run(
        record_event(
            session,
            event_type="artefact.revised",
            project_id="PROJ_1",
            actor_user_id="USER_1",
            affected_artefact_ids=["ART_1"],
            context=context,
        )
    )

    audit = next(value for value in session.added if isinstance(value, AuditEvent))
    outbox = next(
        value for value in session.added if isinstance(value, DomainEventOutbox)
    )
    assert audit.request_id == "REQ_test"
    assert audit.correlation_id == outbox.correlation_id == "CORR_test"
    assert audit.role_at_time_of_action == "quality_engineer"
    assert outbox.payload_json["affected_artefact_ids"] == ["ART_1"]


def test_domain_event_idempotency_reuses_existing_record() -> None:
    existing = DomainEventOutbox(
        event_id="EVT_1",
        event_type="import.completed",
        payload_json={},
    )
    session = _Session(scalar_result=existing)

    result = asyncio.run(
        append_domain_event(
            session,
            event_type="import.completed",
            idempotency_key="import:IMP_1:completed",
        )
    )

    assert result is existing
    assert session.added == []


def test_import_completion_has_idempotent_validation_and_gate_consumers() -> None:
    assert _consumer_names_for("import.completed") == (
        "release_gate_invalidation",
        "import_validation",
    )


def test_api_envelope_uses_current_request_context() -> None:
    establish_request_context(request_id="REQ_api", correlation_id="CORR_api")

    envelope = ApiEnvelope()

    assert envelope.request_id == "REQ_api"
    assert envelope.correlation_id == "CORR_api"
