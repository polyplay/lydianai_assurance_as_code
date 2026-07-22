import asyncio
from datetime import UTC, datetime

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import DBAPIError

from aac_backend.models.access import User
from aac_backend.models.artefacts import Artefact, ArtefactRevision
from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.models.events import DomainEventOutbox
from aac_backend.models.imports import ImportRun, ImportRunItem
from aac_backend.models.jobs import Job
from aac_backend.models.projects import Project
from aac_backend.schemas.domain import ArtefactCreate, ArtefactSource, ArtefactUpdate, ImportStart
from aac_backend.services.artefact_service import (
    change_artefact_status,
    create_artefact,
    update_artefact,
)
from aac_backend.services.baseline_service import release_baseline
from aac_backend.services.event_service import record_event
from aac_backend.services.import_service import (
    create_import_run,
    mark_import_interrupted,
    process_import_run,
)

pytestmark = pytest.mark.integration


@pytest.mark.asyncio
async def test_revision_chain_persists_schema_predecessor_and_audit(
    postgres_session_factory,
) -> None:
    async with postgres_session_factory() as session:
        session.add_all(
            [
                User(
                    user_id="USER_REVISION",
                    username="revision-user",
                    display_name="Revision User",
                    email="revision@example.test",
                    status="active",
                    global_roles_json=["admin"],
                ),
                Project(
                    project_id="PROJ_REVISION",
                    project_key="REVISION",
                    name="Revision integrity project",
                ),
            ]
        )
        await session.flush()
        artefact = await create_artefact(
            session,
            "PROJ_REVISION",
            ArtefactCreate(
                artefact_type="SoftwareRequirement",
                title="Revision requirement",
                source=ArtefactSource(
                    source_object_id="REQ_REVISION",
                    source_document="revision.rst",
                ),
                payload={
                    "statement": "The software shall preserve revision history.",
                    "verification_intent": "integration test",
                },
            ),
            "USER_REVISION",
        )
        first_revision_id = artefact.current_revision_id
        artefact = await update_artefact(
            session,
            artefact,
            ArtefactUpdate(
                title="Revised requirement",
                payload={
                    "statement": "The software shall preserve an explicit revision chain.",
                    "verification_intent": "integration test",
                },
                base_revision_id=first_revision_id,
                change_reason="integration test update",
            ),
            "USER_REVISION",
        )
        second_revision_id = artefact.current_revision_id
        artefact = await change_artefact_status(
            session,
            artefact,
            new_status="under_review",
            actor_user_id="USER_REVISION",
            base_revision_id=second_revision_id,
        )
        await session.commit()

    async with postgres_session_factory() as session:
        revisions = list(
            await session.scalars(
                select(ArtefactRevision)
                .where(ArtefactRevision.artefact_id == artefact.artefact_id)
                .order_by(ArtefactRevision.revision_number)
            )
        )
        assert [item.revision_number for item in revisions] == [1, 2, 3]
        assert revisions[0].previous_revision_id is None
        assert revisions[1].previous_revision_id == revisions[0].artefact_revision_id
        assert revisions[2].previous_revision_id == revisions[1].artefact_revision_id
        assert {item.schema_version for item in revisions} == {"1.0"}
        assert all(item.audit_event_id for item in revisions)
        assert revisions[2].metadata_json["status"] == "under_review"


