# Standards Traceability Matrix

## 1. Purpose

This document defines the standards traceability model for Assurance-as-Code.

It maps tool resources, rules, review expectations, confirmation measures, test artefacts, and profile obligations to the standards basis used by the project:

- ISO 26262
- Automotive SPICE Level 3
- ISO/IEC/IEEE 29119
- UNECE R155
- UNECE R156

## 2. Source Control Rule

AAC-STD-FR-001
Each standards-derived requirement, rule, artefact, or profile obligation shall identify its standards basis.

AAC-STD-FR-002
Each standards mapping entry shall include a review status.

AAC-STD-FR-003
Allowed review status values are:

- `draft_public_reference`
- `reviewed_against_controlled_standard`
- `project_tailored`
- `obsolete`

AAC-STD-FR-004
Mappings based only on public summaries shall be marked `draft_public_reference`.

AAC-STD-FR-005
Mappings shall be marked `reviewed_against_controlled_standard` only after review against the official applicable standard text used by the project.

## 3. Standards Reference Schema

AAC-STD-DR-001
A standards reference shall use this schema:

```yaml
standard_reference:
  id: string
  standard: enum[ISO26262, ASPICE, ISO29119, UNECE_R155, UNECE_R156]
  edition: string
  part_or_process: string
  clause_or_process_id: string
  title: string
  reference_type: enum[clause, process, base_practice, process_attribute, work_product, regulation_paragraph]
  source_access: enum[public, controlled_standard, project_process]
  review_status: enum[draft_public_reference, reviewed_against_controlled_standard, project_tailored, obsolete]
```

## 4. ISO 26262 Reference Anchors

The following anchors shall be used for software-system functional safety mapping.

| Reference ID | Standard Anchor | Tool Usage |
|---|---|---|
| STD-ISO26262-2 | ISO 26262-2:2018, functional safety management | Safety planning, roles, confirmation measures, safety case references |
| STD-ISO26262-4 | ISO 26262-4:2018, product development at system level | Item, HARA references, safety goals, functional/technical safety requirements, system architecture references |
| STD-ISO26262-6-5 | ISO 26262-6:2018, Clause 5, software-level general topics | Software development environment, methods, planning constraints |
| STD-ISO26262-6-6 | ISO 26262-6:2018, Clause 6, software safety requirements | SoftwareSafetyRequirement, HSI refinement, verification |
| STD-ISO26262-6-7 | ISO 26262-6:2018, Clause 7, software architectural design | SoftwareArchitecture, SoftwareComponent, InterfaceContract, SafetyMechanism |
| STD-ISO26262-6-8 | ISO 26262-6:2018, Clause 8, software unit design and implementation | SoftwareUnitDesign, ImplementationItem, SourceCodeReference |
| STD-ISO26262-6-9 | ISO 26262-6:2018, Clause 9, software unit verification | Unit verification specification/result |
| STD-ISO26262-6-10 | ISO 26262-6:2018, Clause 10, software integration and verification | Integration verification, interface verification |
| STD-ISO26262-6-11 | ISO 26262-6:2018, Clause 11, testing of embedded software | Embedded software test specification/result |
| STD-ISO26262-8-6 | ISO 26262-8:2018, safety requirements management | Requirement attributes, traceability, change impact |
| STD-ISO26262-8-7 | ISO 26262-8:2018, configuration management | Baselines, configuration item control |
| STD-ISO26262-8-8 | ISO 26262-8:2018, change management | ChangeRequest, ImpactAnalysisResult |
| STD-ISO26262-8-9 | ISO 26262-8:2018, verification | Verification planning, review, analysis, test evidence |
| STD-ISO26262-8-10 | ISO 26262-8:2018, documentation management | EvidenceReference, EvidenceBundle, generated reports |
| STD-ISO26262-8-11 | ISO 26262-8:2018, software tool confidence | ToolInventoryItem, ToolConfidenceAssessment, ToolQualificationEvidence |

## 5. ISO 26262 Work Product Mapping

