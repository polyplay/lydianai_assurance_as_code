# ASIL Profile Configuration Schema

## 1. Purpose

This document defines the configurable assurance profile schema used by the Assurance-as-Code platform.

Profiles control which artefacts, relationships, rules, evidence types, and review states are mandatory, optional, conditional, disabled, or not applicable for a project.

The default high-rigor profile is ASIL D. Lower ASIL profiles may tailor requirements down by configuration.

## 2. Reference Basis

The profile model is structured to support:

- ISO 26262 software-system functional safety evidence, especially software requirements, architecture, implementation, integration, verification, configuration, and safety analysis concerns.
- Automotive SPICE Level 3 evidence expectations, especially defined process use, work products, traceability, verification, validation, quality assurance, configuration management, problem resolution, and change management.
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
  artefact_classes:
    <ArtefactClass>:
      applicability: enum[mandatory, optional, conditional, disabled]
      condition: string | null
      standards_refs: [string]
      required_status_for_baseline: [string]
      required_status_for_release: [string]
      evidence_required: boolean
      tailoring_allowed: boolean
      tailoring_approval_role: enum[admin, project_lead, quality_engineer]
  relationship_types:
    <relationship_type>:
      applicability: enum[mandatory, optional, conditional, disabled]
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
  "tailoring_decisions_applied": [],
  "blocking_gaps": []
}
```
