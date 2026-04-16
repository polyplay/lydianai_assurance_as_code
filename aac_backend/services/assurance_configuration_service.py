from __future__ import annotations

from copy import deepcopy
from typing import Any

from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.services.artefact_schema_service import CANONICAL_ARTEFACT_PAYLOAD_FIELDS


ASIL_LEVELS = ("QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D")
ASPICE_MODEL = "ASPICE_PAM_4_0"
VISIBILITY_POLICIES = ("relevant_first", "strict_hide", "show_all_tagged")
DEFAULT_ASPICE_CAPABILITY_BY_ASIL = {
    "QM": 1,
    "ASIL_A": 1,
    "ASIL_B": 2,
    "ASIL_C": 3,
    "ASIL_D": 3,
}

DEFAULT_ASPICE_SCOPED_PROCESSES = (
    "MAN.3",
    "SWE.1",
    "SWE.2",
    "SWE.3",
    "SWE.4",
    "SWE.5",
    "SWE.6",
    "SUP.1",
    "SUP.8",
    "SUP.9",
    "SUP.10",
    "VAL.1",
)

RELATIONSHIP_TYPES = {
    "allocates_to",
    "assumes",
    "constrains",
    "depends_on",
    "derives_from",
    "guarantees",
    "implements",
    "interacts_via",
    "mitigates",
    "produces_result_for",
    "protects",
    "references",
    "satisfies",
    "traces_to",
    "verifies",
}

ASIL_D_MANDATORY_ARTEFACT_TYPES = {
    "ProjectScope",
    "SafetyPlan",
    "SoftwareSafetyPlan",
    "SafetyCase",
    "HazardAnalysisRiskAssessment",
    "SafetyGoal",
    "FunctionalSafetyRequirement",
    "TechnicalSafetyRequirement",
    "SoftwareSafetyRequirement",
    "SoftwareRequirement",
    "SoftwareArchitecture",
    "SoftwareComponent",
    "InterfaceContract",
    "AssumptionGuaranteeContract",
    "Safeguard",
    "SoftwareUnitDesign",
    "SoftwareUnit",
    "ImplementationItem",
    "SourceCodeReference",
    "BuildConfiguration",
    "ToolInventoryItem",
    "ToolConfidenceAssessment",
    "TestPlan",
    "TestSpecification",
    "TestCase",
    "TestProcedure",
    "TestEnvironment",
    "TestResult",
    "CoverageResult",
    "RequirementsCoverageRecord",
    "RequirementReviewRecord",
    "ArchitectureReviewRecord",
    "ImplementationReviewRecord",
    "QualityAssuranceRecord",
    "ChangeRequest",
    "ChangeSet",
    "DefectRecord",
    "ConfirmationMeasureRecord",
}

MANDATORY_ARTEFACTS_BY_ASIL: dict[str, set[str]] = {
    "QM": {
        "ProjectScope",
        "SoftwareRequirement",
        "SoftwareArchitecture",
        "SoftwareComponent",
        "ImplementationItem",
        "BuildConfiguration",
        "TestSpecification",
        "TestCase",
        "TestResult",
        "DefectRecord",
        "ChangeRequest",
    },
    "ASIL_A": {
        "ProjectScope",
        "SafetyPlan",
        "SoftwareRequirement",
        "SoftwareSafetyRequirement",
        "SoftwareArchitecture",
        "SoftwareComponent",
        "InterfaceContract",
        "ImplementationItem",
        "BuildConfiguration",
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "RequirementsCoverageRecord",
        "ChangeRequest",
        "DefectRecord",
    },
    "ASIL_B": {
        "ProjectScope",
        "SafetyPlan",
        "SoftwareSafetyPlan",
        "SafetyGoal",
        "FunctionalSafetyRequirement",
        "TechnicalSafetyRequirement",
        "SoftwareSafetyRequirement",
        "SoftwareRequirement",
        "SoftwareArchitecture",
        "SoftwareComponent",
        "InterfaceContract",
        "Safeguard",
        "SoftwareUnitDesign",
        "SoftwareUnit",
        "ImplementationItem",
        "SourceCodeReference",
        "BuildConfiguration",
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "CoverageResult",
        "RequirementsCoverageRecord",
        "ChangeRequest",
        "ChangeSet",
        "DefectRecord",
    },
    "ASIL_C": ASIL_D_MANDATORY_ARTEFACT_TYPES
    - {"ConfirmationMeasureRecord", "QualityAssuranceRecord"},
    "ASIL_D": ASIL_D_MANDATORY_ARTEFACT_TYPES,
}