| Tool Resource | ISO 26262 Anchor | Required Tool Content | Review / Independence Expectation |
|---|---|---|---|
| SafetyCase | STD-ISO26262-2 | safety claim, argument structure, supported artefact references, open assumptions/issues, confidence argument, evidence references | independent review required for ASIL D |
| SafetyPlan | STD-ISO26262-2 | safety activities, roles, confirmation measures, work products, schedule, responsibilities | review required; independence per configured ASIL profile |
| SoftwareSafetyPlan | STD-ISO26262-2, STD-ISO26262-6-5 | software safety activities, software lifecycle, verification activities, tools, integration points | review required; independence per ASIL profile |
| DevelopmentEnvironmentRecord | STD-ISO26262-6-5 | development environment, toolchain references, configuration references, known limitations, qualification/confidence references | review required where used as safety evidence |
| SystemSafetyConcept | STD-ISO26262-4 | system safety requirements, safety mechanisms, external interface assumptions, software allocation references | external reference allowed; review status tracked |
| ItemDefinition | STD-ISO26262-4 | item scope, boundaries, dependencies, operating context, external interfaces | referenced or imported; review status tracked |
| HazardAnalysisRiskAssessment | STD-ISO26262-4 | hazardous events, operational situations, ASIL classification, safety goals source | external reference allowed |
| SafetyGoal | STD-ISO26262-4 | safety goal statement, ASIL, source hazard, safe state or safety objective | trace to requirements |
| FunctionalSafetyRequirement | STD-ISO26262-4 | requirement text, ASIL, allocated element, source safety goal | trace to technical/software safety requirements |
| TechnicalSafetyRequirement | STD-ISO26262-4 | requirement text, ASIL, allocation, technical safety concept reference | trace to software safety requirements |
| SoftwareSafetyRequirement | STD-ISO26262-6-6 | requirement text, ASIL, source TSR/HSI, rationale, acceptance criteria, verification intent | review and verification required |
| HardwareSoftwareInterface | STD-ISO26262-6-6 | interface data, timing, range, error handling, operating constraints | required when HSI applies |
| SoftwareArchitecture | STD-ISO26262-6-7 | components, interfaces, dependencies, safety mechanisms, allocation | review and safety analysis required |
| InterfaceContract | STD-ISO26262-6-7, STD-ISO26262-6-10 | source/destination, payload, timing, validity, failure behavior, classification | review required for ASIL-relevant interfaces |
| AssumptionGuaranteeContract | STD-ISO26262-6-7 | ASIL assumptions, guarantees, linked safeguards/tests | required for ASIL-relevant cross-criticality interaction |
| Safeguard | STD-ISO26262-6-7 | mechanism type, protected fault, expected response, allocation, implementation/test links | implementation and verification required |
| SoftwareUnitDesign | STD-ISO26262-6-8 | unit responsibilities, interfaces, design constraints, safety behavior | review required |
| ImplementationItem | STD-ISO26262-6-8 | source/config/script reference, implemented requirements/safeguards/interfaces | review and traceability required |
| UnitVerificationSpecification | STD-ISO26262-6-9 | unit test/analysis/inspection objective, method, pass criteria | method by ASIL profile |
| UnitVerificationResult | STD-ISO26262-6-9 | execution result, verdict, evidence, defects | required for released units |
| IntegrationVerificationSpecification | STD-ISO26262-6-10 | integration objective, interface checks, fault/misuse cases | required for ASIL-relevant interfaces |
| EmbeddedSoftwareTestSpecification | STD-ISO26262-6-11 | test objective, test cases, environment, pass criteria, coverage | required for embedded software testing |
| SoftwareVerificationReport | STD-ISO26262-6-6/7/8/9/10/11 | verification summary, deviations, coverage, verdicts | release-gate input |
| ConfigurationManagementRecord | STD-ISO26262-8-7 | configuration item IDs, versions, baseline membership | baseline required |
| ChangeManagementRecord | STD-ISO26262-8-8 | change request, impact, approval, implementation, verification impact | required for changed released artefacts |
| ToolConfidenceAssessment | STD-ISO26262-8-11 | tool use case, possible errors, confidence rationale, qualification need | conditional |
| ToolQualificationEvidence | STD-ISO26262-8-11 | qualification evidence or external reference | conditional |