@pytest.mark.asyncio
async def test_import_db_failure_rolls_back_active_batch_and_resumes(
    postgres_session_factory,
) -> None:
    project_id = "PROJ_FAULT"
    needs = [_software_requirement(index) for index in range(1, 5)]
    payload = ImportStart(
        source_root="fault-injection",
        version_update_mode="automatic_new_version",
        sphinx_needs=needs,
    )

    async with postgres_session_factory() as session:
        session.add(
            Project(
                project_id=project_id,
                project_key="FAULT",
                name="Fault injection project",
            )
        )
        await session.flush()
        import_run = await create_import_run(
            session,
            project_id,
            payload,
            actor_user_id=None,
            batch_size=2,
        )
        job = Job(
            job_id="JOB_FAULT",
            project_id=project_id,
            job_type="sphinx_import",
            state="running",
            submitted_at=datetime.now(UTC),
            committed_effects_json={"exists": False, "last_committed_unit": None},
            result_ref_json={
                "resource_type": "ImportRun",
                "resource_id": import_run.import_run_id,
            },
        )
        session.add(job)
        await session.commit()
        import_run_id = import_run.import_run_id

    async with postgres_session_factory.begin() as connection:
        await connection.execute(
            text(
                """
                CREATE FUNCTION aac_fail_second_import_batch()
                RETURNS trigger
                LANGUAGE plpgsql
                AS $$
                BEGIN
                    IF NEW.source_object_id = 'REQ_4' THEN
                        RAISE EXCEPTION 'injected second-batch database failure';
                    END IF;
                    RETURN NEW;
                END;
                $$;
                """
            )
        )
        await connection.execute(
            text(
                """
                CREATE TRIGGER aac_fail_second_import_batch
                BEFORE INSERT ON artefacts
                FOR EACH ROW
                EXECUTE FUNCTION aac_fail_second_import_batch();
                """
            )
        )

    async with postgres_session_factory() as session:
        import_run = await session.get(ImportRun, import_run_id)
        job = await session.get(Job, "JOB_FAULT")
        with pytest.raises(DBAPIError, match="injected second-batch"):
            await process_import_run(
                session,
                import_run,
                actor_user_id=None,
                actor_roles={"admin"},
                job=job,
            )
        interrupted_run, interrupted_job = await mark_import_interrupted(
            session,
            import_run_id=import_run_id,
            job_id="JOB_FAULT",
            actor_user_id=None,
            error=ConnectionError("injected database outage"),
            attempt=1,
        )
        assert interrupted_run is not None
        assert interrupted_job is not None

    async with postgres_session_factory() as session:
        source_ids = set(
            await session.scalars(
                select(Artefact.source_object_id).where(
                    Artefact.project_id == project_id
                )
            )
        )
        item_count = await session.scalar(
            select(func.count())
            .select_from(ImportRunItem)
            .where(ImportRunItem.import_run_id == import_run_id)
        )
        created_event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventOutbox)
            .where(
                DomainEventOutbox.project_id == project_id,
                DomainEventOutbox.event_type == "artefact.created",
            )
        )
        persisted_run = await session.get(ImportRun, import_run_id)
        persisted_job = await session.get(Job, "JOB_FAULT")

        assert source_ids == {"REQ_1", "REQ_2"}
        assert item_count == 2
        assert created_event_count == 2
        assert persisted_run.last_committed_batch_index == 0
        assert persisted_run.summary_json["created"] == 2
        assert persisted_job.state == "queued"
        assert persisted_job.last_committed_unit == "batch:0"

    async with postgres_session_factory.begin() as connection:
        await connection.execute(
            text("DROP TRIGGER aac_fail_second_import_batch ON artefacts")
        )
        await connection.execute(text("DROP FUNCTION aac_fail_second_import_batch()"))

    async with postgres_session_factory() as session:
        import_run = await session.get(ImportRun, import_run_id)
        job = await session.get(Job, "JOB_FAULT")
        completed_run = await process_import_run(
            session,
            import_run,
            actor_user_id=None,
            actor_roles={"admin"},
            job=job,
        )
        assert completed_run.state == "completed"

    async with postgres_session_factory() as session:
        source_ids = set(
            await session.scalars(
                select(Artefact.source_object_id).where(
                    Artefact.project_id == project_id
                )
            )
        )
        item_count = await session.scalar(
            select(func.count())
            .select_from(ImportRunItem)
            .where(ImportRunItem.import_run_id == import_run_id)
        )
        created_event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventOutbox)
            .where(
                DomainEventOutbox.project_id == project_id,
                DomainEventOutbox.event_type == "artefact.created",
            )
        )
        persisted_run = await session.get(ImportRun, import_run_id)

        assert source_ids == {"REQ_1", "REQ_2", "REQ_3", "REQ_4"}
        assert item_count == 4
        assert created_event_count == 4
        assert persisted_run.last_committed_batch_index == 1
        assert persisted_run.summary_json["created"] == 4


