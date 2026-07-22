from aac_backend.services.assurance_configuration_service import (
    assurance_configuration_from_profile_id,
    derive_artefact_applicability,
    derive_profile_payload,
    derive_rule_policy,
    derive_validation_policy,
    normalize_assurance_configuration,
)
from aac_backend.services.project_service import aspice_tailoring_changes


def test_asil_b_cl2_has_smaller_mandatory_set_than_asil_d_cl3() -> None:
    asil_b_cl2 = derive_artefact_applicability(
        {
            "asil_level": "ASIL_B",
            "aspice_default_capability_level": 2,
            "r155_applicable": False,
            "r156_applicable": False,
        }
    )
    asil_d_cl3 = derive_artefact_applicability(
        {
            "asil_level": "ASIL_D",
            "aspice_default_capability_level": 3,
            "r155_applicable": False,
            "r156_applicable": False,
        }
    )

    assert "ConfirmationMeasureRecord" not in asil_b_cl2["mandatory_artefact_types"]
    assert "ProcessComplianceRecord" not in asil_b_cl2["mandatory_artefact_types"]
    assert "ConfirmationMeasureRecord" in asil_d_cl3["mandatory_artefact_types"]
    assert "ProcessComplianceRecord" in asil_d_cl3["mandatory_artefact_types"]
    assert len(asil_b_cl2["mandatory_artefact_types"]) < len(asil_d_cl3["mandatory_artefact_types"])


def test_cl3_process_target_adds_pa31_pa32_evidence() -> None:
    cl2 = derive_artefact_applicability(
        {"asil_level": "QM", "aspice_default_capability_level": 2}
    )
    cl3 = derive_artefact_applicability(
        {"asil_level": "QM", "aspice_default_capability_level": 2, "aspice_process_overrides": {"SWE.1": 3}}
    )

    assert "ProcessComplianceRecord" not in cl2["mandatory_artefact_types"]
    assert "ASPICEScopeDecision" in cl3["mandatory_artefact_types"]
    assert "ProcessComplianceRecord" in cl3["mandatory_artefact_types"]


def test_r155_and_r156_flags_add_regulatory_work_products_and_rules() -> None:
    payload = derive_profile_payload(
        {
            "asil_level": "ASIL_B",
            "aspice_default_capability_level": 2,
            "r155_applicable": True,
            "r156_applicable": True,
        }
    )

    artefacts = payload["artefact_classes"]
    rules = payload["rules"]
    assert artefacts["ThreatAnalysisRiskAssessment"]["applicability"] == "mandatory"
    assert artefacts["CybersecurityRequirement"]["applicability"] == "mandatory"
    assert artefacts["SoftwareUpdateManagementEvidence"]["applicability"] == "mandatory"
    assert artefacts["SoftwareVersionRecord"]["applicability"] == "mandatory"
    assert rules["AAC-RULE-RULE-070"]["enabled"] is True
    assert rules["AAC-RULE-RULE-071"]["enabled"] is True


def test_relevant_first_visibility_hides_optional_catalogue_by_default() -> None:
    model = derive_artefact_applicability(
        {
            "asil_level": "ASIL_B",
            "aspice_default_capability_level": 2,
            "visibility_policy": "relevant_first",
        }
    )

    assert "SoftwareRequirement" in model["visible_artefact_types"]
    assert "SoftwareBillOfMaterials" not in model["visible_artefact_types"]
    assert "SoftwareBillOfMaterials" in model["not_applicable_artefact_types"]


def test_validation_policy_carries_derived_rule_enablement_and_scope_flags() -> None:
    config = normalize_assurance_configuration(
        {"asil_level": "QM", "r155_applicable": True, "r156_applicable": False}
    )
    policy = derive_validation_policy(config, existing_policy={"artefact_schemas": {"SoftwareRequirement": {}}})
    rules = derive_rule_policy(config)

    assert policy["artefact_schemas"] == {"SoftwareRequirement": {}}
    assert policy["has_cybersecurity_relevance"] is True
    assert policy["has_software_update_relevance"] is False
    assert policy["rules"]["AAC-RULE-RULE-070"]["enabled"] is True
    assert policy["rules"]["AAC-RULE-RULE-071"]["enabled"] is False
    assert policy["rules"] == rules


def test_legacy_profile_id_defaults_select_reasonable_aspice_target() -> None:
    asil_b = assurance_configuration_from_profile_id("ASIL_B_DEFAULT")
    asil_d = assurance_configuration_from_profile_id("ASIL_D_DEFAULT")

    assert asil_b["asil_level"] == "ASIL_B"
    assert asil_b["aspice_default_capability_level"] == 2
    assert asil_d["aspice_default_capability_level"] == 3


def test_process_capability_targets_derive_from_default_and_overrides() -> None:
    config = normalize_assurance_configuration(
        {
            "asil_level": "ASIL_C",
            "aspice_default_capability_level": 2,
            "aspice_scoped_processes": ["SWE.1", "SWE.2"],
            "aspice_process_overrides": {"SWE.2": 3},
        }
    )

    assert config["aspice_process_capability_targets"] == {"SWE.1": 2, "SWE.2": 3}


def test_aspice_tailoring_changes_capture_scope_default_and_process_targets() -> None:
    previous = normalize_assurance_configuration(
        {
            "asil_level": "ASIL_C",
            "aspice_default_capability_level": 2,
            "aspice_scoped_processes": ["SWE.1", "SWE.2"],
        }
    )
    updated = normalize_assurance_configuration(
        {
            "asil_level": "ASIL_C",
            "aspice_default_capability_level": 3,
            "aspice_scoped_processes": ["SWE.2", "SWE.3"],
            "aspice_process_overrides": {"SWE.2": 2},
        }
    )

    assert aspice_tailoring_changes(previous, updated) == [
        {
            "target_kind": "aspice_default_capability",
            "target_id": "ASPICE_DEFAULT_CAPABILITY",
            "previous": "CL2",
            "current": "CL3",
        },
        {
            "target_kind": "aspice_process_scope",
            "target_id": "SWE.3",
            "previous": "out_of_scope",
            "current": "in_scope",
        },
        {
            "target_kind": "aspice_process_capability",
            "target_id": "SWE.3",
            "previous": "not_applicable",
            "current": "CL3",
        },
        {
            "target_kind": "aspice_process_scope",
            "target_id": "SWE.1",
            "previous": "in_scope",
            "current": "out_of_scope",
        },
        {
            "target_kind": "aspice_process_capability",
            "target_id": "SWE.1",
            "previous": "CL2",
            "current": "not_applicable",
        },
    ]


def test_aspice_tailoring_changes_capture_override_target_change() -> None:
    previous = normalize_assurance_configuration(
        {
            "asil_level": "ASIL_C",
            "aspice_default_capability_level": 2,
            "aspice_scoped_processes": ["SWE.1"],
        }
    )
    updated = normalize_assurance_configuration(
        {
            "asil_level": "ASIL_C",
            "aspice_default_capability_level": 2,
            "aspice_scoped_processes": ["SWE.1"],
            "aspice_process_overrides": {"SWE.1": 3},
        }
    )

    assert aspice_tailoring_changes(previous, updated) == [
        {
            "target_kind": "aspice_process_capability",
            "target_id": "SWE.1",
            "previous": "CL2",
            "current": "CL3",
        }
    ]
