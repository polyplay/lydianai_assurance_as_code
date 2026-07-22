# ASIL Profile Configuration Schema

## 1. Purpose

This document defines the configurable assurance profile schema used by the Assurance-as-Code platform.

Profiles control which artefacts, relationships, rules, evidence types, and review states are mandatory, optional, conditional, disabled, or not applicable for a project.

The default high-rigor profile is ASIL D with Automotive SPICE PAM 4.0 capability level 3 expectations. Lower ASIL or lower ASPICE capability targets may tailor requirements down by configuration.

## 2. Reference Basis

The profile model is structured to support:

- ISO 26262 software-system functional safety evidence, especially software requirements, architecture, implementation, integration, verification, configuration, and safety analysis concerns.
- Automotive SPICE PAM 4.0 evidence expectations up to capability level 3, especially defined process use, work products, traceability, verification, validation, quality assurance, configuration management, problem resolution, and change management.
- ISO/IEC/IEEE 29119 testing artefacts, especially test processes and test documentation.
- UNECE R155 cybersecurity management evidence where cybersecurity-related safety interactions exist.
- UNECE R156 software update management evidence where software release/update control is in scope.

Clause-exact mapping shall be validated later against licensed copies of the standards and project-specific process definitions.

## 3. Profile Scope

AAC-PROFILE-FR-001
The system shall assign one active assurance profile at project level.

AAC-PROFILE-FR-002
The system shall support scoped overrides at component, interface, requirement, and baseline level.

AAC-PROFILE-FR-003
Project-level profile selection shall be mandatory.

AAC-PROFILE-FR-004
If a lower-level scoped profile conflicts with a project-level profile, the system shall apply the stricter applicable requirement unless an approved tailoring decision exists.

AAC-PROFILE-FR-005
The project lead shall be able to make an artefact optional when evidence and rationale are provided.

AAC-PROFILE-FR-006
Project lead tailoring decisions shall be versioned, audited, and preserved in baselines.

AAC-PROFILE-FR-007
The system shall derive artefact visibility, mandatory artefact classes, required fields, validation rules, review expectations, and release-gate criteria from the project assurance configuration.

AAC-PROFILE-FR-008
The project assurance configuration shall treat ISO 26262 ASIL classification and Automotive SPICE capability target as separate configuration axes.

AAC-PROFILE-FR-009
When several configured standards or process targets apply to the same artefact or rule, the stricter applicability shall win unless an approved tailoring decision exists.

## 4. Applicability Values

AAC-PROFILE-DR-001
The schema shall support these applicability values:

- `mandatory`
- `optional`
- `conditional`
- `disabled`
- `not_applicable`

AAC-PROFILE-DR-002
`mandatory` means the resource or relationship is required in the configured scope.

AAC-PROFILE-DR-003
`optional` means the resource or relationship is not required, but if present it shall be validated.

AAC-PROFILE-DR-004
`conditional` means the resource or relationship is required only when a configured condition evaluates true.

AAC-PROFILE-DR-005
`disabled` means the resource, relationship, or rule is not used by the profile.

AAC-PROFILE-DR-006
`not_applicable` means a normally required resource has been explicitly tailored out for a defined scope with rationale and approval.

## 5. Tailoring Decision Schema

AAC-PROFILE-DR-010
A tailoring decision shall contain:

```yaml
tailoring_decision:
  id: string
  project_id: string
  scope_type: enum[project, component, interface, requirement, baseline]
  scope_id: string
  target_kind: enum[artefact_class, relationship_type, rule]
  target_id: string
  previous_applicability: string
  tailored_applicability: string
  rationale: string
  evidence_refs: [string]
  requested_by: string
  approved_by: string
  approved_at: datetime
  status: enum[draft, approved, rejected, obsolete]
```

AAC-PROFILE-DR-011
An approved tailoring decision shall create an audit event.

AAC-PROFILE-DR-012
An approved tailoring decision shall be included by reference in every affected baseline.

## 6. Profile Schema

AAC-PROFILE-DR-020
An assurance profile shall conform to this logical schema:

```yaml
profile:
  profile_id: string
  name: string
  standard_basis:
    iso26262: string
    automotive_spice: string
    iso29119: string
    unece_r155: string
    unece_r156: string
  standards_traceability_matrix_ref: string
  inherits_from: string | null
  project_classification: enum[QM, ASIL_A, ASIL_B, ASIL_C, ASIL_D]
  project_assurance_configuration:
    project_type: enum[software_system]
    asil_level: enum[QM, ASIL_A, ASIL_B, ASIL_C, ASIL_D]
    aspice_model: enum[ASPICE_PAM_4_0]
    aspice_default_capability_level: integer[1..3]
    aspice_scoped_processes: [string]
    aspice_process_overrides:
      <ASPICE process ID>: integer[1..3]
    r155_applicable: boolean
    r156_applicable: boolean
    has_cybersecurity_relevance: boolean
    has_software_update_relevance: boolean
    test_scope: [unit, integration, software_qualification, system, acceptance]
    visibility_policy: enum[relevant_first, strict_hide, show_all_tagged]
  artefact_classes:
    <ArtefactClass>:
      applicability: enum[mandatory, optional, conditional, disabled, not_applicable]
      visible: boolean
      condition: string | null
      standards_refs: [string]
      required_status_for_baseline: [string]
      required_status_for_release: [string]
      evidence_required: boolean
      tailoring_allowed: boolean
      tailoring_approval_role: enum[admin, project_lead, quality_engineer]
  relationship_types:
    <relationship_type>:
      applicability: enum[mandatory, optional, conditional, disabled, not_applicable]
      condition: string | null
      standards_refs: [string]
      source_types: [string]
      target_types: [string]
      min_count: integer | null
  rules:
    <rule_id>:
      enabled: boolean
      standards_refs: [string]
      severity: enum[critical, major, minor, info]
      execution_modes: [import, immediate, baseline, release_gate, manual]
      blocking_contexts: [import, baseline, release_gate]
      tailoring_allowed: boolean
  reports:
    <report_type>:
      applicability: enum[mandatory, optional, conditional, disabled]
```

AAC-PROFILE-DR-021
`aspice_model` shall be fixed to `ASPICE_PAM_4_0` for the current implementation.

AAC-PROFILE-DR-022
`aspice_default_capability_level` shall support values 1, 2, and 3 only.

AAC-PROFILE-DR-023
`aspice_process_overrides` shall allow a project to target a different capability level for a specific scoped process than the project default.

AAC-PROFILE-DR-024
`visibility_policy=relevant_first` shall show mandatory and conditional artefacts in the normal workflow and keep optional artefacts available from an advanced catalogue.

## 7. ASIL D Default Profile

AAC-PROFILE-FR-020
The system shall provide an `ASIL_D_DEFAULT` profile.

AAC-PROFILE-FR-021
`ASIL_D_DEFAULT` shall enable the full software-system resource model.

AAC-PROFILE-FR-022
`ASIL_D_DEFAULT` shall make the following artefact groups mandatory unless tailored:

- project and configuration records
- project scope and ASPICE scope decisions
- safety case and system safety concept references
- safety planning and software safety planning
- system-level safety references
- software safety requirements and software requirements
- software architecture and component model
- SW-SW interface contracts
- assumption-guarantee contracts for ASIL-relevant interfaces
- safeguards and safety mechanisms
- software unit design and implementation mappings
- source code references
- build and toolchain configuration
- verification plans, test specifications, test cases, test procedures, test environments, test results, and coverage results
- review records
- quality assurance records
- static analysis or justified equivalent evidence
- coding guideline compliance or justified equivalent evidence
- change management and defect/problem records
- baseline, release gate, impact analysis, suspect state, evidence, report, revision, and audit resources

AAC-PROFILE-FR-023
`ASIL_D_DEFAULT` shall enable all critical validation and release-gate rules unless explicitly tailored by project lead with evidence.

AAC-PROFILE-FR-024
`ASIL_D_DEFAULT` shall reference the standards traceability matrix for each mandatory artefact group, relationship group, and rule group.

AAC-PROFILE-FR-025
`ASIL_D_DEFAULT` shall mark the review status of each standards-derived obligation as either `draft_public_reference` or `reviewed_against_controlled_standard`.

## 8. Lower ASIL Profiles