@pytest.mark.asyncio
async def test_concurrent_blocking_event_is_ordered_before_release_guard(
    postgres_session_factory,
) -> None:
    user_id = "USER_RELEASE"
    project_id = "PROJ_RELEASE"
    baseline_id = "BASE_RELEASE"

    async with postgres_session_factory() as session:
        session.add_all(
            [
                User(
                    user_id=user_id,
                    username="release-user",
                    display_name="Release User",
                    email="release@example.test",
                    status="active",
                    global_roles_json=["quality_engineer"],
                ),
                Project(
                    project_id=project_id,
                    project_key="RELEASE",
                    name="Concurrent release project",
                ),
            ]
        )
        await session.flush()
        session.add(
            Baseline(
                baseline_id=baseline_id,
                project_id=project_id,
                name="Release baseline",
                state="approved",
                created_by=user_id,
                created_at=datetime.now(UTC),
                approved_by=user_id,
                approved_at=datetime.now(UTC),
                release_gate_status="passed",
            )
        )
        session.add(
            ReleaseGateResult(
                release_gate_result_id="RGATE_RELEASE",
                project_id=project_id,
                baseline_id=baseline_id,
                evaluation_number=1,
                triggered_by=user_id,
                status="passed",
                result="pass",
                started_at=datetime.now(UTC),
                completed_at=datetime.now(UTC),
                evaluation_cutoff_sequence=0,
            )
        )
        await session.commit()

    event_has_lock = asyncio.Event()
    allow_event_commit = asyncio.Event()

    async def append_blocking_event() -> None:
        async with postgres_session_factory() as session:
            async with session.begin():
                await record_event(
                    session,
                    event_type="artefact.revised",
                    project_id=project_id,
                    actor_user_id=user_id,
                    affected_artefact_ids=["ART_CONCURRENT"],
                )
                await session.flush()
                event_has_lock.set()
                await allow_event_commit.wait()

    async def attempt_release() -> str:
        async with postgres_session_factory() as session:
            async with session.begin():
                baseline = await session.get(Baseline, baseline_id)
                try:
                    await release_baseline(session, baseline, user_id)
                except ValueError as exc:
                    return str(exc)
        return "released"

    event_task = asyncio.create_task(append_blocking_event())
    await asyncio.wait_for(event_has_lock.wait(), timeout=5)
    release_task = asyncio.create_task(attempt_release())

    await asyncio.sleep(0.1)
    assert not release_task.done()

    allow_event_commit.set()
    await asyncio.wait_for(event_task, timeout=5)
    release_result = await asyncio.wait_for(release_task, timeout=5)

    assert "stale" in release_result

    async with postgres_session_factory() as session:
        baseline = await session.get(Baseline, baseline_id)
        blocking_event = await session.scalar(
            select(DomainEventOutbox).where(
                DomainEventOutbox.project_id == project_id,
                DomainEventOutbox.event_type == "artefact.revised",
            )
        )
        release_event_count = await session.scalar(
            select(func.count())
            .select_from(DomainEventOutbox)
            .where(
                DomainEventOutbox.project_id == project_id,
                DomainEventOutbox.event_type == "baseline.released",
            )
        )

        assert blocking_event is not None
        assert baseline.state == "created"
        assert baseline.release_gate_status == "stale"
        assert baseline.gate_stale_event_sequence == blocking_event.event_sequence
        assert release_event_count == 0


def _software_requirement(index: int) -> dict:
    return {
        "id": f"REQ_{index}",
        "type": "SoftwareRequirement",
        "title": f"Requirement {index}",
        "content": f"The software shall perform behavior {index}.",
        "verification_method": "test",
        "source_document": "fault_injection.rst",
    }
