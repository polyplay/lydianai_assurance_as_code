# Artefact JSON Schemas

## 1. Purpose

This document defines the MVP field-level JSON schemas for canonical artefact payloads.

All API request and response bodies are JSON for MVP. The web app may render these fields visually, but the back-end contract remains JSON.

## 2. Schema Principles

AAC-SCHEMA-FR-001
Every artefact shall use the common base artefact fields.

AAC-SCHEMA-FR-002
Every artefact shall have a type-specific `payload`.

AAC-SCHEMA-FR-003
By default, all fields defined for an artefact type shall be enabled.

AAC-SCHEMA-FR-004
Project configuration may disable non-mandatory fields from authoring/API views.

AAC-SCHEMA-FR-005
Project configuration shall not disable fields required for identity, versioning, audit, validation, baseline integrity, source traceability, or standards traceability.

AAC-SCHEMA-FR-006
Unknown fields shall be rejected in strict mode and preserved as raw import metadata in non-strict mode.

## 3. Common Base Artefact Schema

```json
{
  "artefact_id": "string",
  "project_id": "string",
  "artefact_type": "string",
  "title": "string",
  "description": "string",
  "status": "draft|under_review|reviewed|approved|released|obsolete",
  "owner": "string",
  "current_revision_id": "string",
  "tags": ["string"],
  "source": {
    "source_kind": "sphinx|api|external|generated",
    "source_tool": "string",
    "source_object_id": "string",
    "source_document": "string",
    "external_uri": "string"
  },
  "standards": {
    "standards_refs": ["string"],
    "work_product_kind": "string",
    "review_expectation": "none|required|independent_required",
    "independence_expectation": "none|same_team_allowed|independent_person|required_by_profile",
    "verification_method_expectation": ["review", "analysis", "test", "inspection"]
  },
  "review": {
    "review_status": "not_required|not_started|under_review|reviewed|approved|rejected",
    "reviewers": ["string"],
    "independent_reviewer_id": "string",
    "review_independence_evidence": ["string"],
    "approver_id": "string",
    "approval_timestamp": "datetime"
  },
  "timestamps": {
    "created_at": "datetime",
    "updated_at": "datetime"
  },
  "payload": {}
}
```

## 4. Project And Configuration Schemas

### Project

```json
{
  "payload": {
    "project_key": "string",
    "name": "string",
    "description": "string",
    "active_profile_id": "string",
    "lifecycle_phase": "concept|development|verification|release|maintenance",
    "regulatory_scope": {
      "iso26262": true,
      "aspice_level3": true,
      "iso29119": true,
      "unece_r155": false,
      "unece_r156": false
    }
  }
}
```

### ProjectConfiguration

```json
{
  "payload": {
    "version_update_mode": "automatic_new_version|ask_user",
    "sphinx_source_root": "string",
    "strict_unknown_fields": false,
    "enabled_artefact_fields": {},
    "baseline_policy": {},
    "validation_policy": {},
    "reporting_policy": {}
  }
}
```

### AssuranceProfile

```json
{
  "payload": {
    "profile_id": "string",
    "classification": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "inherits_from_profile_id": "string",
    "standards_traceability_matrix_ref": "string",
    "artefact_classes": {},
    "relationship_types": {},
    "rules": {},
    "reports": {}
  }
}
```

### ProjectScope

