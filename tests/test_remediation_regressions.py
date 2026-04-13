import inspect

import pytest
from pydantic import ValidationError

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.jobs import ProjectUpdateLock
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.schemas.domain import ArtefactStatusTransition
from aac_backend.services import validation_service
from aac_backend.services.artefact_service import change_artefact_status
from aac_backend.services.baseline_service import _release_project_update_lock, _rule_count_for_mode
from aac_backend.services.impact_service import _traverse_dependents


def test_run_validation_does_not_seed_rule_catalog_in_hot_path() -> None:
    source = inspect.getsource(validation_service.run_validation)
    assert "seed_rule_catalog(" not in source


def test_rule_count_for_mode_excludes_project_disabled_rules() -> None:
    release_gate_rule_id = next(
        rule_id
        for rule_id, rule in RULE_CATALOG.items()
        if "release_gate" in rule.execution_modes
    )
    base_count = _rule_count_for_mode("release_gate")

    count = _rule_count_for_mode(
        "release_gate",
        {"rules": {release_gate_rule_id: {"enabled": False}}},
    )

    assert count == base_count - 1


def test_status_transition_schema_rejects_unknown_status() -> None:
    with pytest.raises(ValidationError):
        ArtefactStatusTransition(status="ready_for_launch")


@pytest.mark.asyncio
async def test_status_service_rejects_invalid_lifecycle_jump() -> None:
    artefact = Artefact(
        artefact_id="ART_1",
        project_id="PROJ_1",
        artefact_type="SoftwareRequirement",
        title="Requirement",
        status="draft",
        source_object_id="REQ_1",
        source_document="unit_test.rst",
        payload_json={},
    )

    with pytest.raises(ValueError, match="draft -> released"):
        await change_artefact_status(
            _NoLockSession(),
            artefact,
            new_status="released",
            actor_user_id="USER_1",
        )


@pytest.mark.asyncio
async def test_impact_traversal_preloads_relationships_once() -> None:
    session = _RelationshipSession(
        [
            _relationship("R1", "allocates_to", "A", "B"),
            _relationship("R2", "verifies", "C", "B"),
            _relationship("R3", "depends_on", "B", "D"),
        ]
    )

    traversal = await _traverse_dependents(session, "PROJ_1", "A")

    assert session.scalars_calls == 1
    assert [node["artefact_id"] for node in traversal] == ["B", "D", "C"]


@pytest.mark.asyncio
async def test_project_update_lock_cleanup_deletes_and_flushes() -> None:
    session = _LockSession(ProjectUpdateLock(project_id="PROJ_1", lock_owner_job_id="JOB_1"))

    await _release_project_update_lock(session, "PROJ_1")

    assert session.deleted is True
    assert session.flushed is True


class _NoLockSession:
    async def get(self, model, key):
        return None


class _RelationshipSession:
    def __init__(self, relationships: list[Relationship]) -> None:
        self.relationships = relationships
        self.scalars_calls = 0

    async def scalars(self, statement):
        self.scalars_calls += 1
        return self.relationships


class _LockSession:
    def __init__(self, lock: ProjectUpdateLock | None) -> None:
        self.lock = lock
        self.deleted = False
        self.flushed = False

    async def get(self, model, key):
        return self.lock

    async def delete(self, lock) -> None:
        self.deleted = True
        self.lock = None

    async def flush(self) -> None:
        self.flushed = True


def _relationship(
    relationship_id: str,
    relationship_type: str,
    source_artefact_id: str,
    target_artefact_id: str,
) -> Relationship:
    return Relationship(
        relationship_id=relationship_id,
        project_id="PROJ_1",
        relationship_type=relationship_type,
        source_artefact_id=source_artefact_id,
        target_artefact_id=target_artefact_id,
    )