AAC-PROFILE-FR-030
The system shall provide default profiles for `ASIL_A_DEFAULT`, `ASIL_B_DEFAULT`, `ASIL_C_DEFAULT`, and `QM_DEFAULT`.

AAC-PROFILE-FR-031
Lower ASIL profiles shall inherit from the ASIL D resource model and tailor applicability through configuration.

AAC-PROFILE-FR-032
Lower ASIL profiles shall not remove validation of artefacts that are present.

AAC-PROFILE-FR-033
Lower ASIL profiles may reduce mandatory review, analysis, evidence, and coverage obligations according to project-approved tailoring.

AAC-PROFILE-FR-034
Lower ASIL profile defaults shall document every relaxed obligation relative to ASIL D using standards references and tailoring rationale.

## 8.1 Combined ASIL And ASPICE Capability Profiles

AAC-PROFILE-FR-040
The system shall support project creation with both a highest ISO 26262 classification and an Automotive SPICE PAM 4.0 target capability level. The Automotive SPICE target capability shall be exposed in the UI as a project-level planning/default value, not as a consolidated project assessment rating.

AAC-PROFILE-FR-041
The system shall support one project-level default ASPICE capability target and per-process overrides. The system shall derive expected capability targets for each configured in-scope Automotive SPICE process using the project default unless a per-process override exists.

AAC-PROFILE-FR-041A
The system shall allow an administrator to tailor the configured in-scope Automotive SPICE processes and their expected capability levels for a project.

AAC-PROFILE-FR-041B
Every project-specific change to Automotive SPICE process scope or expected process capability shall be documented with rationale, evidence reference, approver, approval timestamp, and audit history.

AAC-PROFILE-FR-042
For a project configured as `ASIL_B` and ASPICE CL2, the system shall not require ASIL D-only confirmation or CL3 process deployment artefacts unless another configured scope makes them mandatory.

AAC-PROFILE-FR-043
For any ASPICE process configured at CL3, the system shall require process definition and process deployment evidence through `ProcessComplianceRecord` and `ASPICEScopeDecision`.

AAC-PROFILE-FR-044
For projects where UNECE R155 is applicable, the derived profile shall require cybersecurity lifecycle artefacts such as `ThreatAnalysisRiskAssessment`, `CybersecurityRequirement`, and `CybersecurityManagementEvidence`.

AAC-PROFILE-FR-045
For projects where UNECE R156 is applicable, the derived profile shall require software update lifecycle artefacts such as `SoftwareUpdateManagementEvidence`, `SoftwareVersionRecord`, `UpdateCampaign`, `UpdateIntegrityEvidence`, and `SoftwareBillOfMaterials`.

## 9. Conditional Examples

AAC-PROFILE-DR-030
The schema shall support condition expressions such as:

```yaml
AssumptionGuaranteeContract:
  applicability: conditional
  condition: "interface.classification in ['QM_to_ASIL', 'ASIL_to_QM', 'ASIL_to_ASIL']"

FreedomFromInterferenceArgument:
  applicability: conditional
  condition: "component.has_mixed_criticality_interaction == true"

ASILDecompositionArgument:
  applicability: conditional
  condition: "requirement.uses_asil_decomposition == true"

ToolQualificationEvidence:
  applicability: conditional
  condition: "tool_confidence.requires_qualification == true"

SoftwareUpdateManagementEvidence:
  applicability: conditional
  condition: "project.software_update_regulatory_scope == true"

CybersecurityInterfaceEvidence:
  applicability: conditional
  condition: "interface.security_relevant == true"
```

## 10. Profile Evaluation Output

AAC-PROFILE-IR-001
Profile evaluation shall produce:

```json
{
  "project_id": "PROJ_001",
  "profile_id": "ASIL_D_DEFAULT",
  "scope": {
    "type": "baseline",
    "id": "BASE_001"
  },
  "required_artefact_classes": [],
  "missing_artefact_classes": [],
  "required_relationships": [],
  "missing_relationships": [],
  "enabled_rules": [],
  "disabled_rules": [],
  "visible_artefact_types": [],
  "mandatory_artefact_types": [],
  "conditional_artefact_types": [],
  "optional_artefact_types": [],
  "not_applicable_artefact_types": [],
  "assurance_configuration": {},
  "tailoring_decisions_applied": [],
  "blocking_gaps": []
}
```