## 6. Automotive SPICE Level 3 Reference Anchors

Automotive SPICE 4.0 is the default ASPICE basis. The VDA QMC public PDF identifies the process groups and Level 3 process attributes.

| Reference ID | ASPICE 4.0 Anchor | Tool Usage |
|---|---|---|
| STD-ASPICE-SPL.2 | SPL.2 Product Release | Release package, release approval, release evidence |
| STD-ASPICE-SYS.1 | SYS.1 Requirements Elicitation | Stakeholder/system input references |
| STD-ASPICE-SYS.2 | SYS.2 System Requirements Analysis | System requirements and bidirectional traceability |
| STD-ASPICE-SYS.3 | SYS.3 System Architectural Design | System architecture references |
| STD-ASPICE-SYS.4 | SYS.4 System Integration and Integration Verification | System integration evidence |
| STD-ASPICE-SYS.5 | SYS.5 System Verification | System verification evidence |
| STD-ASPICE-SWE.1 | SWE.1 Software Requirements Analysis | Software requirements, attributes, consistency, traceability |
| STD-ASPICE-SWE.2 | SWE.2 Software Architectural Design | Software architecture, components, interfaces |
| STD-ASPICE-SWE.3 | SWE.3 Software Detailed Design and Unit Construction | Unit design and construction |
| STD-ASPICE-SWE.4 | SWE.4 Software Unit Verification | Unit verification |
| STD-ASPICE-SWE.5 | SWE.5 Software Component Verification and Integration Verification | Integration/component verification |
| STD-ASPICE-SWE.6 | SWE.6 Software Verification | Software verification |
| STD-ASPICE-VAL.1 | VAL.1 Validation | Validation evidence |
| STD-ASPICE-SUP.1 | SUP.1 Quality Assurance | QA evidence and independence |
| STD-ASPICE-SUP.8 | SUP.8 Configuration Management | Configuration items and baselines |
| STD-ASPICE-SUP.9 | SUP.9 Problem Resolution Management | Defect/problem records |
| STD-ASPICE-SUP.10 | SUP.10 Change Request Management | Change requests and impact |
| STD-ASPICE-MAN.3 | MAN.3 Project Management | Project planning/status/risk links |
| STD-ASPICE-PA3.1 | PA 3.1 Process Definition | defined process evidence |
| STD-ASPICE-PA3.2 | PA 3.2 Process Deployment | process deployment evidence |

## 7. Automotive SPICE Resource Mapping

| Tool Resource | ASPICE Anchor | Required Tool Content |
|---|---|---|
| ProjectScope | STD-ASPICE-MAN.3, STD-ASPICE-PA3.1 | project scope, included/excluded system boundaries, included/excluded ASPICE process scope, rationale and evidence |
| ASPICEScopeDecision | STD-ASPICE-PA3.1, STD-ASPICE-PA3.2 | process scope decision, scope status, rationale, affected work products, approval evidence |
| SoftwareRequirement | STD-ASPICE-SWE.1 | requirement statement, attributes, source, analysis status, communication/review status |
| SoftwareArchitecture | STD-ASPICE-SWE.2 | architecture elements, interfaces, dynamic behavior where applicable, trace to requirements |
| SoftwareUnitDesign | STD-ASPICE-SWE.3 | unit design, interfaces, trace to architecture/requirements |
| ImplementationItem | STD-ASPICE-SWE.3 | constructed software unit/source reference |
| UnitVerificationSpecification/Result | STD-ASPICE-SWE.4 | verification criteria, method, result |
| IntegrationVerificationSpecification/Result | STD-ASPICE-SWE.5 | component/integration verification criteria and result |
| SoftwareVerificationReport | STD-ASPICE-SWE.6 | software verification coverage and results |
| DefectRecord | STD-ASPICE-SUP.9 | problem identity, analysis, status, resolution evidence |
| ChangeRequest | STD-ASPICE-SUP.10 | change identity, analysis, affected work products, implementation confirmation |
| Baseline | STD-ASPICE-SUP.8 | configured item snapshot and status |
| ReleaseGateResult | STD-ASPICE-SPL.2 | release criteria, approval, release package references |
| QualityAssuranceRecord | STD-ASPICE-SUP.1 | QA activity, scope, findings, independence evidence, closure references |
| ProcessComplianceRecord | STD-ASPICE-PA3.1, STD-ASPICE-PA3.2 | defined process and deployment evidence |