```json
{
  "payload": {
    "scope_statement": "string",
    "included_systems": ["string"],
    "excluded_systems": ["string"],
    "included_aspice_processes": ["string"],
    "excluded_aspice_processes": ["string"],
    "scope_boundaries": ["string"],
    "justification_refs": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### ASPICEScopeDecision

```json
{
  "payload": {
    "process_id": "string",
    "process_name": "string",
    "scope_status": "in_scope|out_of_scope|partially_in_scope",
    "rationale": "string",
    "affected_work_products": ["string"],
    "evidence_refs": ["string"],
    "approved_by": "string",
    "approved_at": "datetime"
  }
}
```

### TailoringDecision

```json
{
  "payload": {
    "scope_type": "project|component|interface|requirement|baseline",
    "scope_id": "string",
    "target_kind": "artefact_class|relationship_type|rule|field",
    "target_id": "string",
    "previous_applicability": "mandatory|optional|conditional|disabled|not_applicable",
    "tailored_applicability": "mandatory|optional|conditional|disabled|not_applicable",
    "rationale": "string",
    "evidence_refs": ["string"],
    "requested_by": "string",
    "approved_by": "string",
    "approved_at": "datetime",
    "decision_basis": "human_approved_evidence"
  }
}
```

## 5. Safety Management And Planning Schemas

### SafetyPlan

```json
{
  "payload": {
    "scope": "string",
    "safety_lifecycle": "string",
    "roles_and_responsibilities": ["string"],
    "planned_work_products": ["string"],
    "confirmation_measures": ["string"],
    "verification_strategy": "string",
    "configuration_management_strategy": "string",
    "change_management_strategy": "string",
    "evidence_refs": ["string"]
  }
}
```

### SoftwareSafetyPlan

```json
{
  "payload": {
    "software_scope": "string",
    "software_lifecycle": "string",
    "software_work_products": ["string"],
    "software_verification_activities": ["string"],
    "software_integration_strategy": "string",
    "tools_and_environments": ["string"],
    "confirmation_measures": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### SafetyCase

```json
{
  "payload": {
    "claim": "string",
    "argument_structure": "string",
    "supported_artefact_refs": ["string"],
    "open_assumptions": ["string"],
    "open_issues": ["string"],
    "confidence_argument": "string",
    "evidence_refs": ["string"]
  }
}
```

### SystemSafetyConcept

```json
{
  "payload": {
    "concept_scope": "string",
    "system_safety_requirements": ["string"],
    "safety_mechanisms": ["string"],
    "external_interface_assumptions": ["string"],
    "software_allocation_refs": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### DevelopmentEnvironmentRecord

```json
{
  "payload": {
    "environment_name": "string",
    "toolchain_refs": ["string"],
    "runtime_platform": "string",
    "configuration_refs": ["string"],
    "qualification_or_confidence_refs": ["string"],
    "known_limitations": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### QualityAssuranceRecord

```json
{
  "payload": {
    "qa_activity": "string",
    "scope": "string",
    "planned_by": "string",
    "performed_by": "string",
    "independence_evidence": ["string"],
    "findings": ["string"],
    "closure_refs": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### DevelopmentPlan

```json
{
  "payload": {
    "scope": "string",
    "milestones": ["string"],
    "deliverables": ["string"],
    "responsibilities": ["string"],
    "process_refs": ["string"]
  }
}
```

### VerificationPlan

```json
{
  "payload": {
    "scope": "string",
    "verification_levels": ["unit", "integration", "software", "system"],
    "verification_methods": ["review", "analysis", "test", "inspection"],
    "entry_criteria": ["string"],
    "exit_criteria": ["string"],
    "environments": ["string"],
    "evidence_expectations": ["string"]
  }
}
```

### ValidationPlan

```json
{
  "payload": {
    "scope": "string",
    "validation_objectives": ["string"],
    "validation_methods": ["string"],
    "acceptance_criteria": ["string"],
    "external_refs": ["string"]
  }
}
```

### ConfigurationManagementPlan

```json
{
  "payload": {
    "configuration_item_types": ["string"],
    "baseline_strategy": "string",
    "versioning_strategy": "string",
    "access_control_strategy": "string",
    "audit_strategy": "string"
  }
}
```

### ChangeManagementRecord

```json
{
  "payload": {
    "change_request_id": "string",
    "change_summary": "string",
    "reason": "string",
    "affected_artefacts": ["string"],
    "impact_analysis_refs": ["string"],
    "approval_status": "draft|approved|rejected|implemented|closed",
    "verification_impact": ["string"]
  }
}
```

### ConfirmationMeasureRecord

```json
{
  "payload": {
    "measure_type": "review|audit|assessment|confirmation_review",
    "scope": "string",
    "performed_by": "string",
    "independence_level": "none|independent_person|independent_team|external",
    "performed_at": "datetime",
    "result": "pass|fail|open_issues",
    "findings": ["string"],
    "evidence_refs": ["string"]
  }
}
```

## 6. System-Level Reference Schemas

### ItemDefinition

```json
{
  "payload": {
    "item_scope": "string",
    "item_boundaries": ["string"],
    "operational_context": "string",
    "dependencies": ["string"],
    "external_interfaces": ["string"],
    "external_refs": ["string"]
  }
}
```

### HazardAnalysisRiskAssessment

```json
{
  "payload": {
    "external_refs": ["string"],
    "hazard_ids": ["string"],
    "safety_goal_ids": ["string"],
    "asil_classifications": ["QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"]
  }
}
```

### SafetyGoal

```json
{
  "payload": {
    "statement": "string",
    "asil_level": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "source_hazard_refs": ["string"],
    "safe_state": "string",
    "linked_requirements": ["string"]
  }
}
```

### FunctionalSafetyRequirement

```json
{
  "payload": {
    "statement": "string",
    "asil_level": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "source_safety_goal_refs": ["string"],
    "allocated_to": ["string"],
    "verification_intent": ["string"]
  }
}
```

### TechnicalSafetyRequirement

```json
{
  "payload": {
    "statement": "string",
    "asil_level": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "source_fsr_refs": ["string"],
    "allocated_to": ["string"],
    "linked_software_safety_requirements": ["string"]
  }
}
```

### SystemDesignElement

```json
{
  "payload": {
    "element_type": "system_component|function|subsystem|external_dependency",
    "responsibilities": ["string"],
    "interfaces": ["string"],
    "allocated_requirements": ["string"]
  }
}
```

### HardwareSoftwareInterface

```json
{
  "payload": {
    "source_element": "string",
    "destination_element": "string",
    "data_items": [],
    "timing_constraints": {},
    "resource_constraints": {},
    "error_handling": {},
    "linked_requirements": ["string"]
  }
}
```

## 7. Software Requirements Schemas

### SoftwareSafetyRequirement

```json
{
  "payload": {
    "statement": "string",
    "asil_level": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "safety_relevant": true,
    "source_refs": ["string"],
    "rationale": "string",
    "acceptance_criteria": ["string"],
    "allocated_to_components": ["string"],
    "linked_interfaces": ["string"],
    "linked_safeguards": ["string"],
    "verification_intent": {
      "methods": ["review", "analysis", "test", "inspection"],
      "levels": ["unit", "integration", "software", "system"]
    }
  }
}
```

### SoftwareRequirement

```json
{
  "payload": {
    "statement": "string",
    "requirement_type": "functional|interface|timing|diagnostic|fault_handling|performance|security|update",
    "asil_level": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "safety_relevant": false,
    "source_refs": ["string"],
    "rationale": "string",
    "acceptance_criteria": ["string"],
    "allocated_to_components": ["string"],
    "verification_intent": {}
  }
}
```

### DerivedSoftwareRequirement

```json
{
  "payload": {
    "statement": "string",
    "derived_from": ["string"],
    "derivation_rationale": "string",
    "allocated_to_components": ["string"],
    "verification_intent": {}
  }
}
```

### Assumption

```json
{
  "payload": {
    "statement": "string",
    "category": "data_validity|timing|sequence|range|protocol|mode|resource|security|update",
    "made_by": "string",
    "applies_to_interface": "string",
    "linked_safeguards": ["string"],
    "linked_tests": ["string"]
  }
}
```

### RequirementReviewRecord

```json
{
  "payload": {
    "reviewed_artefacts": ["string"],
    "review_method": "inspection|walkthrough|peer_review|confirmation_review",
    "reviewers": ["string"],
    "independence_level": "none|independent_person|independent_team|external",
    "result": "accepted|rework_required|rejected",
    "findings": ["string"],
    "evidence_refs": ["string"]
  }
}
```

## 8. Architecture And Interface Schemas

### SoftwareComponent

```json
{
  "payload": {
    "classification": "QM|ASIL_A|ASIL_B|ASIL_C|ASIL_D",
    "responsibilities": ["string"],
    "owned_interfaces": ["string"],
    "consumed_interfaces": ["string"],
    "depends_on_components": ["string"],
    "allocated_requirements": ["string"],
    "linked_safeguards": ["string"],
    "implementation_items": ["string"],
    "has_mixed_criticality_interaction": false
  }
}
```

### SoftwareArchitecture

```json
{
  "payload": {
    "architecture_scope": "string",
    "components": ["string"],
    "interfaces": ["string"],
    "safety_mechanisms": ["string"],
    "allocation_rationale": "string",
    "architecture_decisions": ["string"],
    "analysis_refs": ["string"]
  }
}
```

### InterfaceContract

```json
{
  "payload": {
    "source_component": "string",
    "destination_component": "string",
    "interaction_kind": "data|service_call|event|signal",
    "direction": "unidirectional|bidirectional",
    "classification": "QM_to_ASIL|ASIL_to_QM|ASIL_to_ASIL|QM_to_QM",
    "payload_definition": [
      {
        "name": "string",
        "type": "string",
        "unit": "string",
        "allowed_range": "string",
        "allowed_values": ["string"],
        "encoding": "string",
        "optional": false
      }
    ],
    "timing": {
      "update_period_ms": 0,
      "timeout_ms": 0,
      "freshness_ms": 0,
      "response_time_ms": 0
    },
    "validity_semantics": {
      "has_validity_flag": false,
      "invalid_value_behavior": "reject|clamp|default|ignore|diagnose",
      "default_value": "string"
    },
    "error_handling": {
      "on_invalid": "string",
      "on_timeout": "string",
      "on_stale": "string",
      "on_sequence_error": "string"
    },
    "security_relevant": false,
    "software_update_relevant": false
  }
}
```

### AssumptionGuaranteeContract

```json
{
  "payload": {
    "asil_component": "string",
    "interface_id": "string",
    "assumptions": [
      {
        "id": "string",
        "statement": "string",
        "category": "data_validity|timing|sequence|range|protocol|mode|resource|security|update",
        "linked_safeguards": ["string"],
        "linked_tests": ["string"]
      }
    ],
    "guarantees": [
      {
        "id": "string",
        "statement": "string",
        "category": "reject|clamp|degrade|diagnose|ignore|default",
        "linked_safeguards": ["string"],
        "linked_tests": ["string"]
      }
    ]
  }
}
```

### Safeguard

```json
{
  "payload": {
    "safeguard_type": "range_check|timeout_supervision|plausibility_check|validity_check|sequence_check|fallback_handling|degraded_mode_transition|diagnostic_reporting|rate_limiting|state_gating",
    "allocated_component": "string",
    "linked_interface": "string",
    "protects_against": ["string"],
    "expected_response": ["string"],
    "linked_requirements": ["string"],
    "linked_implementation_items": ["string"],
    "linked_tests": ["string"]
  }
}
```

### SoftwarePartitioningElement

```json
{
  "payload": {
    "partition_name": "string",
    "partitioning_mechanism": "string",
    "allocated_components": ["string"],
    "isolation_claims": ["string"],
    "freedom_from_interference_refs": ["string"]
  }
}
```

### ResourceUsageConstraint

```json
{
  "payload": {
    "constraint_type": "timing|memory|cpu|communication|scheduling|stack|io",
    "applies_to": ["string"],
    "limit": "string",
    "unit": "string",
    "verification_refs": ["string"]
  }
}
```

### ArchitectureReviewRecord

```json
{
  "payload": {
    "reviewed_artefacts": ["string"],
    "reviewers": ["string"],
    "independence_level": "none|independent_person|independent_team|external",
    "result": "accepted|rework_required|rejected",
    "findings": ["string"],
    "evidence_refs": ["string"]
  }
}
```

## 9. Design And Implementation Schemas

### SoftwareUnit

```json
{
  "payload": {
    "parent_component": "string",
    "responsibilities": ["string"],
    "provided_interfaces": ["string"],
    "required_interfaces": ["string"],
    "allocated_requirements": ["string"]
  }
}
```

### SoftwareUnitDesign

```json
{
  "payload": {
    "software_unit": "string",
    "design_description": "string",
    "inputs": ["string"],
    "outputs": ["string"],
    "internal_states": ["string"],
    "algorithms": ["string"],
    "error_handling": ["string"],
    "linked_requirements": ["string"]
  }
}
```

### ImplementationItem

```json
{
  "payload": {
    "repo_path": "string",
    "language": "string",
    "file_type": "source|header|config|script|manifest|model",
    "implements_components": ["string"],
    "implements_interfaces": ["string"],
    "implements_safeguards": ["string"],
    "satisfies_requirements": ["string"],
    "implementation_constraints": ["string"],
    "review_status": "draft|reviewed|approved|changes_requested",
    "commit_ref": "string"
  }
}
```

### SourceCodeReference

```json
{
  "payload": {
    "repo_url": "string",
    "repo_path": "string",
    "commit_ref": "string",
    "line_ref": "string",
    "language": "string",
    "linked_implementation_items": ["string"]
  }
}
```

### BuildConfiguration

```json
{
  "payload": {
    "build_id": "string",
    "source_revision": "string",
    "compiler_toolchain": "string",
    "build_options": ["string"],
    "dependencies": ["string"],
    "artifact_refs": ["string"]
  }
}
```

### CompilerToolchainConfiguration

```json
{
  "payload": {
    "toolchain_name": "string",
    "toolchain_version": "string",
    "compiler": "string",
    "compiler_version": "string",
    "configuration_options": ["string"],
    "tool_confidence_refs": ["string"]
  }
}
```

### ImplementationReviewRecord

```json
{
  "payload": {
    "reviewed_items": ["string"],
    "reviewers": ["string"],
    "independence_level": "none|independent_person|independent_team|external",
    "result": "accepted|rework_required|rejected",
    "findings": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### StaticAnalysisResult

```json
{
  "payload": {
    "tool": "string",
    "tool_version": "string",
    "scope": ["string"],
    "ruleset": "string",
    "execution_time": "datetime",
    "summary": {},
    "open_findings": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### CodingGuidelineComplianceRecord

```json
{
  "payload": {
    "guideline": "string",
    "guideline_version": "string",
    "scope": ["string"],
    "compliance_status": "compliant|deviations_exist|not_applicable",
    "deviations": ["string"],
    "evidence_refs": ["string"]
  }
}
```

## 10. Verification And Test Schemas

### TestPlan

```json
{
  "payload": {
    "scope": "string",
    "objectives": ["string"],
    "strategy": "string",
    "resources": ["string"],
    "schedule": "string",
    "risks": ["string"],
    "entry_criteria": ["string"],
    "exit_criteria": ["string"]
  }
}
```

### TestSpecification

```json
{
  "payload": {
    "objective": "string",
    "test_basis": ["string"],
    "derived_from_requirements": ["string"],
    "derived_from_safeguards": ["string"],
    "linked_interfaces": ["string"],
    "linked_components": ["string"],
    "verification_method": "test|analysis|inspection|review",
    "test_level": "unit|integration|component_integration|software_system|system",
    "fault_class": "nominal|invalid_value|out_of_range|timeout|stale_data|inconsistent_validity|overload|sequence_error|degraded_mode_response|security|update",
    "coverage_target": "string",
    "pass_criteria": ["string"],
    "expected_evidence": ["string"]
  }
}
```

### TestCase

```json
{
  "payload": {
    "test_specification": "string",
    "preconditions": ["string"],
    "inputs": ["string"],
    "expected_results": ["string"],
    "pass_fail_criteria": ["string"],
    "linked_requirements": ["string"]
  }
}
```

### TestProcedure

```json
{
  "payload": {
    "test_cases": ["string"],
    "execution_steps": ["string"],
    "setup": ["string"],
    "cleanup": ["string"],
    "test_environment": "string"
  }
}
```

### TestEnvironment

```json
{
  "payload": {
    "environment_name": "string",
    "hardware": ["string"],
    "software": ["string"],
    "tools": ["string"],
    "configuration_refs": ["string"],
    "limitations": ["string"]
  }
}
```

### TestResult

```json
{
  "payload": {
    "test_case": "string",
    "test_procedure": "string",
    "test_environment": "string",
    "build_ref": "string",
    "baseline_ref": "string",
    "execution_time": "datetime",
    "verdict": "pass|fail|blocked|not_run|inconclusive",
    "actual_results": ["string"],
    "evidence_refs": ["string"],
    "defect_refs": ["string"],
    "waiver_ref": "string",
    "notes": "string"
  }
}
```

### CoverageResult

```json
{
  "payload": {
    "coverage_type": "requirements|structural|interface|fault|regression",
    "scope": ["string"],
    "target": "string",
    "achieved": "string",
    "gaps": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### RequirementsCoverageRecord

```json
{
  "payload": {
    "requirements": ["string"],
    "covered_requirements": ["string"],
    "uncovered_requirements": ["string"],
    "coverage_percentage": 0,
    "evidence_refs": ["string"]
  }
}
```

### TestCompletionReport

```json
{
  "payload": {
    "test_scope": "string",
    "summary": "string",
    "executed_tests": ["string"],
    "open_defects": ["string"],
    "coverage_summary": "string",
    "recommendation": "accept|reject|conditional_accept"
  }
}
```

## 11. Analysis And Assurance Schemas

### SafetyAnalysis

```json
{
  "payload": {
    "analysis_type": "FMEA|FTA|DFA|freedom_from_interference|dependent_failure|other",
    "scope": ["string"],
    "method": "string",
    "findings": ["string"],
    "mitigations": ["string"],
    "linked_requirements": ["string"],
    "linked_safeguards": ["string"],
    "evidence_refs": ["string"]
  }
}
```

### InterfaceRiskAnalysis

```json
{
  "payload": {
    "interface_id": "string",
    "risk_scenarios": ["string"],
    "fault_classes": ["string"],
    "assumptions": ["string"],
    "safeguards": ["string"],
    "residual_risk": "string",
    "evidence_refs": ["string"]
  }
}
```

### FreedomFromInterferenceArgument

```json
{
  "payload": {
    "scope": ["string"],
    "interference_channels": ["timing", "memory", "communication", "control_flow", "data"],
    "prevention_mechanisms": ["string"],
    "verification_refs": ["string"],
    "argument_summary": "string"
  }
}
```

### ASILDecompositionArgument

```json
{
  "payload": {
    "decomposed_requirement": "string",
    "decomposition_rationale": "string",
    "independence_argument": "string",
    "allocated_elements": ["string"],
    "verification_refs": ["string"]
  }
}
```

### AssuranceArgument

```json
{
  "payload": {
    "claim": "string",
    "argument": "string",
    "evidence_refs": ["string"],
    "assumptions": ["string"],
    "open_issues": ["string"]
  }
}
```

## 12. Tool, Process, And Qualification Schemas

### ToolInventoryItem

```json
{
  "payload": {
    "tool_name": "string",
    "tool_version": "string",
    "tool_purpose": "string",
    "used_for": ["string"],
    "supplier": "string",
    "configuration": "string"
  }
}
```

### ToolConfidenceAssessment

```json
{
  "payload": {
    "tool_id": "string",
    "use_case": "string",
    "potential_errors": ["string"],
    "error_detection_measures": ["string"],
    "confidence_rationale": "string",
    "qualification_required": false
  }
}
```

### ToolQualificationEvidence

```json
{
  "payload": {
    "tool_id": "string",
    "qualification_strategy": "string",
    "qualification_evidence_refs": ["string"],
    "result": "qualified|not_required|rejected|pending"
  }
}
```

### ProcessComplianceRecord

```json
{
  "payload": {
    "process_ref": "string",
    "scope": "string",
    "compliance_status": "compliant|deviations_exist|not_assessed",
    "deviations": ["string"],
    "evidence_refs": ["string"]
  }
}
```

## 13. Issue, Defect, And Change Schemas

### ValidationIssue

```json
{
  "payload": {
    "rule_id": "string",
    "severity": "critical|major|minor|info",
    "message": "string",
    "affected_artefacts": ["string"],
    "affected_relationships": ["string"],
    "status": "open|resolved|suppressed|obsolete",
    "remediation_hint": "string"
  }
}
```

### DefectRecord

```json
{
  "payload": {
    "defect_id": "string",
    "summary": "string",
    "description": "string",
    "severity": "critical|major|minor|trivial",
    "status": "open|in_analysis|fixed|verified|closed|rejected",
    "affected_artefacts": ["string"],
    "detected_by": "string",
    "resolution": "string",
    "verification_refs": ["string"]
  }
}
```

### ChangeRequest

```json
{
  "payload": {
    "change_id": "string",
    "summary": "string",
    "reason": "string",
    "status": "draft|submitted|approved|rejected|implemented|closed",
    "affected_artefacts": ["string"],
    "impact_analysis_refs": ["string"],
    "approval_refs": ["string"]
  }
}
```

### ChangeSet

```json
{
  "payload": {
    "change_request": "string",
    "changed_artefacts": ["string"],
    "changed_relationships": ["string"],
    "created_revisions": ["string"],
    "summary": "string"
  }
}
```

### SuspectState

```json
{
  "payload": {
    "artefact_id": "string",
    "trigger_event_id": "string",
    "reason": "string",
    "status": "open|cleared|obsolete",
    "clearance_reason": "string",
    "cleared_by": "string",
    "cleared_at": "datetime"
  }
}
```

### ImpactAnalysisResult

```json
{
  "payload": {
    "trigger": "string",
    "impacted_artefacts": ["string"],
    "impacted_relationships": ["string"],
    "impact_paths": [],
    "suspect_recommendations": ["string"],
    "retest_recommendations": ["string"]
  }
}
```

## 14. Evidence And Reporting Schemas

### EvidenceReference

```json
{
  "payload": {
    "evidence_type": "document|test_log|report|review_record|external_link|binary_artifact",
    "uri": "string",
    "checksum": "string",
    "description": "string",
    "created_by": "string",
    "created_at": "datetime"
  }
}
```

### EvidenceBundle

```json
{
  "payload": {
    "baseline_id": "string",
    "included_evidence_refs": ["string"],
    "generated_reports": ["string"],
    "validation_summary": {},
    "coverage_summary": {}
  }
}
```

### GeneratedReport

```json
{
  "payload": {
    "report_type": "traceability_matrix|consistency|coverage|baseline_comparison|interface_assurance|release_gate|evidence_bundle",
    "format": "json|html|csv|pdf",
    "scope": {},
    "uri": "string",
    "generated_at": "datetime"
  }
}
```

### TraceabilityMatrix

```json
{
  "payload": {
    "scope": {},
    "rows": [],
    "generated_from_revision_set": ["string"],
    "gaps": ["string"]
  }
}
```

### InterfaceAssuranceReport

```json
{
  "payload": {
    "interfaces": ["string"],
    "assumptions": ["string"],
    "safeguards": ["string"],
    "tests": ["string"],
    "evidence_status": {},
    "gaps": ["string"]
  }
}
```

## 15. Audit And History Schemas

### AuditEvent

```json
{
  "payload": {
    "event_type": "string",
    "actor_type": "user|system|job",
    "actor_id": "string",
    "correlation_id": "string",
    "causation_id": "string",
    "affected_artefacts": ["string"],
    "affected_relationships": ["string"],
    "event_payload": {}
  }
}
```

### ImportRun

```json
{
  "payload": {
    "source_tool": "sphinx-needs",
    "source_root": "string",
    "state": "created|payload_received|parsed|parse_failed|normalized|normalization_failed|changes_detected|no_changes_detected|waiting_for_user|persisting|persisted|validation_running|completed|completed_no_changes_applied|completed_with_errors|failed|cancelled",
    "version_update_mode": "automatic_new_version|ask_user",
    "summary": {},
    "diagnostics": []
  }
}
```

### ArtefactRevision

```json
{
  "payload": {
    "artefact_id": "string",
    "revision_number": 1,
    "payload_snapshot": {},
    "change_reason": "string",
    "changed_by": "string",
    "changed_at": "datetime",
    "import_run_id": "string"
  }
}
```

### RelationshipRevision

```json
{
  "payload": {
    "relationship_id": "string",
    "revision_number": 1,
    "payload_snapshot": {},
    "changed_by": "string",
    "changed_at": "datetime",
    "import_run_id": "string"
  }
}
```

### Baseline

```json
{
  "payload": {
    "baseline_id": "string",
    "project_id": "string",
    "state": "requested|update_lock_acquired|eligibility_check_running|eligibility_failed|creating_snapshot|created|approved|released|obsolete|failed|cancelled",
    "profile_id": "string",
    "included_artefact_revisions": ["string"],
    "included_relationship_revisions": ["string"],
    "validation_summary": {},
    "coverage_summary": {},
    "suspect_summary": {},
    "release_gate_result": "string"
  }
}
```

### ReleaseGateResult

```json
{
  "payload": {
    "baseline_id": "string",
    "status": "not_evaluated|running|passed|failed|cancelled|stale",
    "result": "pass|fail|null",
    "blocking_issues": ["string"],
    "warning_issues": ["string"],
    "evaluated_rules": ["string"],
    "evaluated_at": "datetime",
    "evaluated_by": "string"
  }
}
```