CONDITIONAL_ARTEFACTS_BY_ASIL: dict[str, set[str]] = {
    "QM": {"ToolInventoryItem", "ToolConfidenceAssessment"},
    "ASIL_A": {"ToolInventoryItem", "ToolConfidenceAssessment"},
    "ASIL_B": {
        "AssumptionGuaranteeContract",
        "FreedomFromInterferenceArgument",
        "ASILDecompositionArgument",
        "ToolConfidenceAssessment",
        "ToolQualificationEvidence",
    },
    "ASIL_C": {
        "FreedomFromInterferenceArgument",
        "ASILDecompositionArgument",
        "ToolQualificationEvidence",
        "SafetyAnalysis",
        "InterfaceRiskAnalysis",
        "ConfirmationMeasureRecord",
    },
    "ASIL_D": {
        "FreedomFromInterferenceArgument",
        "ASILDecompositionArgument",
        "ToolQualificationEvidence",
        "SafetyAnalysis",
        "InterfaceRiskAnalysis",
    },
}

ASPICE_ARTEFACTS_BY_PROCESS: dict[str, set[str]] = {
    "MAN.3": {"ProjectScope", "DevelopmentPlan"},
    "SPL.2": {"GeneratedReport", "EvidenceBundle"},
    "SYS.1": {"ProjectScope", "EvidenceReference"},
    "SYS.2": {"SoftwareRequirement", "RequirementsCoverageRecord"},
    "SYS.3": {"SystemDesignElement", "HardwareSoftwareInterface"},
    "SWE.1": {"SoftwareRequirement", "RequirementsCoverageRecord", "RequirementReviewRecord"},
    "SWE.2": {
        "SoftwareArchitecture",
        "SoftwareComponent",
        "InterfaceContract",
        "ArchitectureReviewRecord",
    },
    "SWE.3": {
        "SoftwareUnitDesign",
        "SoftwareUnit",
        "ImplementationItem",
        "SourceCodeReference",
        "ImplementationReviewRecord",
    },
    "SWE.4": {
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "CoverageResult",
    },
    "SWE.5": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "CoverageResult",
    },
    "SWE.6": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestResult",
        "RequirementsCoverageRecord",
        "TestCompletionReport",
    },
    "SUP.1": {"QualityAssuranceRecord"},
    "SUP.8": {"ConfigurationManagementPlan", "BuildConfiguration"},
    "SUP.9": {"DefectRecord"},
    "SUP.10": {"ChangeRequest", "ChangeSet", "ImpactAnalysisResult"},
    "VAL.1": {"ValidationPlan", "TestCompletionReport"},
}

ASPICE_CL2_CONTROL_ARTEFACTS = {
    "ProjectScope",
    "DevelopmentPlan",
    "ConfigurationManagementPlan",
    "ChangeManagementRecord",
    "QualityAssuranceRecord",
}

ASPICE_CL3_PROCESS_ARTEFACTS = {
    "ASPICEScopeDecision",
    "ProcessComplianceRecord",
}

TEST_ARTEFACTS_BY_SCOPE: dict[str, set[str]] = {
    "unit": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "CoverageResult",
    },
    "integration": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "CoverageResult",
    },
    "software_qualification": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "RequirementsCoverageRecord",
        "TestCompletionReport",
    },
    "system": {
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestProcedure",
        "TestEnvironment",
        "TestResult",
        "TestCompletionReport",
    },
    "acceptance": {
        "ValidationPlan",
        "TestPlan",
        "TestSpecification",
        "TestCase",
        "TestResult",
        "TestCompletionReport",
    },
}

R155_MANDATORY_ARTEFACTS = {
    "ThreatAnalysisRiskAssessment",
    "CybersecurityRequirement",
    "CybersecurityManagementEvidence",
}
R155_CONDITIONAL_ARTEFACTS = {"CybersecurityInterfaceEvidence", "InterfaceRiskAnalysis"}

