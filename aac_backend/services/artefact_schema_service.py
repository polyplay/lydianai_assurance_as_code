from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aac_backend.models.projects import ProjectConfiguration


READONLY_FIELDS = ("current_revision_id", "created_at", "updated_at")
BASE_MANDATORY_FIELDS = ("artefact_type", "title", "source.source_object_id")
FIELD_ENUMS: dict[str, tuple[str, ...]] = {
    "asil_level": ("QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"),
    "classification": ("QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"),
    "compliance_status": ("compliant", "partially_compliant", "non_compliant"),
    "approval_status": ("draft", "under_review", "approved", "rejected"),
    "release_status": ("draft", "approved", "released", "obsolete"),
    "status": ("draft", "active", "under_review", "approved", "released", "obsolete"),
    "verdict": ("pass", "fail", "blocked", "not_run"),
    "result": ("pass", "fail", "inconclusive"),
}
BOOLEAN_FIELDS = {
    "has_mixed_criticality_interaction",
    "qualification_required",
    "r155_applicable",
    "r156_applicable",
    "safety_relevant",
    "security_relevant",
    "software_update_relevant",
    "strict_unknown_fields",
}
NUMBER_FIELDS = {
    "achieved",
    "coverage_percentage",
    "coverage_target",
    "limit",
    "propagation_depth",
}
LONG_TEXT_TERMS = {
    "argument",
    "description",
    "handling",
    "justification",
    "limitations",
    "message",
    "notes",
    "rationale",
    "reason",
    "scope",
    "statement",
    "strategy",
    "summary",
}
ARRAY_SUFFIXES = (
    "_refs",
    "_ids",
    "_items",
    "_requirements",
    "_components",
    "_interfaces",
    "_mechanisms",
    "_methods",
    "_results",
    "_rules",
    "_tests",
)

