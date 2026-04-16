# Rule-To-Resource Applicability Matrix

## 1. Purpose

This document defines how validation, consistency, traceability, testing, baseline, release, ASPICE, ISO 29119, UNECE R155, and UNECE R156 oriented rules apply to platform resources.

The matrix is project-configuration-driven. ASIL D and Automotive SPICE PAM 4.0 CL3 defaults are strict. Lower ASIL, QM, or lower ASPICE capability targets may tailor severity, blocking behavior, visibility, and applicability.

## 2. Rule Schema

Each rule shall be defined using:

```yaml
rule:
  id: string
  title: string
  source_basis: [ISO26262, ASPICE_PAM_4_0, ISO29119, UNECE_R155, UNECE_R156, TOOL]
  objective: string
  applies_to_resources: [string]
  applies_to_relationships: [string]
  profiles: [QM, ASIL_A, ASIL_B, ASIL_C, ASIL_D]
  execution_modes: [import, immediate, baseline, release_gate, manual]
  severity_by_profile:
    QM: enum[critical, major, minor, info, disabled]
    ASIL_A: enum[critical, major, minor, info, disabled]
    ASIL_B: enum[critical, major, minor, info, disabled]
    ASIL_C: enum[critical, major, minor, info, disabled]
    ASIL_D: enum[critical, major, minor, info, disabled]
  pass_condition: string
  fail_condition: string
  produced_issue_type: string
  remediation_hint: string
```

## 3. Core Rule Matrix

