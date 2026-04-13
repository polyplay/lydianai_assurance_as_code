from datetime import UTC, datetime

import pytest

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.impact import SuspectState
from aac_backend.models.projects import TailoringDecision
from aac_backend.models.validation import ValidationRun
from aac_backend.services.validation_service import RULE_EVALUATORS, ValidationContext, _evaluate_rule

NO_OP_META_RULES = {"AAC-RULE-RULE-090", "AAC-RULE-RULE-091"}


def _run() -> ValidationRun:
    return ValidationRun(validation_run_id="VRUN_1", project_id="PROJ_1")


def _artefact(
    artefact_id: str,
    artefact_type: str,
    *,
    title: str | None = None,
    status: str = "draft",
    payload: dict | None = None,
    current_revision_id: str | None = None,
) -> Artefact:
    return Artefact(
        artefact_id=artefact_id,
        project_id="PROJ_1",
        artefact_type=artefact_type,
        title=artefact_id if title is None else title,
        status=status,
        current_revision_id=current_revision_id,
        source_object_id=artefact_id,
        source_document="unit_test.rst",
        payload_json=payload or {},
    )


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


def _tailoring(*, complete: bool = True, target_id: str = "BuildConfiguration") -> TailoringDecision:
    return TailoringDecision(
        tailoring_decision_id="TAIL_1",
        project_id="PROJ_1",
        scope_type="project" if complete else "",
        scope_id="PROJ_1" if complete else "",
        target_kind="artefact_class",
        target_id=target_id,
        previous_applicability="mandatory" if complete else "",
        tailored_applicability="not_applicable" if complete else "",
        rationale="Equivalent evidence exists" if complete else "",
        evidence_refs_json=["EVID_1"] if complete else [],
        requested_by="USER_1",
        approved_by="USER_2" if complete else None,
        approved_at=datetime.now(UTC) if complete else None,
        status="approved",
    )


def _suspect() -> SuspectState:
    return SuspectState(
        suspect_state_id="SUSP_1",
        project_id="PROJ_1",
        artefact_id="ART_1",
        trigger_artefact_id="ART_UPSTREAM",
        trigger_event_type="artefact.revised",
        propagation_depth=1,
        propagation_path_json=["ART_UPSTREAM", "ART_1"],
        status="open",
        created_at=datetime.now(UTC),
    )


def _context(
    artefacts: list[Artefact],
    relationships: list[Relationship] | None = None,
    *,
    mode: str = "release_gate",
    tailoring: list[TailoringDecision] | None = None,
    suspects: list[SuspectState] | None = None,
    validation_policy: dict | None = None,
    profile_payload: dict | None = None,
) -> ValidationContext:
    return ValidationContext(
        project_id="PROJ_1",
        mode=mode,
        artefacts=artefacts,
        relationships=relationships or [],
        tailoring_decisions=tailoring or [],
        open_suspects=suspects or [],
        validation_policy=validation_policy or {},
        profile_payload=profile_payload or {},
    )


def _mandatory_profile(artefact_type: str) -> dict:
    return {"artefact_classes": {artefact_type: {"applicability": "mandatory"}}}


