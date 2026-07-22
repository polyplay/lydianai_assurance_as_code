# Resource Model And API Requirements

## 1. Purpose

This document defines the platform resource model and API requirement basis for the Assurance-as-Code tool.

The resource model is intended to support a software-system assurance workflow up to ASIL D and Automotive SPICE PAM 4.0 capability level 3, with configuration support for lower ASIL profiles and lower ASPICE capability targets where some artefacts may be optional or not applicable.

The back-end owns all canonical resources, versions, baselines, rule evaluations, and API behavior.

## 2. Compliance Boundary

AAC-SYS-DEC-001
The platform shall support the artefact and evidence structure needed for an ASIL D software-system compliance workflow.

AAC-SYS-DEC-002
The platform shall not claim compliance by data presence alone. Compliance depends on the correctness, completeness, review status, independence, and project-specific applicability of the stored artefacts and evidence.

AAC-SYS-DEC-003
The platform shall support references to external system-level artefacts where the tool does not author those artefacts directly.

AAC-SYS-DEC-004
The platform shall distinguish between:

- artefacts authored and controlled inside the platform
- artefacts imported from Sphinx documentation
- artefacts referenced from external tools or repositories
- generated artefacts produced by the platform

AAC-SYS-DEC-005
The platform shall maintain a standards traceability matrix that maps resource classes, relationships, rules, and profile obligations to ISO 26262, Automotive SPICE PAM 4.0, ISO/IEC/IEEE 29119, UNECE R155, and UNECE R156 references.

AAC-SYS-DEC-006
Standards-derived resource obligations shall include review status indicating whether they have been reviewed against the controlled standard text.

## 3. Criticality Profile Configuration

AAC-CORE-FR-001
The system shall support configurable assurance profiles.

AAC-CORE-FR-001A
The system shall support a project assurance configuration that combines ISO 26262 ASIL classification, Automotive SPICE PAM 4.0 capability target, ISO 29119 test scope, UNECE R155 applicability, UNECE R156 applicability, and front-end visibility policy.

AAC-CORE-FR-002
The system shall provide at least these profile levels:

- QM
- ASIL A
- ASIL B
- ASIL C
- ASIL D

AAC-CORE-FR-003
The system shall support configuration of mandatory, optional, conditional, and not-applicable artefact classes per assurance profile.

AAC-CORE-FR-004
The system shall support configuration of mandatory, optional, conditional, and not-applicable relationship types per assurance profile.

AAC-CORE-FR-005
The system shall support configuration of mandatory, optional, conditional, and disabled validation rules per assurance profile.

AAC-CORE-FR-006
The system shall allow a project to define its active assurance profile at project, component, requirement, interface, and baseline scope.

AAC-CORE-FR-007
When a lower ASIL profile is selected, the system shall apply the configured mandatory/optional rule set for that profile instead of the ASIL D default.

AAC-CORE-FR-007A
When a lower ASPICE capability target is selected, the system shall apply the configured process evidence and rule set for that target instead of the CL3 default.

AAC-CORE-FR-007B
The system shall support one project-level default ASPICE capability target and per-process capability overrides for scoped Automotive SPICE PAM 4.0 processes. The project-level target shall be treated as a planning/default value, and the derived per-process capability target map shall define the expected capability for each configured in-scope process.

AAC-CORE-FR-007C
The system shall derive front-end artefact visibility from the active project assurance configuration using the configured visibility policy. The MVP default visibility policy shall be `relevant_first`.

AAC-CORE-FR-007D
The system shall allow an administrator to tailor the configured in-scope Automotive SPICE PAM 4.0 processes and their expected capability levels. Each process-scope or process-capability tailoring change shall require a rationale, at least one evidence reference, approver identity, approval timestamp, and audit event.

AAC-CORE-FR-008
When an artefact is marked not applicable, the system shall require a rationale, approver, timestamp, and scope of applicability.

AAC-CORE-FR-009
The system shall preserve not-applicable decisions in baselines and audit history.

## 4. Artefact Requirement States

AAC-DATA-DR-001
Each artefact class in a profile shall have one of these applicability states:

- mandatory
- optional
- conditional
- not_applicable

AAC-DATA-DR-002
If an artefact class is `mandatory`, at least one valid artefact of that class shall exist in the applicable scope.

