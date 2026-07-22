# Canonical Artefact Name Reconciliation

## 1. Purpose

This document resolves blocker B10 identified in the implementation readiness assessment: inconsistent terminology between the standards traceability matrix and the artefact JSON schemas.

It defines the single canonical implementation name for every artefact type and maps alternative names used in standards references, Sphinx-Needs types, or exploratory documents to the canonical name.

All implementation code, database tables, API endpoints, and schema definitions shall use the canonical names defined in this document.
Field definitions and requiredness are controlled exclusively by
`artefact_json_schemas.md`.

---

## 2. Governing Rules

DEC-NAME-001
The canonical artefact type name shall be used in:
- SQLAlchemy ORM model class names
- Pydantic schema class names
- API endpoint path segments
- `artefact_type` field values in the database
- Sphinx-Needs mapping keys
- Rule catalog `applies_to_resources` entries

DEC-NAME-002
Standards matrix names that differ from the canonical name are documentation-level aliases only and shall not appear in implementation code.

DEC-NAME-003
When a standards matrix entry uses a compound name (e.g., `UnitVerificationSpecification`) that maps to a parameterized canonical type (e.g., `TestSpecification` with `scope=unit`), the canonical name plus parameter is authoritative.

---

## 3. Canonical Name Registry

### 3.1 Configuration And Project Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `Project` | — | Top-level project container |
| `ProjectConfiguration` | — | Project-level settings and profile assignment |
| `AssuranceProfile` | — | ASIL/QM profile definition |
| `TailoringDecision` | — | Profile tailoring record |
| `ProjectScope` | — | **New** (B10 gap): documents ASPICE scope boundaries, system-process exclusions |

### 3.2 Safety Planning Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `SafetyPlan` | — | ISO 26262-2 safety plan |
| `SoftwareSafetyPlan` | — | ISO 26262-2 / 6-5 software safety plan |
| `DevelopmentPlan` | — | General development planning |
| `VerificationPlan` | — | Verification planning |
| `ValidationPlan` | — | Validation planning |
| `ConfigurationManagementPlan` | `ConfigurationManagementRecord` (in standards matrix) | ISO 26262-8-7; standards matrix uses both names; canonical name is `ConfigurationManagementPlan` |
| `ChangeManagementRecord` | — | ISO 26262-8-8 change record |
| `ConfirmationMeasureRecord` | — | ISO 26262-2 confirmation measure evidence |

### 3.3 System-Level Reference Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `ItemDefinition` | — | ISO 26262-4 item definition (external reference) |
| `HazardAnalysisRiskAssessment` | `HARA` | ISO 26262-4 (external reference allowed) |
| `SafetyGoal` | — | ISO 26262-4 safety goal |
| `FunctionalSafetyRequirement` | `FSR` | ISO 26262-4 |
| `TechnicalSafetyRequirement` | `TSR` | ISO 26262-4 |
| `SystemDesignElement` | — | System-level design reference |
| `HardwareSoftwareInterface` | `HSI` | ISO 26262-6-6; conditional under ASIL D |
| `SafetyCase` | — | **New** (ISO 26262-2 gap): formal safety argument; mandatory ASIL D |
| `SystemSafetyConcept` | — | **New** (ISO 26262-4 gap): system safety concept document; external reference |

### 3.4 Software Requirements Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `SoftwareSafetyRequirement` | `SSR` | ISO 26262-6-6; ASIL D mandatory |
| `SoftwareRequirement` | `SR` | General software requirement (ASPICE SWE.1) |
| `DerivedSoftwareRequirement` | — | Derived during architecture/design |
| `RequirementDecomposition` | — | Decomposition relationship record |
| `Assumption` | — | Architectural assumption |
| `RequirementReviewRecord` | — | Review evidence for requirements |

### 3.5 Architecture And Interface Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `SoftwareArchitecture` | — | ISO 26262-6-7; ASIL D mandatory |
| `SoftwareComponent` | — | ISO 26262-6-7; ASIL D mandatory |
| `InterfaceContract` | — | ISO 26262-6-7; contract for component interactions |
| `AssumptionGuaranteeContract` | `AG Contract` | ISO 26262-6-7; ASIL-relevant cross-criticality |
| `Safeguard` | `SafetyMechanism` | ISO 26262-6-7; canonical name is `Safeguard`; `SafetyMechanism` is an alias |
| `SoftwarePartitioningElement` | — | Partitioning evidence |
| `ResourceUsageConstraint` | — | CPU/memory/timing constraints |
| `ArchitectureReviewRecord` | — | Review evidence for architecture |
| `FreedomFromInterferenceArgument` | `FFIArgument` | ISO 26262-6-7 |
| `ASILDecompositionArgument` | — | ISO 26262-9 ASIL decomposition evidence |