RULE_CASES = [
    (
        "AAC-RULE-RULE-001",
        lambda: _context(
            [_artefact("A", "SoftwareRequirement"), _artefact("B", "TestResult")],
            [_relationship("R", "verifies", "B", "A")],
        ),
        lambda: _context(
            [_artefact("A", "SoftwareRequirement")],
            [_relationship("R", "verifies", "MISSING", "A")],
        ),
    ),
    (
        "AAC-RULE-RULE-002",
        lambda: _context(
            [_artefact("REQ", "SoftwareRequirement"), _artefact("TR", "TestResult")],
            [_relationship("R", "verifies", "TR", "REQ")],
        ),
        lambda: _context(
            [_artefact("BUILD", "BuildConfiguration"), _artefact("COMP", "SoftwareComponent")],
            [_relationship("R", "verifies", "BUILD", "COMP")],
        ),
    ),
    (
        "AAC-RULE-RULE-003",
        lambda: _context([_artefact("A", "SoftwareRequirement"), _artefact("B", "SoftwareRequirement")]),
        lambda: _context(
            [
                _artefact("A", "SoftwareRequirement"),
                Artefact(
                    artefact_id="B",
                    project_id="PROJ_1",
                    artefact_type="SoftwareRequirement",
                    title="B",
                    status="draft",
                    source_object_id="A",
                    source_document="unit_test.rst",
                    payload_json={},
                ),
            ]
        ),
    ),
    (
        "AAC-RULE-RULE-004",
        lambda: _context([_artefact("A", "SoftwareRequirement")]),
        lambda: _context([_artefact("A", "SoftwareRequirement", title="")]),
    ),
    (
        "AAC-RULE-RULE-005",
        lambda: _context(
            [_artefact("REQ", "SoftwareRequirement")],
            profile_payload=_mandatory_profile("SoftwareRequirement"),
        ),
        lambda: _context([], profile_payload=_mandatory_profile("SoftwareRequirement")),
    ),
    (
        "AAC-RULE-RULE-006",
        lambda: _context([], tailoring=[_tailoring()]),
        lambda: _context([], tailoring=[_tailoring(complete=False)]),
    ),
    (
        "AAC-RULE-RULE-010",
        lambda: _context(
            [_artefact("SSR", "SoftwareSafetyRequirement"), _artefact("COMP", "SoftwareComponent")],
            [_relationship("R", "allocates_to", "SSR", "COMP")],
        ),
        lambda: _context([_artefact("SSR", "SoftwareSafetyRequirement")]),
    ),
    (
        "AAC-RULE-RULE-011",
        lambda: _context(
            [
                _artefact("PARENT", "SoftwareRequirement", payload={"is_parent_requirement": True}),
                _artefact("CHILD", "SoftwareRequirement"),
            ],
            [_relationship("R", "derives_from", "CHILD", "PARENT")],
        ),
        lambda: _context(
            [_artefact("PARENT", "SoftwareRequirement", payload={"is_parent_requirement": True})]
        ),
    ),
    (
        "AAC-RULE-RULE-012",
        lambda: _context([_artefact("REQ", "SoftwareRequirement", payload={"verification_intent": "test"})]),
        lambda: _context([_artefact("REQ", "SoftwareRequirement")]),
    ),
    (
        "AAC-RULE-RULE-013",
        lambda: _context(
            [_artefact("REQ", "SoftwareRequirement", status="released"), _artefact("TR", "TestResult", payload={"verdict": "pass"})],
            [_relationship("R", "verifies", "TR", "REQ")],
        ),
        lambda: _context([_artefact("REQ", "SoftwareRequirement", status="released")]),
    ),
    (
        "AAC-RULE-RULE-014",
        lambda: _context(
            [_artefact("SSR", "SoftwareSafetyRequirement"), _artefact("SG", "SafetyGoal")],
            [_relationship("R", "derives_from", "SSR", "SG")],
        ),
        lambda: _context([_artefact("SSR", "SoftwareSafetyRequirement")]),
    ),
    (
        "AAC-RULE-RULE-020",
        lambda: _context([_artefact("COMP", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"})]),
        lambda: _context([_artefact("COMP", "SoftwareComponent")]),
    ),
    (
        "AAC-RULE-RULE-021",
        lambda: _context(
            [
                _artefact("SSR", "SoftwareSafetyRequirement", status="released"),
                _artefact("COMP", "SoftwareComponent"),
            ],
            [_relationship("R", "allocates_to", "SSR", "COMP")],
        ),
        lambda: _context([_artefact("SSR", "SoftwareSafetyRequirement", status="released")]),
    ),
    (
        "AAC-RULE-RULE-022",
        lambda: _context(
            [
                _artefact("A", "SoftwareComponent"),
                _artefact("B", "SoftwareComponent"),
                _artefact("IF", "InterfaceContract", payload={"source_component_id": "A", "destination_component_id": "B"}),
            ],
            [_relationship("R", "depends_on", "A", "B")],
        ),
        lambda: _context(
            [_artefact("A", "SoftwareComponent"), _artefact("B", "SoftwareComponent")],
            [_relationship("R", "depends_on", "A", "B")],
        ),
    ),
    (
        "AAC-RULE-RULE-023",
        lambda: _context(
            [
                _artefact("A", "SoftwareComponent"),
                _artefact("B", "SoftwareComponent"),
                _artefact("IF", "InterfaceContract", payload={"source_component_id": "A", "destination_component_id": "B"}),
            ]
        ),
        lambda: _context([_artefact("IF", "InterfaceContract", payload={"source_component_id": "A", "destination_component_id": "A"})]),
    ),
    (
        "AAC-RULE-RULE-024",
        lambda: _context(
            [
                _artefact(
                    "IF",
                    "InterfaceContract",
                    payload={"payload_type": "signal", "data_elements": [{"name": "speed", "type": "uint16", "range": "0..250"}]},
                )
            ]
        ),
        lambda: _context([_artefact("IF", "InterfaceContract")]),
    ),
    (
        "AAC-RULE-RULE-025",
        lambda: _context(
            [
                _artefact("QM", "SoftwareComponent", payload={"criticality_classification": "QM"}),
                _artefact("ASIL", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"}),
                _artefact(
                    "IF",
                    "InterfaceContract",
                    payload={
                        "source_component_id": "QM",
                        "destination_component_id": "ASIL",
                        "validity_semantics": {"invalid_value_behavior": "reject"},
                        "error_handling": {"on_invalid": "safe_state"},
                    },
                ),
            ]
        ),
        lambda: _context(
            [
                _artefact("QM", "SoftwareComponent", payload={"criticality_classification": "QM"}),
                _artefact("ASIL", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"}),
                _artefact("IF", "InterfaceContract", payload={"source_component_id": "QM", "destination_component_id": "ASIL"}),
            ]
        ),
    ),
    (
        "AAC-RULE-RULE-026",
        lambda: _context(
            [
                _artefact("IF", "InterfaceContract", payload={"timing": {"period_ms": 10}}),
                _artefact("TS", "TestSpecification", payload={"test_basis_refs": ["IF"], "timing_verification": True}),
            ]
        ),
        lambda: _context([_artefact("IF", "InterfaceContract", payload={"timing": {"period_ms": 10}})]),
    ),
    (
        "AAC-RULE-RULE-027",
        lambda: _context(
            [
                _artefact("A", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"}),
                _artefact("B", "SoftwareComponent", payload={"criticality_classification": "QM"}),
                _artefact("IF", "InterfaceContract", payload={"source_component_id": "A", "destination_component_id": "B"}),
                _artefact("AG", "AssumptionGuaranteeContract"),
            ],
            [_relationship("R", "references", "AG", "IF")],
        ),
        lambda: _context(
            [
                _artefact("A", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"}),
                _artefact("B", "SoftwareComponent", payload={"criticality_classification": "QM"}),
                _artefact("IF", "InterfaceContract", payload={"source_component_id": "A", "destination_component_id": "B"}),
            ]
        ),
    ),
    (
        "AAC-RULE-RULE-030",
        lambda: _context(
            [_artefact("ASM", "Assumption"), _artefact("SAFE", "Safeguard")],
            [_relationship("R", "protects", "SAFE", "ASM")],
        ),
        lambda: _context([_artefact("ASM", "Assumption")]),
    ),
    (
        "AAC-RULE-RULE-031",
        lambda: _context([_artefact("AG", "AssumptionGuaranteeContract", payload={"guarantees": [{"satisfies_refs": ["REQ"]}]})]),
        lambda: _context([_artefact("AG", "AssumptionGuaranteeContract", payload={"guarantees": [{"text": "g"}]})]),
    ),
    (
        "AAC-RULE-RULE-032",
        lambda: _context(
            [
                _artefact("SAFE", "Safeguard"),
                _artefact("COMP", "SoftwareComponent", payload={"criticality_classification": "ASIL_D"}),
            ],
            [_relationship("R", "allocates_to", "SAFE", "COMP")],
        ),
        lambda: _context([_artefact("SAFE", "Safeguard")]),
    ),
    (
        "AAC-RULE-RULE-033",
        lambda: _context(
            [_artefact("SAFE", "Safeguard", status="released"), _artefact("IMPL", "ImplementationItem")],
            [_relationship("R", "implements", "IMPL", "SAFE")],
        ),
        lambda: _context([_artefact("SAFE", "Safeguard", status="released")]),
    ),
    (
        "AAC-RULE-RULE-034",
        lambda: _context(
            [_artefact("SAFE", "Safeguard", status="released"), _artefact("TR", "TestResult", payload={"verdict": "pass"})],
            [_relationship("R", "verifies", "TR", "SAFE")],
        ),
        lambda: _context([_artefact("SAFE", "Safeguard", status="released")]),
    ),
    (
        "AAC-RULE-RULE-040",
        lambda: _context(
            [
                _artefact("UNIT", "SoftwareUnit"),
                _artefact("DESIGN", "SoftwareUnitDesign"),
                _artefact("REQ", "SoftwareRequirement"),
            ],
            [
                _relationship("R1", "satisfies", "UNIT", "DESIGN"),
                _relationship("R2", "implements", "UNIT", "REQ"),
            ],
        ),
        lambda: _context([_artefact("UNIT", "SoftwareUnit")]),
    ),
    (
        "AAC-RULE-RULE-041",
        lambda: _context([_artefact("IMPL", "ImplementationItem", payload={"source_references": [{"reference_type": "source_file", "location": "src/main.c"}]})]),
        lambda: _context([_artefact("IMPL", "ImplementationItem")]),
    ),
    (
        "AAC-RULE-RULE-042",
        lambda: _context([_artefact("BUILD", "BuildConfiguration", payload={"compiler_version": "gcc-13", "build_flags": "-O2", "target_architecture": "arm"})]),
        lambda: _context([]),
    ),
    (
        "AAC-RULE-RULE-043",
        lambda: _context([_artefact("SA", "StaticAnalysisResult")]),
        lambda: _context([]),
    ),
    (
        "AAC-RULE-RULE-044",
        lambda: _context([_artefact("CG", "CodingGuidelineComplianceRecord")]),
        lambda: _context([]),
    ),
    (
        "AAC-RULE-RULE-050",
        lambda: _context([_artefact("REQ", "SoftwareRequirement"), _artefact("TS", "TestSpecification", payload={"test_basis_refs": ["REQ"]})]),
        lambda: _context([_artefact("TS", "TestSpecification", payload={"test_basis_refs": ["MISSING"]})]),
    ),
    (
        "AAC-RULE-RULE-051",
        lambda: _context([_artefact("TC", "TestCase", payload={"expected_result": "ok", "pass_criteria": "equals ok"})]),
        lambda: _context([_artefact("TC", "TestCase")]),
    ),
    (
        "AAC-RULE-RULE-052",
        lambda: _context([_artefact("ENV", "TestEnvironment"), _artefact("TP", "TestProcedure", payload={"test_environment_ref": "ENV"})]),
        lambda: _context([_artefact("TP", "TestProcedure", payload={"test_environment_ref": "MISSING"})]),
    ),
    (
        "AAC-RULE-RULE-053",
        lambda: _context([_artefact("TC", "TestCase"), _artefact("TR", "TestResult", payload={"test_case_ref": "TC"})]),
        lambda: _context([_artefact("TR", "TestResult")]),
    ),
    (
        "AAC-RULE-RULE-054",
        lambda: _context(
            [_artefact("TR", "TestResult", payload={"verdict": "fail"}), _artefact("DEF", "DefectRecord")],
            [_relationship("R", "references", "TR", "DEF")],
        ),
        lambda: _context([_artefact("TR", "TestResult", payload={"verdict": "fail"})]),
    ),
    (
        "AAC-RULE-RULE-055",
        lambda: _context([_artefact("COV", "RequirementsCoverageRecord", payload={"coverage_percentage": 100})]),
        lambda: _context([]),
    ),
    (
        "AAC-RULE-RULE-060",
        lambda: _context(
            [_artefact("CS", "ChangeSet"), _artefact("IA", "ImpactAnalysisResult")],
            [_relationship("R", "references", "CS", "IA")],
        ),
        lambda: _context([_artefact("CS", "ChangeSet")]),
    ),
    (
        "AAC-RULE-RULE-061",
        lambda: _context([_artefact("DEF", "DefectRecord", status="closed")]),
        lambda: _context([_artefact("DEF", "DefectRecord", payload={"status": "open"})]),
    ),
    (
        "AAC-RULE-RULE-062",
        lambda: _context([_artefact("A", "SoftwareRequirement", status="released", current_revision_id="REV_1")], mode="baseline"),
        lambda: _context([_artefact("A", "SoftwareRequirement", status="released")], mode="baseline"),
    ),
    (
        "AAC-RULE-RULE-063",
        lambda: _context([_artefact("CM", "ConfirmationMeasureRecord", payload={"independent_reviewer_id": "USER_2", "primary_author_id": "USER_1"})]),
        lambda: _context([]),
    ),
    (
        "AAC-RULE-RULE-070",
        lambda: _context(
            [
                _artefact("A", "SoftwareRequirement", payload={"security_relevant": True}),
                _artefact("CYB", "CybersecurityManagementEvidence"),
            ],
            [_relationship("R", "references", "A", "CYB")],
            validation_policy={"has_cybersecurity_relevance": True},
        ),
        lambda: _context(
            [_artefact("A", "SoftwareRequirement", payload={"security_relevant": True})],
            validation_policy={"has_cybersecurity_relevance": True},
        ),
    ),
    (
        "AAC-RULE-RULE-071",
        lambda: _context(
            [_artefact("SUMS", "SoftwareUpdateManagementEvidence")],
            validation_policy={"has_software_update_relevance": True},
        ),
        lambda: _context([], validation_policy={"has_software_update_relevance": True}),
    ),
    (
        "AAC-RULE-RULE-080",
        lambda: _context([]),
        lambda: _context([], suspects=[_suspect()]),
    ),
    (
        "AAC-RULE-RULE-081",
        lambda: _context([]),
        lambda: _context([], suspects=[_suspect()]),
    ),
]


def test_rule_matrix_covers_every_non_meta_evaluator() -> None:
    assert {case[0] for case in RULE_CASES} == set(RULE_EVALUATORS) - NO_OP_META_RULES


@pytest.mark.parametrize(("rule_id", "passing_context", "failing_context"), RULE_CASES)
def test_rule_evaluator_has_passing_and_failing_case(
    rule_id: str,
    passing_context,
    failing_context,
) -> None:
    assert _evaluate_rule(_run(), passing_context(), rule_id) == []
    issues = _evaluate_rule(_run(), failing_context(), rule_id)
    assert issues
    assert {issue.rule_id for issue in issues} == {rule_id}


@pytest.mark.parametrize("rule_id", sorted(NO_OP_META_RULES))
def test_meta_rules_are_currently_noop(rule_id: str) -> None:
    assert _evaluate_rule(_run(), _context([]), rule_id) == []