AAC-DATA-DR-003
If an artefact class is `conditional`, the system shall evaluate a condition expression to determine whether the artefact is required.

AAC-DATA-DR-004
If an artefact class is `optional`, the artefact may be present but shall still be validated if present.

AAC-DATA-DR-005
If an artefact class is `not_applicable`, the artefact shall not be required, but the not-applicable rationale shall be stored and reportable.

AAC-DATA-DR-006
Each artefact type shall support standards reference metadata, including applicable standards references, work-product classification, review expectation, independence expectation, and verification method expectation where applicable.

AAC-DATA-DR-007
Each standards-derived artefact type shall define required content fields in the standards traceability matrix.

## 5. ASIL D Resource Model

The following resource classes form the ASIL D software-system resource model. Some resources may be authored inside Sphinx documentation; others may be imported, referenced, generated, or maintained directly by the back-end.

### 5.1 Project And Configuration Resources

AAC-DATA-DR-010
The system shall support a `Project` resource.

AAC-DATA-DR-011
The system shall support an `AssuranceProfile` resource defining mandatory, optional, conditional, and not-applicable artefact classes, relationships, and rules.

AAC-DATA-DR-012
The system shall support a `ProjectConfiguration` resource defining active profiles, paths, import settings, validation settings, baseline settings, and reporting settings.

AAC-DATA-DR-013
The system shall support a `Baseline` resource.

AAC-DATA-DR-014
The system shall support a `ReleaseGateResult` resource.

AAC-DATA-DR-015
The system shall support a `ProjectScope` resource documenting project boundaries, included and excluded system scope, and ASPICE process scope.

AAC-DATA-DR-016
The system shall support an `ASPICEScopeDecision` resource documenting in-scope, out-of-scope, and partially-in-scope ASPICE process decisions with rationale and evidence.

### 5.2 Safety Management And Planning Resources

AAC-DATA-DR-020
The system shall support a `SafetyPlan` resource or external reference.

AAC-DATA-DR-021
The system shall support a `SoftwareSafetyPlan` resource or external reference.

AAC-DATA-DR-022
The system shall support a `DevelopmentPlan` resource or external reference.

AAC-DATA-DR-023
The system shall support a `VerificationPlan` resource.

AAC-DATA-DR-024
The system shall support a `ValidationPlan` resource or external reference where product-level validation is managed outside the tool.

AAC-DATA-DR-025
The system shall support a `ConfigurationManagementPlan` resource or external reference.

AAC-DATA-DR-026
The system shall support a `ChangeManagementRecord` resource.

AAC-DATA-DR-027
The system shall support a `ConfirmationMeasureRecord` resource or external reference for reviews, audits, and assessments.

AAC-DATA-DR-028
The system shall support a `SafetyCase` resource for the structured safety argument and supporting evidence references.

AAC-DATA-DR-029
The system shall support a `QualityAssuranceRecord` resource for quality assurance activity evidence, findings, independence evidence, and closure references.

### 5.3 System-Level Reference Resources

AAC-DATA-DR-030
The system shall support an `ItemDefinition` resource or external reference.

AAC-DATA-DR-031
The system shall support a `HazardAnalysisRiskAssessment` resource or external reference.

AAC-DATA-DR-032
The system shall support a `SafetyGoal` resource or external reference.

AAC-DATA-DR-033
The system shall support a `FunctionalSafetyRequirement` resource or external reference.

AAC-DATA-DR-034
The system shall support a `TechnicalSafetyRequirement` resource or external reference.

AAC-DATA-DR-035
The system shall support a `SystemDesignElement` resource or external reference.

AAC-DATA-DR-036
The system shall support a `HardwareSoftwareInterface` resource or external reference where applicable.

AAC-DATA-DR-037
The system shall support a `SystemSafetyConcept` resource or external reference where system safety concept evidence is managed outside the software tool.

### 5.4 Software Requirements Resources

AAC-DATA-DR-040
The system shall support a `SoftwareSafetyRequirement` resource.

AAC-DATA-DR-041
The system shall support a `SoftwareRequirement` resource.

AAC-DATA-DR-042
The system shall support a `DerivedSoftwareRequirement` resource.