### 3.6 Implementation Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `SoftwareUnit` | — | ISO 26262-6-8; implementable unit |
| `SoftwareUnitDesign` | — | ISO 26262-6-8 / ASPICE SWE.3 unit design |
| `ImplementationItem` | `ConstructedSoftwareUnit` (in standards matrix) | ASPICE SWE.3; canonical name is `ImplementationItem` |
| `SourceCodeReference` | — | Reference to source code artifact |
| `BuildConfiguration` | — | ISO 26262-8-7; build configuration record |
| `CompilerToolchainConfiguration` | — | Toolchain configuration |
| `ImplementationReviewRecord` | — | Review evidence for implementation |
| `DevelopmentEnvironmentRecord` | — | **New** (ISO 26262-6-5 gap): SW development environment specification |

### 3.7 Analysis And Quality Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `StaticAnalysisResult` | — | Static analysis evidence |
| `CodingGuidelineComplianceRecord` | — | Coding guideline conformance evidence |
| `SafetyAnalysis` | — | FMEA/FTA/etc. safety analysis |
| `InterfaceRiskAnalysis` | — | Interface-specific risk analysis |
| `AssuranceArgument` | `SafetyCase` (exploratory only) | Structured assurance argument; `SafetyCase` is now a separate artefact |
| `ProcessComplianceRecord` | — | ASPICE PA3.1/PA3.2 process evidence |
| `QualityAssuranceRecord` | — | **New** (ASPICE SUP.1 gap): QA activity planning and independence evidence |

### 3.8 Verification And Testing Resources

The standards traceability matrix uses ISO 29119 names that differ from the canonical implementation names. The following reconciliation applies:

| Canonical Name | Standards Matrix Alias | Scope Parameter | Notes |
|---|---|---|---|
| `TestPlan` | `TestPlan` | — | ISO 29119-2; top-level test planning artefact |
| `TestSpecification` | `UnitVerificationSpecification` | `scope=unit` | ISO 29119-3 / ISO 26262-6-9; scoped to unit level |
| `TestSpecification` | `IntegrationVerificationSpecification` | `scope=integration` | ISO 29119-3 / ISO 26262-6-10; scoped to integration |
| `TestSpecification` | `EmbeddedSoftwareTestSpecification` | `scope=embedded` | ISO 29119-3 / ISO 26262-6-11; scoped to embedded |
| `TestSpecification` | `SoftwareVerificationReport` (test spec part) | `scope=software` | ISO 26262-6-6 through 6-11 verification spec |
| `TestCase` | `TestCase` | — | ISO 29119-3 |
| `TestProcedure` | `TestProcedure` | — | ISO 29119-3 |
| `TestEnvironment` | `TestEnvironment` | — | ISO 29119-3 |
| `TestResult` | `UnitVerificationResult` | `scope=unit` | ISO 29119-3 / ISO 26262-6-9 |
| `TestResult` | `IntegrationVerificationResult` | `scope=integration` | ISO 26262-6-10 |
| `TestResult` | `EmbeddedSoftwareTestResult` | `scope=embedded` | ISO 26262-6-11 |
| `CoverageResult` | `CoverageResult` | — | ISO 29119-2/3 |
| `RequirementsCoverageRecord` | — | — | Requirements coverage tracking |
| `GeneratedReport` | `TestCompletionReport` | `report_type=test_completion` | ISO 29119-3; implemented as a generated report |
| `GeneratedReport` | `SoftwareVerificationReport` (final report) | `report_type=verification_summary` | ISO 26262-6 final verification report |

**Rule for scoped TestSpecification / TestResult:**
The `scope` field on `TestSpecification` and `TestResult` identifies which lifecycle level the test applies to. Rules and validation shall use the `scope` field to enforce ISO 26262 clause-specific requirements. The canonical type is `TestSpecification` regardless of scope.

### 3.9 Tools And Process Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `ToolInventoryItem` | — | ISO 26262-8-11 tool inventory |
| `ToolConfidenceAssessment` | — | ISO 26262-8-11 TCL assessment |
| `ToolQualificationEvidence` | — | ISO 26262-8-11 qualification evidence |

### 3.10 Issue And Change Management Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `ValidationIssue` | — | Internal validation finding |
| `DefectRecord` | `ProblemRecord` (ASPICE SUP.9) | ASPICE SUP.9 / ISO 29119 |
| `ChangeRequest` | — | ASPICE SUP.10 change request |
| `ChangeSet` | — | Grouped set of changes |
| `SuspectState` | — | Suspect propagation state record |
| `ImpactAnalysisResult` | — | ISO 26262-8-8 / ASPICE SUP.10 impact analysis |

