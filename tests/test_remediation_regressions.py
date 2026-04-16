import inspect

import pytest
from pydantic import ValidationError

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.jobs import ProjectUpdateLock
from aac_backend.models.projects import ProjectConfiguration
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.schemas.domain import ArtefactStatusTransition
from aac_backend.services import validation_service
from aac_backend.services.artefact_schema_service import (
    apply_schema_override,
    schema_for_artefact_type,
    validate_artefact_payload,
)
from aac_backend.services.artefact_service import change_artefact_status, validate_asil_not_above_project
from aac_backend.services.baseline_service import _release_project_update_lock, _rule_count_for_mode
from aac_backend.services.impact_service import _traverse_dependents
from aac_backend.services.import_service import _canonical_artefact_type, _normalize_payload
from aac_backend.services.traceability_service import _trace_direction
from aac_backend.services.validation_service import ValidationContext, _issue, _meta_rule_issues


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


def test_artefact_schema_registry_enforces_type_specific_required_fields() -> None:
    with pytest.raises(ValueError, match="verification_intent"):
        validate_artefact_payload("SoftwareRequirement", {"statement": "The software shall respond."})

    validate_artefact_payload(
        "SoftwareRequirement",
        {
            "statement": "The software shall respond.",
            "verification_intent": {"methods": ["test"]},
        },
    )


def test_artefact_payload_rejects_asil_above_project_classification() -> None:
    config = ProjectConfiguration(
        project_id="PROJ_1",
        validation_policy_json={
            "project_assurance_configuration": {"asil_level": "ASIL_B"}
        },
    )

    with pytest.raises(ValueError, match="exceeds project maximum ASIL_B"):
        validate_asil_not_above_project(
            "SoftwareSafetyRequirement",
            {"asil_level": "ASIL_D", "statement": "The software shall respond."},
            config,
        )

    validate_asil_not_above_project(
        "SoftwareSafetyRequirement",
        {"asil_level": "ASIL_B", "statement": "The software shall respond."},
        config,
    )


def test_schema_override_rejects_disabling_mandatory_fields_without_mutating_config() -> None:
    config = ProjectConfiguration(project_id="PROJ_1", validation_policy_json={})

    with pytest.raises(ValueError, match="Mandatory fields"):
        apply_schema_override(config, "SoftwareRequirement", {"disabled_fields": ["statement"]})

    assert config.validation_policy_json == {}


def test_schema_override_tails_optional_fields() -> None:
    config = ProjectConfiguration(project_id="PROJ_1", validation_policy_json={})

    schema = apply_schema_override(
        config,
        "SoftwareRequirement",
        {"disabled_fields": ["rationale"]},
    )

    assert "rationale" in schema["disabled_fields"]
    assert "rationale" not in schema_for_artefact_type("SoftwareRequirement", config).enabled_fields


def test_sphinx_need_mapping_normalizes_tool_fields_to_canonical_payload() -> None:
    raw_need = {
        "id": "SSR_1",
        "type": "sw_safety_req",
        "title": "Safety requirement",
        "content": "The software shall detect the fault.",
        "asil": "ASIL_D",
        "verification_method": "test",
    }

    assert _canonical_artefact_type(raw_need) == "SoftwareSafetyRequirement"
    payload = _normalize_payload(raw_need, "SoftwareSafetyRequirement")
    assert payload["statement"] == "The software shall detect the fault."
    assert payload["asil_level"] == "ASIL_D"
    assert payload["verification_intent"] == {"methods": ["test"]}


def test_transitive_traceability_returns_chain_depth_and_path() -> None:
    relationships = [
        _relationship("R1", "derives_from", "REQ_2", "REQ_1"),
        _relationship("R2", "verifies", "TEST_1", "REQ_2"),
    ]

    traced = _trace_direction(relationships, "TEST_1", "forward")

    assert [edge["target_artefact_id"] for edge in traced] == ["REQ_2", "REQ_1"]
    assert traced[1]["depth"] == 2
    assert [edge["relationship_id"] for edge in traced[1]["path"]] == ["R2", "R1"]


def test_meta_rules_raise_release_gate_issue_for_critical_blocker() -> None:
    run = validation_service.ValidationRun(validation_run_id="VRUN_1", project_id="PROJ_1")
    context = ValidationContext(
        project_id="PROJ_1",
        mode="release_gate",
        artefacts=[],
        relationships=[],
        tailoring_decisions=[],
        open_suspects=[],
        validation_policy={},
        profile_payload={},
    )
    blocking_issue = _issue(run, "AAC-RULE-RULE-001", "Broken trace", [])

    meta_issues = _meta_rule_issues(run, context, [blocking_issue])

    assert [issue.rule_id for issue in meta_issues] == ["AAC-RULE-RULE-091"]


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
