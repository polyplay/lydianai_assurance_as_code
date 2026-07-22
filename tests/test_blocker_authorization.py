import asyncio
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from aac_backend.api.imports import cancel_import
from aac_backend.api.jobs import _job_data, cancel_job, get_job
from aac_backend.api.dependencies import CurrentUser
from aac_backend.models.imports import ImportRun
from aac_backend.models.jobs import Job
from aac_backend.models.baselines import Baseline
from aac_backend.services.repository_integration_service import (
    publish_release_approval_for_baseline,
)


class _Session:
    def __init__(self, value) -> None:
        self.value = value

    async def get(self, _model, _object_id):
        return self.value


def _current(user_id: str, global_roles=None) -> CurrentUser:
    return CurrentUser(
        user=SimpleNamespace(user_id=user_id),
        global_roles=global_roles or [],
    )


def test_job_detail_and_cancellation_are_requester_or_admin_only() -> None:
    job = Job(
        job_id="JOB_1",
        project_id="PROJ_1",
        job_type="validation_run",
        state="running",
        submitted_by="USER_OWNER",
        result_ref_json={"secret": "result"},
        error_json={"secret": "error"},
    )
    session = _Session(job)

    with pytest.raises(HTTPException) as read_error:
        asyncio.run(get_job("JOB_1", _current("USER_OTHER"), session))
    with pytest.raises(HTTPException) as cancel_error:
        asyncio.run(cancel_job("JOB_1", _current("USER_OTHER"), session))

    assert read_error.value.status_code == 403
    assert cancel_error.value.status_code == 403


def test_project_job_projection_redacts_sensitive_detail() -> None:
    job = Job(
        job_id="JOB_1",
        project_id="PROJ_1",
        job_type="validation_run",
        state="failed",
        submitted_by="USER_OWNER",
        result_ref_json={"resource_id": "VAL_1"},
        error_json={"message": "internal detail"},
    )

    projected = _job_data(job, include_sensitive=False)

    assert "result_ref" not in projected
    assert "error" not in projected


def test_import_cancellation_is_requester_or_admin_only() -> None:
    import_run = ImportRun(
        import_run_id="IMP_1",
        project_id="PROJ_1",
        state="running",
        submitted_by="USER_OWNER",
    )

    with pytest.raises(HTTPException) as error:
        asyncio.run(
            cancel_import(
                "PROJ_1",
                "IMP_1",
                _current("USER_OTHER"),
                _Session(import_run),
            )
        )

    assert error.value.status_code == 403


def test_repository_publication_requires_released_baseline() -> None:
    baseline = Baseline(
        baseline_id="BASE_1",
        project_id="PROJ_1",
        name="Baseline",
        state="approved",
        created_by="USER_1",
    )

    with pytest.raises(ValueError, match="released baseline"):
        asyncio.run(
            publish_release_approval_for_baseline(
                _Session(None),
                baseline=baseline,
                actor_user_id="USER_1",
            )
        )