_SCHEMA_FIELD_ROWS = """
Project:project_key,name,description,active_profile_id,lifecycle_phase,regulatory_scope
ProjectConfiguration:version_update_mode,sphinx_source_root,strict_unknown_fields,enabled_artefact_fields,baseline_policy,validation_policy,reporting_policy
AssuranceProfile:profile_id,classification,inherits_from_profile_id,standards_traceability_matrix_ref,artefact_classes,relationship_types,rules,reports
ProjectScope:scope_statement,included_systems,excluded_systems,included_aspice_processes,excluded_aspice_processes,scope_boundaries,justification_refs,evidence_refs
ASPICEScopeDecision:process_id,process_name,scope_status,rationale,affected_work_products,evidence_refs,approved_by,approved_at
TailoringDecision:scope_type,scope_id,target_kind,target_id,previous_applicability,tailored_applicability,rationale,evidence_refs,requested_by,approved_by,approved_at,decision_basis
SafetyPlan:scope,safety_lifecycle,roles_and_responsibilities,planned_work_products,confirmation_measures,verification_strategy,configuration_management_strategy,change_management_strategy,evidence_refs
SoftwareSafetyPlan:software_scope,software_lifecycle,software_work_products,software_verification_activities,software_integration_strategy,tools_and_environments,confirmation_measures,evidence_refs
SafetyCase:claim,argument_structure,supported_artefact_refs,open_assumptions,open_issues,confidence_argument,evidence_refs
SystemSafetyConcept:concept_scope,system_safety_requirements,safety_mechanisms,external_interface_assumptions,software_allocation_refs,evidence_refs
DevelopmentEnvironmentRecord:environment_name,toolchain_refs,runtime_platform,configuration_refs,qualification_or_confidence_refs,known_limitations,evidence_refs
QualityAssuranceRecord:qa_activity,scope,planned_by,performed_by,independence_evidence,findings,closure_refs,evidence_refs
DevelopmentPlan:scope,milestones,deliverables,responsibilities,process_refs
VerificationPlan:scope,verification_levels,verification_methods,entry_criteria,exit_criteria,environments,evidence_expectations
ValidationPlan:scope,validation_objectives,validation_methods,acceptance_criteria,external_refs
ConfigurationManagementPlan:configuration_item_types,baseline_strategy,versioning_strategy,access_control_strategy,audit_strategy
ChangeManagementRecord:change_request_id,change_summary,reason,affected_artefacts,impact_analysis_refs,approval_status,verification_impact
ConfirmationMeasureRecord:measure_type,scope,performed_by,independence_level,performed_at,result,findings,evidence_refs
ItemDefinition:item_scope,item_boundaries,operational_context,dependencies,external_interfaces,external_refs
HazardAnalysisRiskAssessment:external_refs,hazard_ids,safety_goal_ids,asil_classifications
SafetyGoal:statement,asil_level,source_hazard_refs,safe_state,linked_requirements
FunctionalSafetyRequirement:statement,asil_level,source_safety_goal_refs,allocated_to,verification_intent
TechnicalSafetyRequirement:statement,asil_level,source_fsr_refs,allocated_to,linked_software_safety_requirements
SystemDesignElement:element_type,responsibilities,interfaces,allocated_requirements
HardwareSoftwareInterface:source_element,destination_element,data_items,timing_constraints,resource_constraints,error_handling,linked_requirements
SoftwareSafetyRequirement:statement,asil_level,safety_relevant,source_refs,rationale,acceptance_criteria,allocated_to_components,linked_interfaces,linked_safeguards,verification_intent
SoftwareRequirement:statement,requirement_type,asil_level,safety_relevant,source_refs,rationale,acceptance_criteria,allocated_to_components,verification_intent
DerivedSoftwareRequirement:statement,derived_from,derivation_rationale,allocated_to_components,verification_intent
Assumption:statement,category,made_by,applies_to_interface,linked_safeguards,linked_tests
RequirementReviewRecord:reviewed_artefacts,review_method,reviewers,independence_level,result,findings,evidence_refs
SoftwareComponent:classification,responsibilities,owned_interfaces,consumed_interfaces,depends_on_components,allocated_requirements,linked_safeguards,implementation_items,has_mixed_criticality_interaction
SoftwareArchitecture:architecture_scope,components,interfaces,safety_mechanisms,allocation_rationale,architecture_decisions,analysis_refs
InterfaceContract:source_component,destination_component,interaction_kind,direction,classification,payload_definition,timing,validity_semantics,error_handling,security_relevant,software_update_relevant
AssumptionGuaranteeContract:asil_component,interface_id,assumptions,guarantees
Safeguard:safeguard_type,allocated_component,linked_interface,protects_against,expected_response,linked_requirements,linked_implementation_items,linked_tests
SoftwarePartitioningElement:partition_name,partitioning_mechanism,allocated_components,isolation_claims,freedom_from_interference_refs
ResourceUsageConstraint:constraint_type,applies_to,limit,unit,verification_refs
ArchitectureReviewRecord:reviewed_artefacts,reviewers,independence_level,result,findings,evidence_refs
SoftwareUnit:parent_component,responsibilities,provided_interfaces,required_interfaces,allocated_requirements
SoftwareUnitDesign:software_unit,design_description,inputs,outputs,internal_states,algorithms,error_handling,linked_requirements
ImplementationItem:repository_connector_id,repo_url,repo_path,language,file_type,implements_components,implements_interfaces,implements_safeguards,satisfies_requirements,implementation_constraints,review_status,commit_ref,commit_sha,branch,source_references
SourceCodeReference:repository_connector_id,repo_url,repo_path,commit_ref,commit_sha,branch,line_ref,line_range,language,linked_implementation_items,mapping_source
BuildConfiguration:repository_connector_id,build_id,source_revision,commit_sha,branch,workflow,build_ref,compiler_toolchain,build_options,dependencies,artifact_refs
CompilerToolchainConfiguration:toolchain_name,toolchain_version,compiler,compiler_version,configuration_options,tool_confidence_refs
ImplementationReviewRecord:reviewed_items,reviewers,independence_level,result,findings,evidence_refs
StaticAnalysisResult:tool,tool_version,scope,ruleset,execution_time,summary,open_findings,evidence_refs
CodingGuidelineComplianceRecord:guideline,guideline_version,scope,compliance_status,deviations,evidence_refs
TestPlan:scope,objectives,strategy,resources,schedule,risks,entry_criteria,exit_criteria
TestSpecification:objective,test_basis,derived_from_requirements,derived_from_safeguards,linked_interfaces,linked_components,verification_method,test_level,fault_class,coverage_target,pass_criteria,expected_evidence
TestCase:test_specification,preconditions,inputs,expected_results,pass_fail_criteria,linked_requirements
TestProcedure:test_cases,execution_steps,setup,cleanup,test_environment
TestEnvironment:environment_name,hardware,software,tools,configuration_refs,limitations
TestResult:test_case,test_procedure,test_environment,build_ref,baseline_ref,execution_time,verdict,actual_results,evidence_refs,defect_refs,waiver_ref,notes
CoverageResult:coverage_type,scope,target,achieved,gaps,evidence_refs
RequirementsCoverageRecord:requirements,covered_requirements,uncovered_requirements,coverage_percentage,evidence_refs
TestCompletionReport:test_scope,summary,executed_tests,open_defects,coverage_summary,recommendation
SafetyAnalysis:analysis_type,scope,method,findings,mitigations,linked_requirements,linked_safeguards,evidence_refs
InterfaceRiskAnalysis:interface_id,risk_scenarios,fault_classes,assumptions,safeguards,residual_risk,evidence_refs
FreedomFromInterferenceArgument:scope,interference_channels,prevention_mechanisms,verification_refs,argument_summary
ASILDecompositionArgument:decomposed_requirement,decomposition_rationale,independence_argument,allocated_elements,verification_refs
AssuranceArgument:claim,argument,evidence_refs,assumptions,open_issues
ThreatAnalysisRiskAssessment:scope,assets,threat_scenarios,risk_ratings,treatment_decisions,cybersecurity_goals,evidence_refs
CybersecurityRequirement:statement,source_tara_refs,security_relevant,allocated_to,verification_intent,acceptance_criteria
CybersecurityManagementEvidence:csms_scope,process_refs,risk_treatment_refs,verification_refs,monitoring_refs,incident_response_refs,evidence_refs
CybersecurityInterfaceEvidence:interface_id,threat_refs,risk_rating,mitigations,verification_refs,residual_risk,evidence_refs
SoftwareUpdateManagementEvidence:sums_scope,process_refs,update_package_refs,approval_refs,integrity_refs,version_refs,evidence_refs
SoftwareVersionRecord:software_item,version_identifier,baseline_ref,build_configuration_ref,compatible_vehicle_refs,release_status,evidence_refs
UpdateCampaign:campaign_id,scope,software_versions,delivery_method,authorization_refs,rollback_plan,monitoring_plan,evidence_refs
UpdateIntegrityEvidence:update_package_ref,signature_ref,hashes,verification_method,verification_result,evidence_refs
SoftwareBillOfMaterials:software_item,version_ref,components,suppliers,licenses,vulnerability_refs,evidence_refs
TestRiskAssessment:scope,product_risks,test_risk_level,mitigations,linked_test_plan,evidence_refs
ToolInventoryItem:tool_name,tool_version,tool_purpose,used_for,supplier,configuration
ToolConfidenceAssessment:tool_id,use_case,potential_errors,error_detection_measures,confidence_rationale,qualification_required
ToolQualificationEvidence:tool_id,qualification_strategy,qualification_evidence_refs,result
ProcessComplianceRecord:process_ref,scope,compliance_status,deviations,evidence_refs
ValidationIssue:rule_id,severity,message,affected_artefacts,affected_relationships,status,remediation_hint
DefectRecord:defect_id,summary,description,severity,status,affected_artefacts,detected_by,resolution,verification_refs
ChangeRequest:change_id,summary,reason,status,affected_artefacts,impact_analysis_refs,approval_refs
ChangeSet:change_request,changed_artefacts,changed_relationships,created_revisions,summary
SuspectState:artefact_id,trigger_event_id,reason,status,clearance_reason,cleared_by,cleared_at
ImpactAnalysisResult:trigger,impacted_artefacts,impacted_relationships,impact_paths,suspect_recommendations,retest_recommendations
EvidenceReference:evidence_type,uri,checksum,description,created_by,created_at
EvidenceBundle:baseline_id,included_evidence_refs,generated_reports,validation_summary,coverage_summary
GeneratedReport:report_type,format,scope,uri,generated_at
TraceabilityMatrix:scope,rows,generated_from_revision_set,gaps
InterfaceAssuranceReport:interfaces,assumptions,safeguards,tests,evidence_status,gaps
AuditEvent:event_type,actor_type,actor_id,correlation_id,causation_id,affected_artefacts,affected_relationships,event_payload
ImportRun:source_tool,source_root,state,version_update_mode,summary,diagnostics
ArtefactRevision:artefact_id,revision_number,payload_snapshot,change_reason,changed_by,changed_at,import_run_id
RelationshipRevision:relationship_id,revision_number,payload_snapshot,changed_by,changed_at,import_run_id
Baseline:baseline_id,project_id,state,profile_id,included_artefact_revisions,included_relationship_revisions,validation_summary,coverage_summary,suspect_summary,release_gate_result
ReleaseGateResult:baseline_id,status,result,blocking_issues,warning_issues,evaluated_rules,evaluated_at,evaluated_by
""".strip()