AAC-DATA-DR-043
The system shall support a `RequirementDecomposition` relationship resource.

AAC-DATA-DR-044
The system shall support an `Assumption` resource where assumptions are not embedded inside an assumption-guarantee contract.

AAC-DATA-DR-045
The system shall support a `RequirementReviewRecord` resource.

### 5.5 Software Architecture And Interface Resources

AAC-DATA-DR-050
The system shall support a `SoftwareComponent` resource.

AAC-DATA-DR-051
The system shall support a `SoftwareArchitecture` resource or architecture baseline grouping.

AAC-DATA-DR-052
The system shall support an `InterfaceContract` resource for SW-SW interfaces.

AAC-DATA-DR-053
The system shall support an `AssumptionGuaranteeContract` resource.

AAC-DATA-DR-054
The system shall support a `SafetyMechanism` or `Safeguard` resource.

AAC-DATA-DR-055
The system shall support a `SoftwarePartitioningElement` resource where freedom-from-interference, partitioning, or resource isolation needs to be argued.

AAC-DATA-DR-056
The system shall support a `ResourceUsageConstraint` resource for timing, memory, scheduling, communication, or execution constraints relevant to software safety.

AAC-DATA-DR-057
The system shall support an `ArchitectureReviewRecord` resource.

### 5.6 Software Design And Implementation Resources

AAC-DATA-DR-060
The system shall support a `SoftwareUnit` resource.

AAC-DATA-DR-061
The system shall support a `SoftwareUnitDesign` resource.

AAC-DATA-DR-062
The system shall support an `ImplementationItem` resource.

AAC-DATA-DR-063
The system shall support a `SourceCodeReference` resource.

AAC-DATA-DR-064
The system shall support a `BuildConfiguration` resource.

AAC-DATA-DR-065
The system shall support a `CompilerToolchainConfiguration` resource or external reference.

AAC-DATA-DR-066
The system shall support an `ImplementationReviewRecord` resource.

AAC-DATA-DR-067
The system shall support a `StaticAnalysisResult` resource or external reference.

AAC-DATA-DR-068
The system shall support a `CodingGuidelineComplianceRecord` resource or external reference.

AAC-DATA-DR-069
The system shall support a `DevelopmentEnvironmentRecord` resource or external reference for software development environment definition, toolchain configuration, and known limitations.

### 5.7 Software Verification Resources

AAC-DATA-DR-070
The system shall support a `TestSpecification` resource.

AAC-DATA-DR-071
The system shall support a `TestCase` resource.

AAC-DATA-DR-072
The system shall support a `TestProcedure` resource.

AAC-DATA-DR-073
The system shall support a `TestEnvironment` resource.

AAC-DATA-DR-074
The system shall support a `TestResult` resource.

AAC-DATA-DR-075
The system shall support a `CoverageResult` resource.

AAC-DATA-DR-076
The system shall support a `RequirementsCoverageRecord` resource.

AAC-DATA-DR-077
The system shall support an `InterfaceRobustnessTest` specialization or classification of test resources.

AAC-DATA-DR-078
The system shall support a `FaultInjectionTest` specialization or classification of test resources.

AAC-DATA-DR-079
The system shall support a `RegressionTestResult` resource or classification.

### 5.8 Analysis And Assurance Resources

AAC-DATA-DR-080
The system shall support a `SafetyAnalysis` resource.

AAC-DATA-DR-081
The system shall support software-level analysis records such as FMEA, FTA, DFA, freedom-from-interference, dependent failure, or equivalent project-specific analyses as configured resources.

AAC-DATA-DR-082
The system shall support an `InterfaceHazardAnalysis` or `InterfaceRiskAnalysis` resource for ASIL-relevant software interfaces.

AAC-DATA-DR-083
The system shall support a `FreedomFromInterferenceArgument` resource where mixed-criticality interaction or partitioning claims are made.

AAC-DATA-DR-084
The system shall support an `ASILDecompositionArgument` resource where ASIL decomposition is used.

AAC-DATA-DR-085
The system shall support an `AssuranceArgument` resource for lower-level structured assurance arguments. The project-level safety argument shall use the `SafetyCase` resource.

### 5.9 Tool, Process, And Qualification Resources

AAC-DATA-DR-090
The system shall support a `ToolInventoryItem` resource.

