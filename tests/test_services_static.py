from aac_backend.services.artefact_service import fingerprint
from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.projects import TailoringDecision
from aac_backend.models.validation import ValidationRun
from aac_backend.services.validation_service import ValidationContext, _evaluate_rule


def test_fingerprint_is_stable_for_key_order() -> None:
    assert fingerprint({"b": 2, "a": 1}) == fingerprint({"a": 1, "b": 2})


def test_rule_013_flags_released_requirement_without_passing_test_result() -> None:
    requirement = _artefact(
        "REQ_1",
        "SoftwareRequirement",
        status="released",
        payload={"verification_intent": "test"},
    )
    context = _context([requirement])

    issues = _evaluate_rule(_run(), context, "AAC-RULE-RULE-013")

    assert len(issues) == 1
    assert issues[0].rule_id == "AAC-RULE-RULE-013"
    assert issues[0].affected_artefact_ids_json == ["REQ_1"]


def test_rule_013_passes_with_incoming_passing_test_result() -> None:
    requirement = _artefact("REQ_1", "SoftwareRequirement", status="released")
    result = _artefact("TRES_1", "TestResult", payload={"verdict": "pass"})
    verifies = _relationship("REL_1", "verifies", "TRES_1", "REQ_1")
    context = _context([requirement, result], [verifies])

    issues = _evaluate_rule(_run(), context, "AAC-RULE-RULE-013")

    assert issues == []


def test_rule_025_flags_qm_to_asil_interface_missing_failure_behavior() -> None:
    qm_component = _artefact("COMP_QM", "SoftwareComponent", payload={"criticality_classification": "QM"})
    asil_component = _artefact(
        "COMP_D",
        "SoftwareComponent",
        payload={"criticality_classification": "ASIL_D"},
    )
    interface = _artefact(
        "IF_1",
        "InterfaceContract",
        payload={
            "source_component_id": "COMP_QM",
            "destination_component_id": "COMP_D",
        },
    )
    context = _context([qm_component, asil_component, interface])

    issues = _evaluate_rule(_run(), context, "AAC-RULE-RULE-025")

    assert len(issues) == 1
    assert issues[0].rule_id == "AAC-RULE-RULE-025"


def test_rule_005_honors_approved_not_applicable_tailoring() -> None:
    context = _context(
        [],
        tailoring=[
            TailoringDecision(
                tailoring_decision_id="TAIL_1",
                project_id="PROJ_1",
                scope_type="project",
                scope_id="PROJ_1",
                target_kind="artefact_class",
                target_id="SoftwareSafetyRequirement",
                previous_applicability="mandatory",
                tailored_applicability="not_applicable",
                rationale="Equivalent evidence exists",
                evidence_refs_json=["EVID_1"],
                requested_by="USER_1",
                approved_by="USER_2",
                status="approved",
            )
        ],
    )

    issues = _evaluate_rule(_run(), context, "AAC-RULE-RULE-005")

    assert all("SoftwareSafetyRequirement" not in issue.message for issue in issues)


def _run() -> ValidationRun:
    return ValidationRun(validation_run_id="VRUN_1", project_id="PROJ_1")


def _artefact(
    artefact_id: str,
    artefact_type: str,
    *,
    status: str = "draft",
    payload: dict | None = None,
) -> Artefact:
    return Artefact(
        artefact_id=artefact_id,
        project_id="PROJ_1",
        artefact_type=artefact_type,
        title=artefact_id,
        status=status,
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


def _context(
    artefacts: list[Artefact],
    relationships: list[Relationship] | None = None,
    *,
    tailoring: list[TailoringDecision] | None = None,
) -> ValidationContext:
    return ValidationContext(
        project_id="PROJ_1",
        mode="release_gate",
        artefacts=artefacts,
        relationships=relationships or [],
        tailoring_decisions=tailoring or [],
        open_suspects=[],
        validation_policy={},
        profile_payload={},
    )