CANONICAL_ARTEFACT_PAYLOAD_FIELDS = {
    row.split(":", 1)[0]: tuple(row.split(":", 1)[1].split(","))
    for row in _SCHEMA_FIELD_ROWS.splitlines()
}

DEFAULT_REQUIRED_FIELDS: dict[str, tuple[str, ...]] = {
    artefact_type: (fields[0],) for artefact_type, fields in CANONICAL_ARTEFACT_PAYLOAD_FIELDS.items() if fields
}
DEFAULT_REQUIRED_FIELDS.update(
    {
        "SafetyGoal": ("statement", "asil_level"),
        "FunctionalSafetyRequirement": ("statement", "asil_level"),
        "TechnicalSafetyRequirement": ("statement", "asil_level"),
        "SoftwareSafetyRequirement": ("statement", "asil_level", "verification_intent"),
        "SoftwareRequirement": ("statement", "verification_intent"),
        "DerivedSoftwareRequirement": ("statement", "derived_from", "verification_intent"),
        "SoftwareComponent": ("classification", "responsibilities"),
        "SoftwareArchitecture": ("architecture_scope", "components"),
        "InterfaceContract": ("source_component", "destination_component", "interaction_kind", "payload_definition"),
        "AssumptionGuaranteeContract": ("assumptions", "guarantees"),
        "Safeguard": ("safeguard_type", "allocated_component"),
        "SoftwareUnit": ("parent_component", "responsibilities"),
        "SoftwareUnitDesign": ("software_unit", "design_description"),
        "ImplementationItem": ("repo_path", "language"),
        "SourceCodeReference": ("repo_url", "repo_path", "commit_ref"),
        "BuildConfiguration": ("build_id", "compiler_toolchain"),
        "StaticAnalysisResult": ("tool", "summary"),
        "CodingGuidelineComplianceRecord": ("guideline", "compliance_status"),
        "TestSpecification": ("objective", "test_basis", "verification_method"),
        "TestCase": ("test_specification", "expected_results", "pass_fail_criteria"),
        "TestProcedure": ("test_cases", "test_environment"),
        "TestEnvironment": ("environment_name",),
        "TestResult": ("test_case", "test_environment", "verdict"),
        "RequirementsCoverageRecord": ("requirements", "coverage_percentage"),
        "ThreatAnalysisRiskAssessment": ("scope", "threat_scenarios", "risk_ratings"),
        "CybersecurityRequirement": ("statement", "source_tara_refs", "verification_intent"),
        "CybersecurityManagementEvidence": ("csms_scope", "process_refs", "evidence_refs"),
        "CybersecurityInterfaceEvidence": ("interface_id", "threat_refs", "mitigations"),
        "SoftwareUpdateManagementEvidence": ("sums_scope", "process_refs", "integrity_refs"),
        "SoftwareVersionRecord": ("software_item", "version_identifier", "baseline_ref"),
        "UpdateCampaign": ("campaign_id", "scope", "software_versions"),
        "UpdateIntegrityEvidence": ("update_package_ref", "verification_result"),
        "SoftwareBillOfMaterials": ("software_item", "version_ref", "components"),
        "TestRiskAssessment": ("scope", "product_risks", "test_risk_level"),
        "DefectRecord": ("defect_id", "summary", "status"),
        "ChangeRequest": ("change_id", "summary", "status"),
        "ChangeSet": ("change_request", "changed_artefacts"),
    }
)