AAC-DATA-DR-091
The system shall support a `ToolConfidenceAssessment` resource or external reference.

AAC-DATA-DR-092
The system shall support a `ToolQualificationEvidence` resource or external reference where applicable.

AAC-DATA-DR-093
The system shall support a `ProcessComplianceRecord` resource or external reference.

### 5.10 Issue, Defect, And Change Resources

AAC-DATA-DR-100
The system shall support a `ValidationIssue` resource.

AAC-DATA-DR-101
The system shall support a `DefectRecord` resource or external reference.

AAC-DATA-DR-102
The system shall support a `ChangeRequest` resource or external reference.

AAC-DATA-DR-103
The system shall support a `ChangeSet` resource.

AAC-DATA-DR-104
The system shall support a `SuspectState` resource.

AAC-DATA-DR-105
The system shall support an `ImpactAnalysisResult` resource.

### 5.11 Evidence And Reporting Resources

AAC-DATA-DR-110
The system shall support an `EvidenceReference` resource.

AAC-DATA-DR-111
The system shall support an `EvidenceBundle` resource.

AAC-DATA-DR-112
The system shall support a `GeneratedReport` resource.

AAC-DATA-DR-113
The system shall support a `TraceabilityMatrix` generated resource.

AAC-DATA-DR-114
The system shall support an `InterfaceAssuranceReport` generated resource.

### 5.12 Audit And History Resources

AAC-DATA-DR-120
The system shall support an `AuditEvent` resource.

AAC-DATA-DR-121
The system shall support an `ImportRun` resource.

AAC-DATA-DR-122
The system shall support an `ArtefactRevision` resource.

AAC-DATA-DR-123
The system shall support a `RelationshipRevision` resource.

## 6. ASIL D Default Mandatory Profile

AAC-CORE-FR-020
The system shall provide an ASIL D default profile.

AAC-CORE-FR-021
The ASIL D default profile shall mark the following resource classes as mandatory unless explicitly justified as not applicable:

- Project
- ProjectScope
- ProjectConfiguration
- AssuranceProfile
- ASPICEScopeDecision
- SafetyCase
- SystemSafetyConcept or external reference
- SoftwareSafetyPlan
- VerificationPlan
- ConfigurationManagementPlan or external reference
- ChangeManagementRecord
- ConfirmationMeasureRecord or external reference
- DevelopmentEnvironmentRecord or external reference
- QualityAssuranceRecord
- ItemDefinition or external reference
- HazardAnalysisRiskAssessment or external reference
- SafetyGoal or external reference
- FunctionalSafetyRequirement or external reference
- TechnicalSafetyRequirement or external reference
- SoftwareSafetyRequirement
- SoftwareRequirement
- SoftwareComponent
- SoftwareArchitecture
- InterfaceContract
- AssumptionGuaranteeContract for ASIL-relevant interfaces
- Safeguard or SafetyMechanism
- SoftwareUnit
- SoftwareUnitDesign
- ImplementationItem
- SourceCodeReference
- BuildConfiguration
- CompilerToolchainConfiguration or external reference
- ImplementationReviewRecord
- StaticAnalysisResult or external reference
- CodingGuidelineComplianceRecord or external reference
- TestSpecification
- TestCase
- TestProcedure
- TestEnvironment
- TestResult
- CoverageResult
- RequirementsCoverageRecord
- SafetyAnalysis where required by project safety argument
- InterfaceRiskAnalysis for ASIL-relevant interfaces
- FreedomFromInterferenceArgument where mixed-criticality or partitioning claims are made
- ToolInventoryItem
- ToolConfidenceAssessment or justified not-applicable decision
- DefectRecord or external reference
- ChangeSet
- ImpactAnalysisResult
- EvidenceReference
- EvidenceBundle
- TraceabilityMatrix
- InterfaceAssuranceReport
- AuditEvent
- ImportRun
- ArtefactRevision
- RelationshipRevision
- Baseline
- ReleaseGateResult

AAC-CORE-FR-022
The ASIL D default profile shall require an explicit not-applicable decision for any mandatory resource class that is not present in a scoped baseline.

AAC-CORE-FR-023
The ASIL D default profile shall treat absence of required traceability between mandatory artefacts as a validation issue.

