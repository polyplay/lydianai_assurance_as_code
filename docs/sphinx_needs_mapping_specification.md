# Sphinx-Needs Mapping Specification

## 1. Purpose

This document defines how Sphinx-Needs authored objects map to Assurance-as-Code canonical artefacts and relationships.

Sphinx-Needs is the authoring and publishing shell. The back-end owns canonical truth.

## 2. Mapping Principles

AAC-SNEEDS-FR-001
Each Sphinx-Needs object intended for import shall have a stable ID.

AAC-SNEEDS-FR-002
The Sphinx object ID shall map to the canonical artefact ID unless a project-specific ID mapping exists.

AAC-SNEEDS-FR-003
Sphinx fields shall be normalized into canonical payload fields.

AAC-SNEEDS-FR-004
Sphinx links shall be normalized into canonical relationships.

AAC-SNEEDS-FR-005
Unknown Sphinx fields shall be preserved as raw source data unless strict import mode rejects them.

AAC-SNEEDS-FR-006
The source document path and source object ID shall be preserved on every imported artefact revision.

## 3. Custom Need Types

The Sphinx-Needs profile shall define these need types:

| Sphinx Type | Canonical Resource |
|---|---|
| `project_aac` | Project |
| `project_scope` | ProjectScope |
| `aspice_scope_decision` | ASPICEScopeDecision |
| `safety_plan` | SafetyPlan |
| `sw_safety_plan` | SoftwareSafetyPlan |
| `safety_case` | SafetyCase |
| `system_safety_concept` | SystemSafetyConcept |
| `verification_plan` | VerificationPlan |
| `config_mgmt_plan` | ConfigurationManagementPlan |
| `change_record` | ChangeManagementRecord |
| `confirmation_record` | ConfirmationMeasureRecord |
| `dev_environment` | DevelopmentEnvironmentRecord |
| `quality_assurance` | QualityAssuranceRecord |
| `item_def` | ItemDefinition |
| `hara_ref` | HazardAnalysisRiskAssessment |
| `safety_goal` | SafetyGoal |
| `fsr` | FunctionalSafetyRequirement |
| `tsr` | TechnicalSafetyRequirement |
| `sw_safety_req` | SoftwareSafetyRequirement |
| `sw_req` | SoftwareRequirement |
| `derived_sw_req` | DerivedSoftwareRequirement |
| `assumption` | Assumption |
| `req_review` | RequirementReviewRecord |
| `sw_arch` | SoftwareArchitecture |
| `sw_comp` | SoftwareComponent |
| `sw_interface` | InterfaceContract |
| `ag_contract` | AssumptionGuaranteeContract |
| `safeguard` | Safeguard |
| `partitioning_element` | SoftwarePartitioningElement |
| `resource_constraint` | ResourceUsageConstraint |
| `arch_review` | ArchitectureReviewRecord |
| `sw_unit` | SoftwareUnit |
| `unit_design` | SoftwareUnitDesign |
| `impl_item` | ImplementationItem |
| `source_ref` | SourceCodeReference |
| `build_config` | BuildConfiguration |
| `toolchain_config` | CompilerToolchainConfiguration |
| `impl_review` | ImplementationReviewRecord |
| `static_analysis` | StaticAnalysisResult |
| `coding_compliance` | CodingGuidelineComplianceRecord |
| `test_spec` | TestSpecification |
| `test_case` | TestCase |
| `test_procedure` | TestProcedure |
| `test_environment` | TestEnvironment |
| `test_result` | TestResult |
| `coverage_result` | CoverageResult |
| `requirements_coverage` | RequirementsCoverageRecord |
| `safety_analysis` | SafetyAnalysis |
| `interface_risk` | InterfaceRiskAnalysis |
| `ffi_argument` | FreedomFromInterferenceArgument |
| `asil_decomposition` | ASILDecompositionArgument |
| `assurance_argument` | AssuranceArgument |
| `tool_inventory` | ToolInventoryItem |
| `tool_confidence` | ToolConfidenceAssessment |
| `tool_qualification` | ToolQualificationEvidence |
| `process_compliance` | ProcessComplianceRecord |
| `defect_record` | DefectRecord |
| `change_request` | ChangeRequest |
| `evidence_ref` | EvidenceReference |

Generated resources such as baselines, revisions, validation issues, import runs, audit events, traceability matrices, interface assurance reports, and generated reports are produced by the back-end. The back-end may export those resources into Sphinx-Needs for publishing.

## 4. Common Field Mapping

| Sphinx Field | Canonical Field |
|---|---|
| `id` | `artefact_id` |
| title/body title | `title` |
| body content | `description` |
| `status` | `status` |
| `owner` | `owner` |
| `asil` | `payload.asil_level` |
| `classification` | `payload.classification` |
| `tags` | `tags` |
| source document | `source_document` |
| Sphinx type | `source_object_type` |
| `standards_refs` | `standards_refs` |
| `work_product_kind` | `work_product_kind` |
| `review_expectation` | `review_expectation` |
| `independence_expectation` | `independence_expectation` |
| `verification_method` | `verification_method` |

## 5. Link Mapping

| Sphinx Link | Canonical Relationship |
|---|---|
| `allocates_to` | `allocates_to` |
| `satisfies` | `satisfies` |
| `depends_on` | `depends_on` |
| `interacts_via` | `interacts_via` |
| `constrains` | `constrains` |
| `assumes` | `assumes` |
| `guarantees` | `guarantees` |
| `protects` | `protects` |
| `implements` | `implements` |
| `verifies` | `verifies` |
| `produces_result_for` | `produces_result_for` |
| `derived_from` | `derives_from` |
| `references` | `references` |

## 6. Required Extra Options

The Sphinx-Needs configuration shall support at least:

```python
needs_extra_options = [
    "status",
    "owner",
    "asil",
    "classification",
    "source_kind",
    "external_ref",
    "rationale",
    "acceptance_criteria",
    "verification_method",
    "test_level",
    "fault_class",
    "source_component",
    "destination_component",
    "interaction_kind",
    "direction",
    "payload_definition",
    "timing",
    "validity_semantics",
    "error_handling",
    "safeguard_type",
    "expected_response",
    "repo_path",
    "language",
    "file_type",
    "build_ref",
    "environment_ref",
    "verdict",
    "evidence_refs",
    "baseline_ref",
    "review_state",
    "standards_refs",
    "work_product_kind",
    "review_expectation",
    "independence_expectation",
    "independent_reviewer",
    "review_independence_evidence",
    "security_relevant",
    "software_update_relevant"
]
```

## 7. Import Normalization

AAC-SNEEDS-FR-010
The adapter shall map Sphinx scalar fields to canonical scalar fields.

AAC-SNEEDS-FR-011
The adapter shall parse list-like fields into arrays.

AAC-SNEEDS-FR-012
The adapter shall parse structured JSON/YAML field values where configured.

AAC-SNEEDS-FR-013
The adapter shall produce diagnostics for invalid enum values.

AAC-SNEEDS-FR-014
The adapter shall preserve raw source values for audit and debugging.

## 8. Generated Publishing Back To Sphinx

AAC-SNEEDS-FR-020
The back-end may export generated validation issues, reports, baselines, and traceability views as Sphinx-importable content.

AAC-SNEEDS-FR-021
Generated Sphinx content shall not become canonical truth unless explicitly re-imported and accepted by the back-end.