@dataclass(frozen=True)
class ArtefactSchema:
    artefact_type: str
    schema_version: str
    enabled_fields: tuple[str, ...]
    disabled_fields: tuple[str, ...]
    mandatory_fields: tuple[str, ...]
    readonly_fields: tuple[str, ...] = READONLY_FIELDS

    def as_dict(self) -> dict[str, Any]:
        return {
            "artefact_type": self.artefact_type,
            "schema_version": self.schema_version,
            "enabled_fields": list(self.enabled_fields),
            "disabled_fields": list(self.disabled_fields),
            "mandatory_fields": list(self.mandatory_fields),
            "readonly_fields": list(self.readonly_fields),
            "fields": [
                _field_metadata(
                    field,
                    required=field in self.mandatory_fields,
                    readonly=field in self.readonly_fields,
                )
                for field in self.enabled_fields
            ],
        }


def all_schema_summaries(config: ProjectConfiguration | None = None) -> list[dict[str, Any]]:
    return [
        schema_for_artefact_type(artefact_type, config).as_dict()
        for artefact_type in sorted(CANONICAL_ARTEFACT_PAYLOAD_FIELDS)
    ]


def schema_for_artefact_type(
    artefact_type: str,
    config: ProjectConfiguration | None = None,
) -> ArtefactSchema:
    fields = CANONICAL_ARTEFACT_PAYLOAD_FIELDS.get(artefact_type)
    if fields is None:
        raise ValueError(f"Unknown artefact type: {artefact_type}")
    override = _schema_overrides(config).get(artefact_type, {})
    disabled = set(override.get("disabled_fields", []))
    enabled = tuple(field for field in override.get("enabled_fields", fields) if field not in disabled)
    mandatory = tuple(override.get("mandatory_fields", DEFAULT_REQUIRED_FIELDS.get(artefact_type, ())))
    invalid_disabled = set(mandatory).intersection(disabled)
    if invalid_disabled:
        raise ValueError(f"Mandatory fields cannot be disabled: {', '.join(sorted(invalid_disabled))}")
    return ArtefactSchema(
        artefact_type=artefact_type,
        schema_version=str(override.get("schema_version", "1.0")),
        enabled_fields=enabled,
        disabled_fields=tuple(sorted(disabled)),
        mandatory_fields=mandatory,
    )