## 8. ISO/IEC/IEEE 29119 Test Artefact Mapping

| Tool Resource | ISO 29119 Anchor | Required Tool Content |
|---|---|---|
| TestPlan | ISO/IEC/IEEE 29119-2 and 29119-3 | scope, objectives, strategy, resources, schedule, risks, entry/exit criteria |
| TestSpecification | ISO/IEC/IEEE 29119-3 | test basis, test design objective, test conditions, coverage target |
| TestCase | ISO/IEC/IEEE 29119-3 | input, preconditions, expected result, pass/fail criteria, trace to test basis |
| TestProcedure | ISO/IEC/IEEE 29119-3 | execution sequence, environment, data, setup/cleanup |
| TestEnvironment | ISO/IEC/IEEE 29119-3 | hardware/software/tool configuration, version, constraints |
| TestResult | ISO/IEC/IEEE 29119-3 | execution timestamp, verdict, evidence, deviations, defects |
| TestCompletionReport | ISO/IEC/IEEE 29119-3 | summary, coverage, unresolved issues, recommendation |
| CoverageResult | ISO/IEC/IEEE 29119-2/3 | coverage target, achieved coverage, gaps |

## 9. UNECE R155/R156 Evidence Mapping

| Tool Resource | Regulation Anchor | Required Tool Content |
|---|---|---|
| CybersecurityManagementEvidence | UNECE R155 | CSMS reference, cybersecurity risk evidence, treatment status, interface relevance |
| CybersecurityInterfaceEvidence | UNECE R155 | security-relevant interface, threat/risk reference, mitigation/evidence |
| SoftwareUpdateManagementEvidence | UNECE R156 | SUMS reference, update package, version identification, approval, integrity evidence |
| ReleaseGateResult | UNECE R156 | release/update approval, version, affected software items |
| AuditEvent | UNECE R155/R156 | traceability of changes, approvals, releases, and updates |

## 10. Mandatory Versus Optional By ASIL

AAC-STD-FR-010
The platform shall not hard-code all ASIL tailoring decisions in source code.

AAC-STD-FR-011
Mandatory versus optional status shall be profile-driven and reviewable.

AAC-STD-FR-012
The default ASIL D profile shall be the strictest supplied profile.

AAC-STD-FR-013
Lower ASIL profiles shall inherit from ASIL D and relax obligations only through explicit profile configuration.

AAC-STD-FR-014
Any project-specific tailoring that makes an ASIL D mandatory artefact optional shall require evidence and Project Lead approval.

## 11. Tailoring Justification Model

Tailoring may be justified only by one of:

- not applicable to project scope
- externally controlled artefact with reference
- equivalent evidence exists in another controlled artefact
- lower ASIL profile permits optionality
- project process defines an approved alternative
- regulatory scope not applicable

Tailoring shall not be accepted without:

- rationale
- evidence reference
- scope
- approver
- timestamp
- audit event

AAC-STD-FR-020
Equivalent evidence acceptance shall be a human approval decision.

AAC-STD-FR-021
Equivalent evidence shall be acceptable when the Project Lead approves the tailoring decision and at least one evidence reference is attached.

AAC-STD-FR-022
The tool shall not attempt to automatically judge semantic equivalence of evidence for tailoring approval in MVP.