## 7. API Resource Model

AAC-API-IR-001
The back-end API shall expose resources using stable resource identifiers.

AAC-API-IR-002
The API shall support generic artefact operations for all canonical artefact classes:

- create artefact
- read artefact
- update artefact
- soft-delete artefact
- list artefacts
- search/filter artefacts
- retrieve artefact history
- retrieve artefact revision
- compare artefact revisions

AAC-API-IR-003
The API shall support relationship operations:

- create relationship
- read relationship
- update relationship
- soft-delete relationship
- list relationships
- retrieve relationship history
- retrieve relationship revision
- compare relationship revisions

AAC-API-IR-004
The API shall support Sphinx import operations:

- create import run
- submit authored object set
- validate import payload
- normalize authored objects
- persist imported changes
- retrieve import diagnostics
- retrieve import-created revisions

AAC-API-IR-005
The API shall support versioning operations:

- get current version
- get revision history
- compare revisions
- list revisions by import run
- list revisions by change set
- list revisions by baseline

AAC-API-IR-006
The API shall support baseline operations:

- request baseline creation
- evaluate baseline eligibility
- create baseline
- read baseline
- list baselines
- compare baselines
- retrieve baseline artefact revisions
- retrieve baseline relationship revisions
- retrieve baseline validation state
- retrieve baseline coverage state
- retrieve baseline release-gate result

AAC-API-IR-007
The API shall support traceability and graph operations:

- get forward trace
- get backward trace
- get full trace chain
- get traceability matrix
- get upstream artefacts
- get downstream artefacts
- get relationship path between artefacts

AAC-API-IR-008
The API shall support validation and rule operations:

- run validation
- retrieve validation issues
- retrieve rule catalog
- retrieve rule execution results
- resolve or suppress issue where permitted
- retrieve profile applicability gaps

AAC-API-IR-009
The API shall support impact operations:

- request impact analysis
- retrieve impacted artefacts
- retrieve impact paths
- retrieve suspect states
- clear suspect state where permitted
- retrieve retest recommendations

AAC-API-IR-010
The API shall support test and evidence operations:

- import test results
- retrieve test results
- link evidence references
- retrieve verification status
- retrieve evidence bundle

AAC-API-IR-011
The API shall support reporting operations:

- request report generation
- retrieve generated reports
- retrieve report status
- retrieve machine-readable report data

AAC-REPORT-IR-001
Version 1 report content shall be JSON and shall use this common envelope:

```json
{
  "report_id": "string",
  "report_type": "traceability_matrix|baseline_comparison|validation_summary",
  "project_id": "string",
  "generated_at": "ISO8601 timestamp",
  "generated_by": "user_id",
  "source_refs": {},
  "summary": {},
  "rows": []
}
```

AAC-REPORT-IR-002
A traceability matrix report row shall identify source and target artefact IDs,
types, revision IDs, relationship type, and trace status.

AAC-REPORT-IR-003
A baseline comparison report row shall identify the artefact or relationship,
its `added|removed|changed` classification, and both compared revision IDs where
applicable.

AAC-REPORT-IR-004
A validation summary report shall group open issues by severity and include
issue ID, rule ID, affected resource, blocking contexts, and status.

AAC-API-IR-012
The API shall support audit operations:

- retrieve audit events
- filter audit events by artefact, relationship, actor, event type, baseline, and time range

AAC-API-IR-013
The API shall support profile configuration operations:

- read assurance profile
- create project-specific profile
- update project-specific profile
- evaluate mandatory/optional applicability
- retrieve not-applicable decisions

## 8. API Derivation Principles

AAC-API-IR-020
API endpoints shall be derived from canonical resource needs, not from front-end screen layout.

AAC-API-IR-021
API commands that modify canonical state shall create audit events.

AAC-API-IR-022
API commands that modify artefacts or relationships shall trigger automatic versioning.

AAC-API-IR-023
API commands that modify artefacts or relationships shall trigger graph update and impacted validation checks.

AAC-API-IR-024
API commands that affect released or baselined artefacts shall trigger impact analysis and suspect propagation where applicable.

AAC-API-IR-025
API commands that create baselines shall use persisted canonical revisions, not mutable current artefact state.