| Rule ID | Title | Basis | Applies To | ASIL D Default | Execution |
|---|---|---|---|---|---|
| AAC-RULE-RULE-001 | Referenced artefact exists | TOOL, ASPICE_PAM_4_0 | Relationship | critical | import, immediate, baseline, release_gate |
| AAC-RULE-RULE-002 | Relationship type allowed | TOOL, ASPICE_PAM_4_0 | Relationship | critical | import, immediate, baseline, release_gate |
| AAC-RULE-RULE-003 | Unique artefact ID | TOOL, ASPICE_PAM_4_0 | Artefact | critical | import, immediate |
| AAC-RULE-RULE-004 | Required metadata present | ASPICE_PAM_4_0, ISO26262 | Artefact | critical | import, baseline, release_gate |
| AAC-RULE-RULE-005 | Profile mandatory artefact present | ISO26262, ASPICE_PAM_4_0, ISO29119 | Project, Baseline | critical | baseline, release_gate |
| AAC-RULE-RULE-006 | Tailoring decision complete | ISO26262, ASPICE_PAM_4_0 | TailoringDecision | critical | baseline, release_gate |
| AAC-RULE-RULE-010 | ASIL safety requirement allocated | ISO26262, ASPICE_PAM_4_0 | SoftwareSafetyRequirement | critical | immediate, baseline, release_gate |
| AAC-RULE-RULE-011 | Requirement decomposition traced | ISO26262, ASPICE_PAM_4_0 | Requirement | major | baseline, release_gate |
| AAC-RULE-RULE-012 | Requirement has verification intent | ISO26262, ISO29119 | Requirement | critical | baseline, release_gate |
| AAC-RULE-RULE-013 | Released requirement has verification evidence | ISO26262, ISO29119, ASPICE_PAM_4_0 | Requirement | critical | release_gate |
| AAC-RULE-RULE-014 | Safety requirement traces to safety source | ISO26262 | SoftwareSafetyRequirement | critical | baseline, release_gate |
| AAC-RULE-RULE-020 | Component classification defined | ISO26262, ASPICE_PAM_4_0 | SoftwareComponent | critical | import, baseline |
| AAC-RULE-RULE-021 | Software architecture covers requirements | ISO26262, ASPICE_PAM_4_0 | SoftwareArchitecture, SoftwareComponent | critical | baseline, release_gate |
| AAC-RULE-RULE-022 | Interface contract exists for component interaction | ISO26262, ASPICE_PAM_4_0 | SoftwareComponent, InterfaceContract | critical | immediate, baseline |
| AAC-RULE-RULE-023 | Interface source and destination valid | ISO26262, ASPICE_PAM_4_0 | InterfaceContract | critical | import, immediate |
| AAC-RULE-RULE-024 | Interface payload semantics defined | ISO26262 | InterfaceContract | critical | baseline, release_gate |
| AAC-RULE-RULE-025 | QM-to-ASIL interface has failure behavior | ISO26262 | InterfaceContract | critical | immediate, baseline, release_gate |
| AAC-RULE-RULE-026 | Timing-relevant interface has timing verification | ISO26262, ISO29119 | InterfaceContract, TestSpecification | critical | baseline, release_gate |
| AAC-RULE-RULE-027 | ASIL-relevant interface has AG contract | ISO26262 | InterfaceContract, AssumptionGuaranteeContract | critical | immediate, baseline, release_gate |
| AAC-RULE-RULE-030 | Assumption covered by safeguard or test | ISO26262 | Assumption, AssumptionGuaranteeContract | critical | immediate, baseline, release_gate |
| AAC-RULE-RULE-031 | Guarantee mapped to requirement or safeguard | ISO26262 | AssumptionGuaranteeContract | major | baseline |
| AAC-RULE-RULE-032 | Safeguard allocated to ASIL component | ISO26262 | Safeguard | critical | immediate, baseline, release_gate |
| AAC-RULE-RULE-033 | Released safeguard has implementation | ISO26262, ASPICE_PAM_4_0 | Safeguard, ImplementationItem | critical | release_gate |
| AAC-RULE-RULE-034 | Released safeguard has verification | ISO26262, ISO29119 | Safeguard, TestSpecification, TestResult | critical | release_gate |
| AAC-RULE-RULE-040 | Software unit traces to design and requirement | ISO26262, ASPICE_PAM_4_0 | SoftwareUnit, SoftwareUnitDesign | critical | baseline, release_gate |
| AAC-RULE-RULE-041 | Implementation item references valid source | ASPICE_PAM_4_0 | ImplementationItem, SourceCodeReference | major | baseline |
| AAC-RULE-RULE-042 | Build configuration identified | ISO26262, ASPICE_PAM_4_0 | BuildConfiguration | critical | baseline, release_gate |
| AAC-RULE-RULE-043 | Static analysis evidence present or tailored | ISO26262, ASPICE_PAM_4_0 | StaticAnalysisResult | major | release_gate |
| AAC-RULE-RULE-044 | Coding guideline compliance evidence present or tailored | ISO26262, ASPICE_PAM_4_0 | CodingGuidelineComplianceRecord | major | release_gate |
| AAC-RULE-RULE-050 | Test specification traces to test basis | ISO29119, ISO26262, ASPICE_PAM_4_0 | TestSpecification | critical | baseline, release_gate |
| AAC-RULE-RULE-051 | Test case has expected result and pass criteria | ISO29119 | TestCase | critical | baseline, release_gate |
| AAC-RULE-RULE-052 | Test procedure references environment | ISO29119 | TestProcedure, TestEnvironment | major | baseline |
| AAC-RULE-RULE-053 | Test result references valid test case/spec | ISO29119, ASPICE_PAM_4_0 | TestResult | critical | immediate, baseline |
| AAC-RULE-RULE-054 | Failed test result linked to defect or waiver | ISO29119, ASPICE_PAM_4_0 | TestResult, DefectRecord | critical | release_gate |
| AAC-RULE-RULE-055 | Requirements coverage exists | ISO26262, ISO29119, ASPICE_PAM_4_0 | RequirementsCoverageRecord | critical | release_gate |
| AAC-RULE-RULE-060 | Change has impact analysis | ASPICE_PAM_4_0, ISO26262 | ChangeSet, ImpactAnalysisResult | critical | baseline, release_gate |
| AAC-RULE-RULE-061 | Defect resolution traced | ASPICE_PAM_4_0 | DefectRecord | major | release_gate |
| AAC-RULE-RULE-062 | Configuration items baselined | ASPICE_PAM_4_0, ISO26262 | Baseline | critical | baseline |
| AAC-RULE-RULE-063 | Confirmation measure evidence exists | ISO26262 | ConfirmationMeasureRecord | major | release_gate |
| AAC-RULE-RULE-070 | Cybersecurity relevant item has CS evidence | UNECE_R155 | InterfaceContract, SoftwareComponent | critical when condition applies | baseline, release_gate |
| AAC-RULE-RULE-071 | Software update relevant item has SUMS evidence | UNECE_R156 | BuildConfiguration, Baseline, ReleaseGateResult | critical when condition applies | release_gate |
| AAC-RULE-RULE-080 | Released upstream change creates suspect state | ISO26262, ASPICE_PAM_4_0 | Artefact, Relationship | major | immediate |
| AAC-RULE-RULE-081 | Suspect artefact not releasable | ISO26262, ASPICE_PAM_4_0 | SuspectState | critical | release_gate |
| AAC-RULE-RULE-090 | Baseline contains no critical issues | TOOL, ISO26262, ASPICE_PAM_4_0 | Baseline | critical | baseline, release_gate |
| AAC-RULE-RULE-091 | Release gate fails on critical issues | TOOL, ISO26262, ASPICE_PAM_4_0 | ReleaseGateResult | critical | release_gate |

