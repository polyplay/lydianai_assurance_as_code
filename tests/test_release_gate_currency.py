import asyncio

import pytest

from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.models.events import DomainEventOutbox
from aac_backend.services.baseline_service import approve_baseline, release_baseline
from aac_backend.services.event_policy import is_blocking_relevant_event_type


class _Session:
    def __init__(self, *, scalar_results, scalars_results) -> None:
        self.scalar_results = list(scalar_results)
        self.scalars_results = list(scalars_results)

    async def scalar(self, _statement):
        return self.scalar_results.pop(0)

    async def scalars(self, _statement):
        return self.scalars_results.pop(0)


def _passed_result() -> ReleaseGateResult:
    return ReleaseGateResult(
        release_gate_result_id="RGATE_1",
        project_id="PROJ_1",
        baseline_id="BASE_1",
        evaluation_number=1,
        triggered_by="USER_1",
        status="passed",
        result="pass",
        evaluation_cutoff_sequence=10,
    )


def _later_event() -> DomainEventOutbox:
    return DomainEventOutbox(
        event_id="EVT_11",
        event_sequence=11,
        event_type="artefact.revised",
        project_id="PROJ_1",
        payload_json={},
    )


def test_blocking_relevance_registry_is_conservative() -> None:
    assert is_blocking_relevant_event_type("artefact.revised")
    assert is_blocking_relevant_event_type("relationship.deleted")
    assert is_blocking_relevant_event_type("validation.run_completed")
    assert not is_blocking_relevant_event_type("job.completed")


def test_approval_marks_gate_stale_when_a_later_blocking_event_exists() -> None:
    baseline = Baseline(
        baseline_id="BASE_1",
        project_id="PROJ_1",
        name="Baseline",
        state="created",
        release_gate_status="passed",
        created_by="USER_1",
    )
    session = _Session(
        scalar_results=[_passed_result()],
        scalars_results=[[_later_event()]],
    )

    with pytest.raises(ValueError, match="stale"):
        asyncio.run(approve_baseline(session, baseline, "USER_1"))

    assert baseline.release_gate_status == "stale"
    assert baseline.gate_stale_event_sequence == 11


def test_release_guard_invalidates_approval_under_row_lock() -> None:
    baseline = Baseline(
        baseline_id="BASE_1",
        project_id="PROJ_1",
        name="Baseline",
        state="approved",
        release_gate_status="passed",
        created_by="USER_1",
    )
    session = _Session(
        scalar_results=[baseline, _passed_result()],
        scalars_results=[[_later_event()]],
    )

    with pytest.raises(ValueError, match="stale"):
        asyncio.run(release_baseline(session, baseline, "USER_1"))

    assert baseline.state == "created"
    assert baseline.release_gate_status == "stale"
    assert baseline.gate_stale_event_sequence == 11