### 3.11 Evidence And Reporting Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `EvidenceReference` | — | External evidence pointer |
| `EvidenceBundle` | — | Grouped evidence collection |
| `GeneratedReport` | See §3.8 for testing sub-types | Includes traceability matrices, interface assurance reports |
| `ThreatAnalysisRiskAssessment` | `TARA` | UNECE R155 cybersecurity risk assessment |
| `CybersecurityRequirement` | — | Requirement derived from TARA/cybersecurity goal |
| `CybersecurityManagementEvidence` | — | UNECE R155 |
| `CybersecurityInterfaceEvidence` | — | UNECE R155 |
| `SoftwareUpdateManagementEvidence` | — | UNECE R156 |
| `SoftwareVersionRecord` | — | Software version identification for update/release control |
| `UpdateCampaign` | — | Software update campaign authorization and rollout evidence |
| `UpdateIntegrityEvidence` | — | Update package integrity/signature verification evidence |
| `SoftwareBillOfMaterials` | `SBOM` | Software composition evidence for update and vulnerability tracking |
| `TestRiskAssessment` | — | ISO 29119 test risk evidence |

### 3.12 Infrastructure Resources

| Canonical Name | Aliases / Standards Matrix Name | Notes |
|---|---|---|
| `Baseline` | — | ISO 26262-8-7 / ASPICE SUP.8 baseline snapshot |
| `ReleaseGateResult` | — | Release gate evaluation record |
| `AuditEvent` | — | Append-only audit trail entry |
| `ImportRun` | — | Sphinx import execution record |
| `ArtefactRevision` | — | Immutable revision record for an artefact |
| `RelationshipRevision` | — | Immutable revision record for a relationship |
| `ImportRunItem` | — | Per-artefact result within an import run |
| `ValidationRun` | — | Validation execution record |
| `ValidationRule` | — | Rule definition record (catalog entry) |
| `Job` | `AsyncJob` | Canonical name is `Job` |
| `ASPICEScopeDecision` | — | **New** (ASPICE gap): records which ASPICE processes are in/out of scope |

---

## 4. Canonical Relationship Types

| Canonical Relationship Type | Description | Standards Basis |
|---|---|---|
| `allocates_to` | Requirement allocated to component | ISO 26262, ASPICE |
| `satisfies` | Artefact satisfies requirement | ISO 26262, ASPICE |
| `depends_on` | Component depends on component | ISO 26262-6-7 |
| `interacts_via` | Component interacts via interface contract | ISO 26262-6-7 |
| `constrains` | Resource constraint applied to component | ISO 26262-6-7 |
| `assumes` | Component assumes condition | ISO 26262-6-7 |
| `guarantees` | Component guarantees condition | ISO 26262-6-7 |
| `protects` | Safeguard protects against fault | ISO 26262-6-7 |
| `implements` | Implementation item implements requirement/design | ISO 26262-6-8, ASPICE SWE.3 |
| `verifies` | Test case/result verifies requirement/artefact | ISO 26262, ISO 29119 |
| `produces_result_for` | Test result produced for test case | ISO 29119 |
| `derives_from` | Derived requirement derives from parent | ISO 26262-8-6 |
| `references` | General evidence/external reference | ISO 26262-8-10 |
| `mitigates` | Safety mechanism mitigates hazard/fault | ISO 26262-6-7 |
| `traces_to` | General bidirectional traceability | ASPICE SWE.1/SWE.2 |

---

## 5. New Artefact Name Decisions

The following artefact types are introduced by this document to close gaps
identified in the standards alignment assessment. The YAML blocks in this
section are rationale and migration guidance, not normative field schemas.
Normative fields, types, and requiredness shall be defined only in
`artefact_json_schemas.md`.

### 5.1 SafetyCase

```yaml
artefact_type: SafetyCase
basis: ISO 26262-2
asil_d_applicability: mandatory
description: >
  Structured argument, supported by evidence, that the item achieves its safety goals.
  Contains safety goal references, argument structure, evidence summary, and confidence assessment.
required_fields:
  - safety_goal_refs          # list of SafetyGoal artefact IDs
  - argument_structure        # structured text or GSN reference
  - evidence_summary          # summary of supporting evidence
  - confidence_assessment     # confidence in argument completeness
  - review_status             # review lifecycle state
  - independent_reviewer_id   # required for ASIL D
  - approver_id
  - approval_timestamp
```

### 5.2 SystemSafetyConcept