R156_MANDATORY_ARTEFACTS = {
    "SoftwareUpdateManagementEvidence",
    "SoftwareVersionRecord",
    "UpdateCampaign",
    "UpdateIntegrityEvidence",
    "SoftwareBillOfMaterials",
}

CORE_RULES = {
    "AAC-RULE-RULE-001",
    "AAC-RULE-RULE-002",
    "AAC-RULE-RULE-003",
    "AAC-RULE-RULE-004",
    "AAC-RULE-RULE-005",
    "AAC-RULE-RULE-006",
    "AAC-RULE-RULE-080",
    "AAC-RULE-RULE-081",
    "AAC-RULE-RULE-090",
    "AAC-RULE-RULE-091",
}

SAFETY_RULES = {
    "AAC-RULE-RULE-010",
    "AAC-RULE-RULE-011",
    "AAC-RULE-RULE-012",
    "AAC-RULE-RULE-013",
    "AAC-RULE-RULE-014",
    "AAC-RULE-RULE-025",
    "AAC-RULE-RULE-026",
    "AAC-RULE-RULE-027",
    "AAC-RULE-RULE-030",
    "AAC-RULE-RULE-031",
    "AAC-RULE-RULE-032",
    "AAC-RULE-RULE-033",
    "AAC-RULE-RULE-034",
    "AAC-RULE-RULE-043",
    "AAC-RULE-RULE-044",
}

ASIL_CD_ONLY_RULES = {"AAC-RULE-RULE-063"}

ASPICE_RULES_BY_PROCESS: dict[str, set[str]] = {
    "SWE.1": {
        "AAC-RULE-RULE-011",
        "AAC-RULE-RULE-012",
        "AAC-RULE-RULE-013",
    },
    "SWE.2": {
        "AAC-RULE-RULE-020",
        "AAC-RULE-RULE-021",
        "AAC-RULE-RULE-022",
        "AAC-RULE-RULE-023",
        "AAC-RULE-RULE-024",
    },
    "SWE.3": {
        "AAC-RULE-RULE-040",
        "AAC-RULE-RULE-041",
        "AAC-RULE-RULE-042",
    },
    "SWE.4": {
        "AAC-RULE-RULE-050",
        "AAC-RULE-RULE-051",
        "AAC-RULE-RULE-052",
        "AAC-RULE-RULE-053",
    },
    "SWE.5": {
        "AAC-RULE-RULE-050",
        "AAC-RULE-RULE-051",
        "AAC-RULE-RULE-052",
        "AAC-RULE-RULE-053",
    },
    "SWE.6": {"AAC-RULE-RULE-054", "AAC-RULE-RULE-055"},
    "SUP.8": {"AAC-RULE-RULE-062"},
    "SUP.9": {"AAC-RULE-RULE-061"},
    "SUP.10": {"AAC-RULE-RULE-060"},
}