AAC-API-IR-026
API query responses shall expose resource IDs, current revision IDs, lifecycle status, source references, and relevant validation state.

AAC-API-IR-027
Long-running operations shall be represented as jobs or command results that can be queried by the web app and CLI.

## 9. Versioning API Semantics

AAC-API-IR-030
Any create, update, delete, import, or relationship mutation accepted by the back-end shall create a new revision where canonical state changes.

AAC-API-IR-031
The API shall return the created revision IDs for successful state-changing commands.

AAC-API-IR-032
The API shall return an unchanged result when an imported authored object is identical to the current canonical revision.

AAC-API-IR-033
The API shall expose revision lineage for artefacts and relationships.

AAC-API-IR-034
The API shall support comparison between any two revisions of the same artefact or relationship.

AAC-API-IR-035
The API shall reject or flag updates based on stale client revision references according to the configured concurrency policy.

## 10. Baselining API Semantics

AAC-API-IR-040
Baseline creation shall be an explicit command submitted through the API.

AAC-API-IR-041
The back-end shall evaluate baseline eligibility before baseline creation.

AAC-API-IR-042
If baseline eligibility fails, the API shall return the blocking rule violations and no baseline snapshot shall be created.

AAC-API-IR-043
If baseline eligibility passes, the back-end shall create an immutable snapshot of selected artefact revisions and relationship revisions.

AAC-API-IR-044
The API shall return baseline ID, included revision references, validation summary, coverage summary, suspect summary, and release-gate status.

AAC-API-IR-045
Baseline comparison APIs shall identify added, removed, changed, unchanged, and suspect artefacts and relationships.

AAC-API-IR-046
Baseline APIs shall support filtering by project, component, interface, ASIL level, lifecycle status, and release status.

## 11. Repository Integration Resource Semantics

AAC-API-IR-050
The back-end shall support a `RepositoryConnector` resource that binds a project to a configured GitHub repository through a GitHub App installation or encrypted access-token connector.

AAC-API-IR-051
The back-end shall encrypt GitHub private key, GitHub access token, and webhook secret values at rest and shall not return secret values through API responses.

AAC-API-IR-052
The back-end shall support manual and webhook-triggered `RepositoryScanRun` jobs.

AAC-API-IR-053
Repository scans shall read `.aac/repo.yml` from the exact scanned commit and convert mappings into canonical `ImplementationItem`, `SourceCodeReference`, and `BuildConfiguration` artefacts.

AAC-API-IR-054
Repository scans shall create traceability relationships from implementation items to requirements and from source references to implementation items.

AAC-API-IR-055
Baseline creation shall snapshot active repository revisions alongside artefact and relationship revisions.

AAC-API-IR-056
When a project has an active repository connector, validation shall require repository-backed implementation and source-code references to include connector, commit, and path evidence.

AAC-API-IR-057
The back-end shall read repository status, current commit, GitHub checks, and GitHub commit statuses for a configured connector.

AAC-API-IR-058
The back-end shall publish baseline release approval to the exact commit SHA captured in the baseline repository snapshot after the latest release gate result has passed.

AAC-API-IR-059
Repository connector schemas, mapping-file schema, state machines, GitHub check semantics, conflict/versioning rules, and deployment acceptance criteria shall be controlled by [Repository Integration Contract](repository_integration_contract.md).

## 12. Gaps To Close Next

The following details are now covered by dedicated controlled documents:

- exact API endpoint paths and methods: `api_endpoint_specification.md`
- request and response schema configuration: `api_endpoint_specification.md`
- field-level artefact JSON schemas: `artefact_json_schemas.md`
- authentication and authorization model: `specification_refinement_decisions.md` and `api_endpoint_specification.md`
- import-run state machine: `import_and_versioning_state_machines.md`
- version conflict state machine: `import_and_versioning_state_machines.md`
- baseline state machine: `baseline_state_machine.md`
- logical database table design: `logical_database_schema.md`
- rule-to-resource applicability matrix: `rule_to_resource_applicability_matrix.md`
- ASIL profile configuration schema: `asil_profile_configuration_schema.md`
- Sphinx-Needs type and field mappings: `sphinx_needs_mapping_specification.md`
- repository integration: `repository_integration_requirements.md`

The async job payload and worker execution schema is covered by `async_job_schema.md`.