## 3.1 Dynamic Applicability Derivation

AAC-RULE-FR-010
The system shall derive rule enablement from these project configuration dimensions:

- `asil_level`: `QM`, `ASIL_A`, `ASIL_B`, `ASIL_C`, or `ASIL_D`
- `aspice_model`: fixed to `ASPICE_PAM_4_0`
- `aspice_default_capability_level`: `CL1`, `CL2`, or `CL3`
- `aspice_process_overrides`: per-process `CL1`, `CL2`, or `CL3`
- `r155_applicable`
- `r156_applicable`
- `test_scope`

AAC-RULE-FR-011
Rules that are not applicable for the derived project configuration shall be marked disabled and shall not execute.

AAC-RULE-FR-012
If a rule is enabled by any configured standards dimension, it shall remain enabled unless an approved tailoring decision or admin configuration disables it.

AAC-RULE-FR-013
If multiple dimensions assign different severities to the same rule, the stricter severity shall be used.

AAC-RULE-FR-014
For ASPICE PAM 4.0 CL3 targets, PA3.1 and PA3.2 evidence rules shall be enabled for the scoped processes.

## 3.1 Detailed Standards-Driven Rule Groups

AAC-RULE-FR-001
Each rule shall reference one or more `standards_refs` from the standards traceability matrix.

AAC-RULE-FR-002
Each rule shall define its required work product content in machine-checkable terms.

AAC-RULE-FR-003
Each rule shall define review and independence expectations as profile-configurable attributes.

AAC-RULE-FR-004
Each rule shall define the verification method or evidence type it accepts.

AAC-RULE-FR-005
Each rule shall define whether the rule is mandatory, optional, conditional, or disabled for each ASIL profile.

### ISO 26262 Software Rule Anchors