def normalize_assurance_configuration(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    source = dict(raw or {})
    asil_level = _normalize_asil(source.get("asil_level") or source.get("project_classification") or "ASIL_D")
    default_capability = _normalize_capability(
        source.get("aspice_default_capability_level", source.get("aspice_capability_level", 3))
    )
    scoped_processes = source.get("aspice_scoped_processes") or DEFAULT_ASPICE_SCOPED_PROCESSES
    scoped_processes = sorted({str(process).upper() for process in scoped_processes if process})
    overrides = {
        str(process).upper(): _normalize_capability(level)
        for process, level in dict(source.get("aspice_process_overrides") or {}).items()
    }
    process_targets = {
        process: overrides.get(process, default_capability)
        for process in scoped_processes
    }
    visibility_policy = source.get("visibility_policy") or "relevant_first"
    if visibility_policy not in VISIBILITY_POLICIES:
        visibility_policy = "relevant_first"
    test_scope = source.get("test_scope")
    if not test_scope:
        test_scope = ["unit", "integration", "software_qualification"]
    test_scope = sorted({str(scope) for scope in test_scope if scope})
    r155_applicable = bool(source.get("r155_applicable", source.get("has_cybersecurity_relevance", False)))
    r156_applicable = bool(source.get("r156_applicable", source.get("has_software_update_relevance", False)))
    return {
        "project_type": source.get("project_type", "software_system"),
        "asil_level": asil_level,
        "aspice_model": ASPICE_MODEL,
        "aspice_default_capability_level": default_capability,
        "aspice_scoped_processes": scoped_processes,
        "aspice_process_overrides": overrides,
        "aspice_process_capability_targets": process_targets,
        "r155_applicable": r155_applicable,
        "r156_applicable": r156_applicable,
        "has_cybersecurity_relevance": bool(
            source.get("has_cybersecurity_relevance", r155_applicable)
        ),
        "has_software_update_relevance": bool(
            source.get("has_software_update_relevance", r156_applicable)
        ),
        "test_scope": test_scope,
        "visibility_policy": visibility_policy,
    }


def assurance_configuration_from_profile_id(profile_id: str | None) -> dict[str, Any]:
    classification = "ASIL_D"
    if profile_id:
        for level in ASIL_LEVELS:
            if profile_id.startswith(level):
                classification = level
                break
    return default_assurance_configuration_for_asil(classification)


def default_assurance_configuration_for_asil(asil_level: str) -> dict[str, Any]:
    classification = _normalize_asil(asil_level)
    return normalize_assurance_configuration(
        {
            "asil_level": classification,
            "aspice_default_capability_level": DEFAULT_ASPICE_CAPABILITY_BY_ASIL[classification],
        }
    )


def derive_profile_payload(raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = normalize_assurance_configuration(raw_config)
    artefact_model = derive_artefact_applicability(config)
    rules = derive_rule_policy(config)
    return {
        "project_assurance_configuration": config,
        "project_classification": config["asil_level"],
        "aspice": {
            "model": config["aspice_model"],
            "default_capability_level": config["aspice_default_capability_level"],
            "process_capability_targets": config["aspice_process_capability_targets"],
            "max_supported_capability_level": 3,
        },
        "artefact_classes": artefact_model["artefact_classes"],
        "relationship_types": {
            relationship_type: {
                "applicability": "optional",
                "source_types": [],
                "target_types": [],
                "min_count": None,
            }
            for relationship_type in sorted(RELATIONSHIP_TYPES)
        },
        "rules": rules,
        "reports": {
            "traceability_matrix": {"applicability": "mandatory"},
            "validation_summary": {"applicability": "mandatory"},
            "baseline_comparison": {"applicability": "mandatory"},
        },
        "derived_applicability": {
            key: sorted(value)
            for key, value in artefact_model.items()
            if key != "artefact_classes"
        },
    }


def derive_validation_policy(
    raw_config: dict[str, Any] | None = None,
    existing_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = normalize_assurance_configuration(raw_config)
    policy = deepcopy(existing_policy or {})
    policy["project_assurance_configuration"] = config
    policy["rules"] = derive_rule_policy(config)
    policy["has_cybersecurity_relevance"] = config["has_cybersecurity_relevance"]
    policy["has_software_update_relevance"] = config["has_software_update_relevance"]
    policy["requirements_coverage_minimum"] = _coverage_minimum_for(config["asil_level"])
    return policy


def derive_artefact_applicability(raw_config: dict[str, Any] | None = None) -> dict[str, Any]:
    config = normalize_assurance_configuration(raw_config)
    mandatory: set[str] = set(MANDATORY_ARTEFACTS_BY_ASIL[config["asil_level"]])
    conditional: set[str] = set(CONDITIONAL_ARTEFACTS_BY_ASIL[config["asil_level"]])

    for process, capability_level in config["aspice_process_capability_targets"].items():
        if capability_level < 1:
            continue
        mandatory.update(ASPICE_ARTEFACTS_BY_PROCESS.get(process, set()))
        if capability_level >= 2:
            mandatory.update(ASPICE_CL2_CONTROL_ARTEFACTS)
        if capability_level >= 3:
            mandatory.update(ASPICE_CL3_PROCESS_ARTEFACTS)

    for scope in config["test_scope"]:
        mandatory.update(TEST_ARTEFACTS_BY_SCOPE.get(scope, set()))
    if config["test_scope"]:
        conditional.add("TestRiskAssessment")

    if config["r155_applicable"]:
        mandatory.update(R155_MANDATORY_ARTEFACTS)
        conditional.update(R155_CONDITIONAL_ARTEFACTS)
    if config["r156_applicable"]:
        mandatory.update(R156_MANDATORY_ARTEFACTS)

    known_types = set(CANONICAL_ARTEFACT_PAYLOAD_FIELDS)
    mandatory &= known_types
    conditional = (conditional & known_types) - mandatory
    regulatory_types = R155_MANDATORY_ARTEFACTS | R155_CONDITIONAL_ARTEFACTS | R156_MANDATORY_ARTEFACTS
    not_applicable = {
        artefact_type
        for artefact_type in regulatory_types & known_types
        if (
            artefact_type in R155_MANDATORY_ARTEFACTS | R155_CONDITIONAL_ARTEFACTS
            and not config["r155_applicable"]
        )
        or (artefact_type in R156_MANDATORY_ARTEFACTS and not config["r156_applicable"])
    }
    optional = known_types - mandatory - conditional - not_applicable
    visible = _visible_artefacts(
        mandatory=mandatory,
        conditional=conditional,
        optional=optional,
        not_applicable=not_applicable,
        visibility_policy=config["visibility_policy"],
    )
    artefact_classes = {}
    for artefact_type in sorted(known_types):
        applicability = "optional"
        if artefact_type in mandatory:
            applicability = "mandatory"
        elif artefact_type in conditional:
            applicability = "conditional"
        elif artefact_type in not_applicable:
            applicability = "not_applicable"
        artefact_classes[artefact_type] = {
            "applicability": applicability,
            "visible": artefact_type in visible,
            "required_status_for_baseline": ["approved", "released"],
            "required_status_for_release": ["released"],
            "evidence_required": applicability in {"mandatory", "conditional"},
            "tailoring_allowed": applicability in {"mandatory", "conditional", "optional"},
            "tailoring_approval_role": "project_lead",
            "source_dimensions": _source_dimensions_for(artefact_type, config),
        }
    return {
        "mandatory_artefact_types": mandatory,
        "conditional_artefact_types": conditional,
        "optional_artefact_types": optional,
        "not_applicable_artefact_types": not_applicable,
        "visible_artefact_types": visible,
        "artefact_classes": artefact_classes,
    }


def derive_rule_policy(raw_config: dict[str, Any] | None = None) -> dict[str, dict[str, Any]]:
    config = normalize_assurance_configuration(raw_config)
    enabled = set(CORE_RULES)
    if config["asil_level"] != "QM":
        enabled.update(SAFETY_RULES)
    if config["asil_level"] in {"ASIL_C", "ASIL_D"}:
        enabled.update(ASIL_CD_ONLY_RULES)
    for process, capability_level in config["aspice_process_capability_targets"].items():
        if capability_level >= 1:
            enabled.update(ASPICE_RULES_BY_PROCESS.get(process, set()))
    if config["test_scope"]:
        enabled.update(
            {
                "AAC-RULE-RULE-050",
                "AAC-RULE-RULE-051",
                "AAC-RULE-RULE-052",
                "AAC-RULE-RULE-053",
                "AAC-RULE-RULE-054",
                "AAC-RULE-RULE-055",
            }
        )
    if config["r155_applicable"]:
        enabled.add("AAC-RULE-RULE-070")
    if config["r156_applicable"]:
        enabled.add("AAC-RULE-RULE-071")

    policy = {}
    for rule_id, rule in RULE_CATALOG.items():
        is_enabled = rule_id in enabled
        severity = _severity_for(rule_id, rule.severity, config["asil_level"]) if is_enabled else "disabled"
        policy[rule_id] = {
            "enabled": is_enabled,
            "severity": severity,
            "execution_modes": list(rule.execution_modes),
            "blocking_contexts": list(rule.blocking_contexts) if is_enabled else [],
            "tailoring_allowed": severity != "critical",
            "source_dimensions": _rule_source_dimensions(rule_id, config),
        }
    return policy


def _normalize_asil(value: Any) -> str:
    normalized = str(value or "ASIL_D").upper().replace("-", "_")
    if normalized == "ASILD":
        normalized = "ASIL_D"
    if normalized == "ASILC":
        normalized = "ASIL_C"
    if normalized == "ASILB":
        normalized = "ASIL_B"
    if normalized == "ASILA":
        normalized = "ASIL_A"
    if normalized not in ASIL_LEVELS:
        return "ASIL_D"
    return normalized


def _normalize_capability(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 3
    return max(1, min(parsed, 3))


def _coverage_minimum_for(asil_level: str) -> int:
    return {
        "QM": 80,
        "ASIL_A": 90,
        "ASIL_B": 95,
        "ASIL_C": 100,
        "ASIL_D": 100,
    }[asil_level]


def _severity_for(rule_id: str, default: str, asil_level: str) -> str:
    if asil_level == "QM" and rule_id in SAFETY_RULES | ASIL_CD_ONLY_RULES:
        return "disabled"
    if asil_level == "ASIL_A" and default == "critical":
        return "major"
    if asil_level == "ASIL_B" and rule_id in {
        "AAC-RULE-RULE-043",
        "AAC-RULE-RULE-044",
        "AAC-RULE-RULE-063",
    }:
        return "major"
    return default


def _visible_artefacts(
    *,
    mandatory: set[str],
    conditional: set[str],
    optional: set[str],
    not_applicable: set[str],
    visibility_policy: str,
) -> set[str]:
    if visibility_policy == "strict_hide":
        return set(mandatory) | set(conditional)
    if visibility_policy == "show_all_tagged":
        return set(mandatory) | set(conditional) | set(optional) | set(not_applicable)
    return set(mandatory) | set(conditional)


def _source_dimensions_for(artefact_type: str, config: dict[str, Any]) -> list[str]:
    dimensions = []
    if artefact_type in MANDATORY_ARTEFACTS_BY_ASIL[config["asil_level"]] or artefact_type in CONDITIONAL_ARTEFACTS_BY_ASIL[config["asil_level"]]:
        dimensions.append(f"ISO26262:{config['asil_level']}")
    for process, artefacts in ASPICE_ARTEFACTS_BY_PROCESS.items():
        if artefact_type in artefacts and process in config["aspice_process_capability_targets"]:
            dimensions.append(f"ASPICE4.0:{process}:CL{config['aspice_process_capability_targets'][process]}")
    if artefact_type in ASPICE_CL3_PROCESS_ARTEFACTS and any(
        level >= 3 for level in config["aspice_process_capability_targets"].values()
    ):
        dimensions.append("ASPICE4.0:PA3.1/PA3.2")
    if artefact_type in R155_MANDATORY_ARTEFACTS | R155_CONDITIONAL_ARTEFACTS:
        dimensions.append("UNECE_R155")
    if artefact_type in R156_MANDATORY_ARTEFACTS:
        dimensions.append("UNECE_R156")
    for scope, artefacts in TEST_ARTEFACTS_BY_SCOPE.items():
        if artefact_type in artefacts and scope in config["test_scope"]:
            dimensions.append(f"ISO29119:{scope}")
    return sorted(set(dimensions))


def _rule_source_dimensions(rule_id: str, config: dict[str, Any]) -> list[str]:
    dimensions = []
    if rule_id in SAFETY_RULES | ASIL_CD_ONLY_RULES:
        dimensions.append(f"ISO26262:{config['asil_level']}")
    for process, rules in ASPICE_RULES_BY_PROCESS.items():
        if rule_id in rules and process in config["aspice_process_capability_targets"]:
            dimensions.append(f"ASPICE4.0:{process}:CL{config['aspice_process_capability_targets'][process]}")
    if rule_id in {"AAC-RULE-RULE-050", "AAC-RULE-RULE-051", "AAC-RULE-RULE-052", "AAC-RULE-RULE-053", "AAC-RULE-RULE-054", "AAC-RULE-RULE-055"}:
        dimensions.extend(f"ISO29119:{scope}" for scope in config["test_scope"])
    if rule_id == "AAC-RULE-RULE-070":
        dimensions.append("UNECE_R155")
    if rule_id == "AAC-RULE-RULE-071":
        dimensions.append("UNECE_R156")
    if rule_id in CORE_RULES:
        dimensions.append("TOOL")
    return sorted(set(dimensions))