```yaml
artefact_type: SystemSafetyConcept
basis: ISO 26262-4
asil_d_applicability: external_reference  # authored externally; tracked by reference
description: >
  System-level document defining how safety goals are achieved at the system level,
  including technical safety requirements and system architecture safety measures.
  May be an external reference when the platform covers SW-only scope.
required_fields:
  - external_reference_id     # reference to external document
  - document_location         # location/URL of external document
  - review_status
  - controlled_document_id    # document ID in external CM system
```

### 5.3 DevelopmentEnvironmentRecord

```yaml
artefact_type: DevelopmentEnvironmentRecord
basis: ISO 26262-6-5
asil_d_applicability: conditional  # condition: project.has_sw_development == true
description: >
  Specifies the software development environment: tools, languages, compilers,
  configuration management tools, test environments, and associated tool confidence levels.
required_fields:
  - development_language       # programming language(s)
  - compiler_toolchain_refs    # list of CompilerToolchainConfiguration artefact IDs
  - tool_inventory_refs        # list of ToolInventoryItem artefact IDs
  - configuration_tool_ref     # CM tool reference
  - review_status
```

### 5.4 QualityAssuranceRecord

```yaml
artefact_type: QualityAssuranceRecord
basis: ASPICE SUP.1
asil_d_applicability: mandatory
description: >
  Documents QA activities, QA plan, independence of QA function, and QA findings.
  Required for Automotive SPICE PAM 4.0 CL3 SUP.1 process capability evidence.
required_fields:
  - qa_plan_reference          # reference to QA plan document
  - qa_activity_summary        # list of QA activities performed
  - independence_evidence      # evidence of QA function independence
  - findings_summary           # summary of QA findings
  - review_status
  - qa_responsible_id          # user with Quality Engineer role
```

### 5.5 ProjectScope

```yaml
artefact_type: ProjectScope
basis: Automotive SPICE PAM 4.0 CL3 (scoping)
asil_d_applicability: mandatory
description: >
  Documents the scope of the assurance assessment: which ASPICE processes are in-scope,
  whether system-level processes are covered externally, and the ISO 26262 item boundary.
required_fields:
  - aspice_in_scope_processes  # list of ASPICE process IDs included
  - aspice_out_of_scope_processes  # list with rationale for each excluded process
  - iso26262_item_boundary     # description of item boundary per ISO 26262-4
  - system_level_coverage      # how/where system-level processes are covered
  - rationale
  - review_status
  - approver_id
```

### 5.6 ASPICEScopeDecision

```yaml
artefact_type: ASPICEScopeDecision
basis: Automotive SPICE PAM 4.0 CL3 PA3.1/PA3.2
asil_d_applicability: mandatory
description: >
  Records the decision to include or exclude a specific ASPICE process from the project scope,
  with rationale and evidence for any exclusion.
required_fields:
  - aspice_process_id          # e.g., SYS.1, SWE.1
  - decision                   # in_scope | out_of_scope_with_rationale | externally_covered
  - rationale
  - evidence_refs
  - approver_id
  - decision_timestamp
```

---

## 6. Independent Review Schema Decision

Per the ISO 26262 standards alignment gap, the following artefact types require
independent review semantics for ASIL D compliance. The canonical field
definitions and conditional requiredness are those in
`artefact_json_schemas.md`; this section records applicability only.

| Artefact Type | Independence Requirement | ISO 26262 Clause |
|---|---|---|
| `SoftwareSafetyRequirement` | Independent review mandatory at ASIL D | 26262-6-6 |
| `SoftwareArchitecture` | Independent review mandatory at ASIL D | 26262-6-7 |
| `SafetyAnalysis` | Independent review mandatory at ASIL D | 26262-6-7 |
| `SafetyCase` | Independent review mandatory at ASIL D | 26262-2 |
| `TestSpecification` (scope=unit, scope=integration) | Independent review at ASIL D | 26262-6-9, 6-10 |
| `SoftwareUnitDesign` | Review per ASIL D | 26262-6-8 |
| `ConfirmationMeasureRecord` | By definition requires independence evidence | 26262-2 |

The canonical schema currently uses the following fields to realize this
applicability. This example is non-normative; the definitions in
`artefact_json_schemas.md` prevail:

```yaml
# Added to all artefact types listed above:
independent_reviewer_id:
  type: string (user ID)
  required_when: profile.asil_level in [ASIL_C, ASIL_D] and artefact.review_status == reviewed
  description: User ID of the independent reviewer; must differ from primary author

review_independence_evidence:
  type: string
  required_when: independent_reviewer_id is set
  description: Reference or description of how independence was established
```