| Rule Group | Standards Refs | Tool Rule Intent |
|---|---|---|
| Software safety requirements | STD-ISO26262-6-6, STD-ISO26262-8-6 | requirements exist, are attributed, traced, reviewed, and verified |
| Software architecture | STD-ISO26262-6-7 | architecture covers requirements and interfaces |
| Interface and HSI handling | STD-ISO26262-6-6, STD-ISO26262-6-7, STD-ISO26262-6-10 | interface contracts define data, timing, failure, and verification behavior |
| Software unit design and implementation | STD-ISO26262-6-8 | unit design and implementation trace to requirements/architecture |
| Unit verification | STD-ISO26262-6-9 | unit verification spec/results exist |
| Integration verification | STD-ISO26262-6-10 | integration and interface verification exists |
| Embedded software testing | STD-ISO26262-6-11 | embedded software test specification/report exists |
| Configuration management | STD-ISO26262-8-7 | baselines/configuration items are controlled |
| Change management | STD-ISO26262-8-8 | changes have impact analysis and re-verification scope |
| Tool confidence | STD-ISO26262-8-11 | tool confidence or qualification evidence exists where applicable |

### Automotive SPICE PAM 4.0 Capability Rule Anchors

| Rule Group | Standards Refs | Tool Rule Intent |
|---|---|---|
| Software requirements | STD-ASPICE-SWE.1 | requirements are specified, structured, analyzed, traced, and communicated |
| Software architecture | STD-ASPICE-SWE.2 | architecture is specified, analyzed, traced, and communicated |
| Detailed design and construction | STD-ASPICE-SWE.3 | detailed design and constructed units are traced |
| Unit verification | STD-ASPICE-SWE.4 | unit verification criteria and results exist |
| Integration verification | STD-ASPICE-SWE.5 | software integration/component verification exists |
| Software verification | STD-ASPICE-SWE.6 | software verification against software requirements exists |
| Quality assurance | STD-ASPICE-SUP.1 | objective quality evidence exists |
| Configuration management | STD-ASPICE-SUP.8 | configuration items and baselines are controlled |
| Problem resolution | STD-ASPICE-SUP.9 | problems are recorded, analyzed, tracked, and closed |
| Change management | STD-ASPICE-SUP.10 | changes are recorded, analyzed, traced, implemented, and closed |
| Process definition | STD-ASPICE-PA3.1 | defined process evidence exists |
| Process deployment | STD-ASPICE-PA3.2 | process deployment evidence exists |

### ISO 29119 Testing Rule Anchors

| Rule Group | Standards Refs | Tool Rule Intent |
|---|---|---|
| Test planning | ISO29119-2, ISO29119-3 | test plan exists with scope, strategy, resources, schedule, risks |
| Test specification | ISO29119-3 | test basis, conditions, cases, procedures, expected results are defined |
| Test execution/result | ISO29119-3 | execution status, verdicts, evidence, defects are recorded |
| Test completion | ISO29119-3 | completion/summary report and coverage status exist |

### UNECE Rule Anchors

| Rule Group | Standards Refs | Tool Rule Intent |
|---|---|---|
| Cybersecurity evidence | UNECE_R155 | cybersecurity-relevant software/interface evidence is referenced |
| Software update evidence | UNECE_R156 | update package, version, approval, and integrity evidence are referenced |

## 4. Rule Detail Template

Every rule shall have an implementation detail record:

```yaml
id: AAC-RULE-RULE-025
title: QM-to-ASIL interface has failure behavior
applies_to_resources:
  - InterfaceContract
condition: "interface.classification == 'QM_to_ASIL'"
required_fields:
  - validity_semantics.invalid_value_behavior
  - error_handling.on_invalid
  - error_handling.on_timeout if timing.timeout_ms is not null
pass_condition: "all required fields are present and non-empty"
fail_condition: "one or more required failure behavior fields are missing"
severity_by_profile:
  ASIL_D: critical
  ASIL_C: critical
  ASIL_B: major
  ASIL_A: major
  QM: disabled
produced_issue_type: missing_interface_failure_behavior
remediation_hint: "Define invalid, timeout, stale, and diagnostic behavior for the interface."
```

## 5. Standards Review Gap

This matrix is implementation-guidance level. Clause-exact derivation from ISO 26262, ISO/IEC/IEEE 29119, Automotive SPICE, UNECE R155, and UNECE R156 requires licensed standard text and project process tailoring.