def apply_schema_override(
    config: ProjectConfiguration,
    artefact_type: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    schema_for_artefact_type(artefact_type, config)
    policy = dict(config.validation_policy_json or {})
    overrides = dict(policy.get("artefact_schemas") or {})
    current = dict(overrides.get(artefact_type) or {})
    for key in ("schema_version", "enabled_fields", "disabled_fields", "mandatory_fields"):
        if key in payload:
            current[key] = payload[key]
    overrides[artefact_type] = current
    policy["artefact_schemas"] = overrides
    candidate_config = ProjectConfiguration(
        project_id=config.project_id,
        validation_policy_json=policy,
    )
    schema = schema_for_artefact_type(artefact_type, candidate_config).as_dict()
    config.validation_policy_json = policy
    return schema


def validate_artefact_payload(
    artefact_type: str,
    payload: dict[str, Any],
    config: ProjectConfiguration | None = None,
) -> None:
    schema = schema_for_artefact_type(artefact_type, config)
    missing = [field for field in schema.mandatory_fields if not _has_value(payload, field)]
    if missing:
        raise ValueError(f"{artefact_type} payload missing mandatory fields: {', '.join(missing)}")
    disabled_present = [field for field in schema.disabled_fields if _has_value(payload, field)]
    if disabled_present:
        raise ValueError(f"{artefact_type} payload contains disabled fields: {', '.join(disabled_present)}")
    if _strict_unknown_fields(config):
        unknown = sorted(set(payload) - set(CANONICAL_ARTEFACT_PAYLOAD_FIELDS[artefact_type]))
        if unknown:
            raise ValueError(f"{artefact_type} payload contains unknown fields: {', '.join(unknown)}")


def required_fields_for_artefact_type(artefact_type: str) -> tuple[str, ...]:
    return DEFAULT_REQUIRED_FIELDS.get(artefact_type, ())


def _field_metadata(field: str, *, required: bool, readonly: bool) -> dict[str, Any]:
    allowed_values = FIELD_ENUMS.get(field, ())
    if allowed_values:
        data_type = "string"
        widget = "select"
    elif field in BOOLEAN_FIELDS or field.startswith(("has_", "is_")):
        data_type = "boolean"
        widget = "checkbox"
    elif field in NUMBER_FIELDS or field.endswith(("_count", "_percentage")):
        data_type = "number"
        widget = "number"
    elif _looks_like_array(field):
        data_type = "array"
        widget = "tag_list"
    elif any(term in field for term in LONG_TEXT_TERMS):
        data_type = "string"
        widget = "textarea"
    else:
        data_type = "string"
        widget = "text"
    return {
        "name": field,
        "label": field.replace("_", " ").replace(".", " ").title(),
        "data_type": data_type,
        "widget": widget,
        "required": required,
        "readonly": readonly,
        "allowed_values": list(allowed_values),
        "item_type": "string" if data_type == "array" else None,
        "help": _field_help(field, data_type),
    }


def _looks_like_array(field: str) -> bool:
    return (
        field.endswith(ARRAY_SUFFIXES)
        or field
        in {
            "algorithms",
            "assumptions",
            "components",
            "dependencies",
            "exclusions",
            "findings",
            "guarantees",
            "hashes",
            "inputs",
            "interfaces",
            "mitigations",
            "outputs",
            "preconditions",
            "responsibilities",
            "risks",
            "rows",
            "safeguards",
            "threat_scenarios",
        }
    )


def _field_help(field: str, data_type: str) -> str:
    if data_type == "array":
        return "Enter one value per line."
    if field.endswith("_refs") or field.endswith("_id"):
        return "Use a stable canonical identifier."
    if field == "asil_level":
        return "Select the applicable automotive safety integrity level."
    return f"Enter {field.replace('_', ' ')}."


def _schema_overrides(config: ProjectConfiguration | None) -> dict[str, Any]:
    return ((config.validation_policy_json if config else {}) or {}).get("artefact_schemas") or {}


def _strict_unknown_fields(config: ProjectConfiguration | None) -> bool:
    policy = (config.validation_policy_json if config else {}) or {}
    return bool(policy.get("strict_unknown_fields"))


def _has_value(payload: dict[str, Any], field: str) -> bool:
    value: Any = payload
    for part in field.split("."):
        if not isinstance(value, dict) or part not in value:
            return False
        value = value[part]
    return value not in (None, "", [], {})
