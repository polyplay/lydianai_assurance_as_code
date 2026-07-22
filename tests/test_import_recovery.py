import asyncio
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from aac_backend.models.imports import ImportRun
from aac_backend.models.jobs import Job
from aac_backend.schemas.domain import ImportDecisionSubmit, ImportStart
from aac_backend.services.import_service import (
    _cancel_import_at_boundary,
    _commit_batch_if_boundary,
    mark_import_failed,
    mark_import_interrupted,
    process_import_run,
)


class _Session:
    def __init__(self, objects=None) -> None:
        self.objects = objects or {}
        self.added = []
        self.commits = 0
        self.flushes = 0
        self.rollbacks = 0

    def add(self, value) -> None:
        self.added.append(value)

    async def flush(self) -> None:
        self.flushes += 1

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1

    async def scalar(self, _statement):
        return None

    async def get(self, model, object_id):
        return self.objects.get((model, object_id))


def _run(**overrides) -> ImportRun:
    values = {
        "import_run_id": "IMP_1",
        "project_id": "PROJ_1",
        "source_root": "",
        "state": "parsed",
        "version_update_mode": "ask_user",
        "submitted_by": None,
        "submitted_at": datetime.now(UTC),
        "source_payload_json": {"source_root": "", "sphinx_needs": []},
        "batch_size": 100,
        "last_committed_batch_index": -1,
        "committed_effects_json": {"exists": False, "last_committed_unit": None},
        "summary_json": {},
        "diagnostics_json": [],
    }
    values.update(overrides)
    return ImportRun(**values)


def _job() -> Job:
    return Job(
        job_id="JOB_1",
        project_id="PROJ_1",
        job_type="sphinx_import",
        state="running",
        submitted_at=datetime.now(UTC),
        committed_effects_json={"exists": False, "last_committed_unit": None},
        result_ref_json={},
    )


def test_import_checkpoint_commits_only_at_batch_boundary() -> None:
    session = _Session()
    import_run = _run()
    job = _job()
    summary = {
        "created": 100,
        "changed": 0,
        "unchanged": 0,
        "waiting_for_user": 0,
        "errors": 0,
        "deleted": 0,
        "type_mismatches": 0,
        "conflicts": 0,
        "relationships_created": 0,
    }

    asyncio.run(
        _commit_batch_if_boundary(session, import_run, job, 98, 250, summary)
    )
    assert session.commits == 0

    asyncio.run(
        _commit_batch_if_boundary(session, import_run, job, 99, 250, summary)
    )
    assert session.commits == 1
    assert import_run.last_committed_batch_index == 0
    assert job.last_committed_unit == "batch:0"
    assert job.committed_effects_json["exists"] is True


def test_cooperative_cancellation_reports_committed_effects() -> None:
    session = _Session()
    import_run = _run(
        last_committed_batch_index=1,
        committed_effects_json={"exists": True, "last_committed_unit": "batch:1"},
    )
    job = _job()

    result = asyncio.run(
        _cancel_import_at_boundary(session, import_run, job, actor_user_id=None)
    )

    assert result.state == "cancelled"
    assert job.state == "cancelled"
    assert job.last_committed_unit == "batch:1"
    assert session.commits == 1


def test_failure_rolls_back_active_batch_before_persisting_terminal_state() -> None:
    import_run = _run(
        committed_effects_json={"exists": True, "last_committed_unit": "batch:0"}
    )
    job = _job()
    session = _Session(
        {
            (ImportRun, "IMP_1"): import_run,
            (Job, "JOB_1"): job,
        }
    )

    failed_run, failed_job = asyncio.run(
        mark_import_failed(
            session,
            import_run_id="IMP_1",
            job_id="JOB_1",
            actor_user_id=None,
            error=RuntimeError("batch failed"),
        )
    )

    assert session.rollbacks == 1
    assert session.commits == 1
    assert failed_run.state == "failed"
    assert failed_job.state == "failed"
    assert failed_run.committed_effects_json["last_committed_unit"] == "batch:0"


def test_interruption_returns_run_to_resumable_checkpoint_state() -> None:
    import_run = _run(
        last_committed_batch_index=2,
        committed_effects_json={"exists": True, "last_committed_unit": "batch:2"},
    )
    job = _job()
    session = _Session(
        {
            (ImportRun, "IMP_1"): import_run,
            (Job, "JOB_1"): job,
        }
    )

    interrupted_run, interrupted_job = asyncio.run(
        mark_import_interrupted(
            session,
            import_run_id="IMP_1",
            job_id="JOB_1",
            actor_user_id=None,
            error=ConnectionError("database unavailable"),
            attempt=2,
        )
    )

    assert session.rollbacks == 1
    assert interrupted_run.state == "parsed"
    assert interrupted_run.last_committed_batch_index == 2
    assert interrupted_job.state == "queued"
    assert interrupted_job.error_json["retryable"] is True


def test_terminal_import_is_not_reprocessed() -> None:
    import_run = _run(state="completed")
    data = ImportStart(source_root="", sphinx_needs=[])

    result = asyncio.run(process_import_run(_Session(), import_run, None))

    assert result is import_run
    assert ImportStart(**import_run.source_payload_json) == data


def test_import_decision_contract_rejects_deprecated_value() -> None:
    with pytest.raises(ValidationError):
        ImportDecisionSubmit(
            decisions=[
                {
                    "decision_id": "IMPITEM_1",
                    "decision": "accept_new_version",
                }
            ]
        )
