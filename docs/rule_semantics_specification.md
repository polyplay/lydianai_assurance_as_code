# Rule Semantics Specification

## 1. Purpose

This document resolves blocker B1 identified in the implementation readiness assessment: the absence of formalized rule condition expressions.

For each configured catalog rule defined in `rule_to_resource_applicability_matrix.md`, this document specifies:
- The precise evaluation context (what data the rule operates on)
- The pass condition (formalized as a Python-evaluable expression)
- The fail condition (what triggers an issue creation)
- Field references using canonical names from `canonical_artefact_name_reconciliation.md`

---

## 2. Expression Syntax Convention

Rule conditions are expressed as Python-style predicate logic against the evaluation context object. They are intended to be implemented as a rule evaluator that receives a typed context dict.

**Convention:**
- `artefact.field_name` — field on the artefact being evaluated
- `relationship.field_name` — field on a relationship
- `project.field_name` — field on the project configuration
- `profile.field_name` — field on the active assurance profile
- `db.has_relationship(artefact_id, rel_type)` — graph query: artefact has at least one active relationship of given type
- `db.get_related(artefact_id, rel_type, direction)` — returns list of related artefacts (direction: outgoing | incoming)
- `db.count_related(artefact_id, rel_type, direction)` — count of related artefacts
- `db.exists(artefact_type, filter_dict)` — project-scoped existence check
- `db.has_open_suspect(artefact_id)` — artefact has open suspect state
- `profile.is_mandatory(artefact_type)` — artefact type is mandatory in current profile
- `profile.severity_for(rule_id)` — rule's configured severity for active profile

---

## 3. Core Validation Rules (RULE-001 to RULE-006)

### AAC-RULE-RULE-001: Referenced artefact exists

**Evaluation context**: Each active relationship

**Pass condition**:
```python
db.artefact_exists(relationship.source_artefact_id) and
db.artefact_exists(relationship.target_artefact_id)
```

**Fail condition**: Either source or target artefact does not exist (has been deleted or was never created)

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: critical, QM: critical

---

### AAC-RULE-RULE-002: Relationship type allowed

**Evaluation context**: Each active relationship

**Pass condition**:
```python
relationship.relationship_type in ALLOWED_RELATIONSHIP_TYPES_FOR[
    (relationship.source_artefact_type, relationship.target_artefact_type)
]
```

Where `ALLOWED_RELATIONSHIP_TYPES_FOR` is the relationship type allowlist defined in `artefact_json_schemas.md`.

**Fail condition**: Relationship type is not permitted between the two artefact types

**Severity by profile**: critical for all profiles

---

### AAC-RULE-RULE-003: Unique artefact ID

**Evaluation context**: Each artefact on import or creation

**Pass condition**:
```python
db.count_artefacts(
    project_id=artefact.project_id,
    source_object_id=artefact.source_object_id,
    source_document=artefact.source_document
) == 1
# (the artefact itself, just inserted)
```

**Fail condition**: More than one active artefact in the project has the same compound source identity key

**Severity by profile**: critical for all profiles

---

### AAC-RULE-RULE-004: Required metadata present

**Evaluation context**: Each artefact

**Pass condition**:
```python
# All fields marked required=true in the artefact's canonical schema are present and non-null
all(
    getattr(artefact, field) is not None and getattr(artefact, field) != ""
    for field in REQUIRED_FIELDS_FOR[artefact.artefact_type]
)
```

**Fail condition**: One or more required fields are null or empty

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-005: Profile mandatory artefact present

**Evaluation context**: Project scope (for baseline/release_gate execution)

**Pass condition**:
```python
for artefact_type in profile.mandatory_artefact_types:
    has_artefact = db.count_active_artefacts(
        project_id=project.project_id, artefact_type=artefact_type
    ) > 0
    has_tailoring = db.exists(
        artefact_type='TailoringDecision',
        filter={
            'project_id': project.project_id,
            'target_artefact_type': artefact_type,
            'tailored_applicability': 'not_applicable',
            'approval_status': 'approved'
        }
    )
    assert has_artefact or has_tailoring
```

**Fail condition**: A mandatory artefact type has no active artefacts in scope and no accepted `not_applicable` tailoring decision

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-006: Tailoring decision complete

**Evaluation context**: Each TailoringDecision artefact

**Pass condition**:
```python
artefact.rationale is not None and len(artefact.rationale) > 0 and
artefact.evidence_refs is not None and len(artefact.evidence_refs) > 0 and
artefact.scope is not None and
artefact.approver_id is not None and
artefact.approval_timestamp is not None and
artefact.previous_applicability is not None and
artefact.tailored_applicability is not None
```

**Fail condition**: Any required tailoring decision field is missing

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

## 4. Requirements Rules (RULE-010 to RULE-014)

### AAC-RULE-RULE-010: ASIL safety requirement allocated

**Evaluation context**: Each SoftwareSafetyRequirement

**Pass condition**:
```python
db.count_related(
    artefact.artefact_id,
    rel_type='allocates_to',
    direction='outgoing'
) > 0
```

**Fail condition**: SoftwareSafetyRequirement has no `allocates_to` relationship pointing to a SoftwareComponent

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: disabled

---

### AAC-RULE-RULE-011: Requirement decomposition traced

**Evaluation context**: Each SoftwareRequirement, SoftwareSafetyRequirement, DerivedSoftwareRequirement with `has_children=True` or `decomposition_type != None`

**Pass condition**:
```python
if artefact.is_parent_requirement:
    db.count_related(
        artefact.artefact_id, rel_type='derives_from', direction='incoming'
    ) > 0
else:
    True  # leaf requirements need no children
```

**Fail condition**: An artefact marked as a parent requirement (via `is_parent_requirement=True` or `decomposition_type` set) has no incoming `derives_from` relationships

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: minor, QM: info

---

### AAC-RULE-RULE-012: Requirement has verification intent

**Evaluation context**: Each SoftwareSafetyRequirement and SoftwareRequirement

**Pass condition**:
```python
artefact.verification_intent is not None and
artefact.verification_intent in ['test', 'analysis', 'inspection', 'simulation', 'formal_verification']
```

**Fail condition**: `verification_intent` field is null or not set to a recognized method

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-013: Released requirement has verification evidence

**Evaluation context**: Each released SoftwareSafetyRequirement and SoftwareRequirement (release_gate only)

**Pass condition**:
```python
artefact.lifecycle_status == 'released' implies (
    db.count_related(
        artefact.artefact_id, rel_type='verifies', direction='incoming'
    ) > 0 and
    any(
        result.verdict == 'pass'
        for result in db.get_related(artefact.artefact_id, 'verifies', 'incoming')
        if result.artefact_type == 'TestResult'
    )
)
```

**Fail condition**: A released requirement has no incoming `verifies` relationship from a TestResult with `verdict=pass`

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-014: Safety requirement traces to safety source

**Evaluation context**: Each SoftwareSafetyRequirement

**Pass condition**:
```python
# Must trace back to at least one of: TechnicalSafetyRequirement, HardwareSoftwareInterface, SafetyGoal
has_tsr = db.count_related(artefact.artefact_id, 'derives_from', 'outgoing',
    target_type='TechnicalSafetyRequirement') > 0
has_hsi = db.count_related(artefact.artefact_id, 'derives_from', 'outgoing',
    target_type='HardwareSoftwareInterface') > 0
has_goal = db.count_related(artefact.artefact_id, 'derives_from', 'outgoing',
    target_type='SafetyGoal') > 0

has_tsr or has_hsi or has_goal
```

**Fail condition**: SSR has no outgoing `derives_from` to a TSR, HSI, or SafetyGoal

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: disabled

---

## 5. Architecture And Component Rules (RULE-020 to RULE-027)

### AAC-RULE-RULE-020: Component classification defined

**Evaluation context**: Each SoftwareComponent

**Pass condition**:
```python
artefact.criticality_classification is not None and
artefact.criticality_classification in ['QM', 'ASIL_A', 'ASIL_B', 'ASIL_C', 'ASIL_D', 'mixed']
```

**Fail condition**: `criticality_classification` is null or not a valid ASIL level

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-021: Software architecture covers requirements

**Evaluation context**: Project scope — SoftwareArchitecture and SoftwareComponent

**Pass condition**:
```python
# Every released SoftwareSafetyRequirement must have at least one
# allocates_to relationship targeting a SoftwareComponent
for req in db.get_released_artefacts(project_id, 'SoftwareSafetyRequirement'):
    assert db.count_related(req.artefact_id, 'allocates_to', 'outgoing') > 0

# Every SoftwareComponent must be part of at least one SoftwareArchitecture
for comp in db.get_active_artefacts(project_id, 'SoftwareComponent'):
    assert db.count_related(comp.artefact_id, 'allocates_to', 'incoming') > 0 or
           db.count_related(comp.artefact_id, 'satisfies', 'outgoing') > 0
```

**Fail condition**: Any released SSR has no component allocation, or any component is unreferenced by any architecture element

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-022: Interface contract exists for component interaction

**Evaluation context**: Each pair of SoftwareComponents with a `depends_on` or `interacts_via` relationship

**Pass condition**:
```python
for rel in db.get_active_relationships(
    project_id, rel_type='depends_on', source_type='SoftwareComponent'
):
    assert db.exists_relationship(
        source_artefact_id=rel.source_artefact_id,
        target_artefact_id=rel.target_artefact_id,
        rel_type='interacts_via'
    ) or db.exists_artefact_linking(
        rel.source_artefact_id, rel.target_artefact_id,
        link_artefact_type='InterfaceContract'
    )
```

**Fail condition**: Two components have a `depends_on` relationship but no associated InterfaceContract

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

### AAC-RULE-RULE-023: Interface source and destination valid

**Evaluation context**: Each InterfaceContract

**Pass condition**:
```python
artefact.source_component_id is not None and
artefact.destination_component_id is not None and
db.artefact_exists(artefact.source_component_id) and
db.artefact_exists(artefact.destination_component_id) and
artefact.source_component_id != artefact.destination_component_id
```

**Fail condition**: Source or destination component reference is null, references a non-existent artefact, or source equals destination

**Severity by profile**: critical for all profiles

---

### AAC-RULE-RULE-024: Interface payload semantics defined

**Evaluation context**: Each InterfaceContract (baseline, release_gate)

**Pass condition**:
```python
artefact.payload_type is not None and
artefact.data_elements is not None and len(artefact.data_elements) > 0 and
all(
    elem.get('name') and elem.get('type') and elem.get('range') is not None
    for elem in artefact.data_elements
)
```

**Fail condition**: `payload_type` is null, `data_elements` is empty, or any data element is missing name, type, or range

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

### AAC-RULE-RULE-025: QM-to-ASIL interface has failure behavior

**Evaluation context**: Each InterfaceContract where the interface crosses a criticality boundary

**Applicability condition**:
```python
source_comp = db.get_artefact(artefact.source_component_id)
dest_comp = db.get_artefact(artefact.destination_component_id)
artefact.criticality_classification == 'QM_to_ASIL' or (
    source_comp.criticality_classification == 'QM' and
    dest_comp.criticality_classification in ['ASIL_A', 'ASIL_B', 'ASIL_C', 'ASIL_D']
)
```

**Pass condition** (when applicable):
```python
artefact.validity_semantics is not None and
artefact.validity_semantics.get('invalid_value_behavior') is not None and
artefact.error_handling is not None and
artefact.error_handling.get('on_invalid') is not None and
(
    artefact.timing is None or artefact.timing.get('timeout_ms') is None or
    artefact.error_handling.get('on_timeout') is not None
)
```

**Fail condition**: Interface crosses QM→ASIL criticality boundary but is missing failure behavior specifications

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: disabled

---

### AAC-RULE-RULE-026: Timing-relevant interface has timing verification

**Evaluation context**: Each InterfaceContract where timing constraints are defined

**Applicability condition**:
```python
artefact.timing is not None and (
    artefact.timing.get('period_ms') is not None or
    artefact.timing.get('deadline_ms') is not None or
    artefact.timing.get('jitter_ms') is not None
)
```

**Pass condition** (when applicable):
```python
# Must have at least one TestSpecification or TestResult that references this interface
# with timing verification objective
db.exists(
    artefact_type='TestSpecification',
    filter={
        'project_id': project.project_id,
        'test_basis_refs': {'contains': artefact.artefact_id},
        'timing_verification': True
    }
) or db.exists_relationship(
    target_artefact_id=artefact.artefact_id,
    rel_type='verifies',
    source_filter={'artefact_type': 'TestResult', 'verdict': 'pass'}
)
```

**Fail condition**: Interface has timing constraints but no timing verification evidence

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

### AAC-RULE-RULE-027: ASIL-relevant interface has AG contract

**Evaluation context**: Each InterfaceContract

**Applicability condition**:
```python
# Interface involves at least one ASIL-classified component
source_comp = db.get_artefact(artefact.source_component_id)
dest_comp = db.get_artefact(artefact.destination_component_id)
any(
    comp.criticality_classification in ['ASIL_A', 'ASIL_B', 'ASIL_C', 'ASIL_D']
    for comp in [source_comp, dest_comp]
    if comp is not None
)
```

**Pass condition** (when applicable):
```python
db.count_related(
    artefact.artefact_id,
    rel_type='references',
    direction='incoming',
    source_type='AssumptionGuaranteeContract'
) > 0
```

**Fail condition**: ASIL-relevant interface has no AssumptionGuaranteeContract referencing it

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

## 6. Assumption And Safeguard Rules (RULE-030 to RULE-034)

### AAC-RULE-RULE-030: Assumption covered by safeguard or test

**Evaluation context**: Each Assumption artefact

**Pass condition**:
```python
# Assumption must have at least one of:
# (a) a Safeguard that protects against its violation
# (b) a TestCase/TestSpecification that verifies the assumption holds
has_safeguard = db.count_related(
    artefact.artefact_id, 'protects', 'incoming', source_type='Safeguard'
) > 0
has_test = db.count_related(
    artefact.artefact_id, 'verifies', 'incoming',
    source_type_in=['TestCase', 'TestSpecification']
) > 0

has_safeguard or has_test
```

**Fail condition**: Assumption has neither safeguard protection nor test verification

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

### AAC-RULE-RULE-031: Guarantee mapped to requirement or safeguard

**Evaluation context**: Each AssumptionGuaranteeContract

**Pass condition**:
```python
# Each guarantee in the AG contract must trace to a requirement or safeguard
all(
    db.count_related(guarantee.artefact_id, 'satisfies', 'outgoing',
        target_type_in=['SoftwareSafetyRequirement', 'SoftwareRequirement', 'Safeguard']) > 0
    for guarantee in artefact.guarantees
) if artefact.guarantees else True
```

**Fail condition**: A guarantee within the AG contract has no `satisfies` relationship to a requirement or safeguard

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

### AAC-RULE-RULE-032: Safeguard allocated to ASIL component

**Evaluation context**: Each Safeguard

**Pass condition**:
```python
allocated_components = db.get_related(
    artefact.artefact_id, 'allocates_to', 'outgoing', target_type='SoftwareComponent'
)
len(allocated_components) > 0 and all(
    comp.criticality_classification in ['ASIL_A', 'ASIL_B', 'ASIL_C', 'ASIL_D']
    for comp in allocated_components
)
```

**Fail condition**: Safeguard has no allocation to an ASIL-classified component, or is allocated to a QM-only component

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: disabled

---

### AAC-RULE-RULE-033: Released safeguard has implementation

**Evaluation context**: Each released Safeguard (release_gate only)

**Pass condition**:
```python
artefact.lifecycle_status == 'released' implies (
    db.count_related(
        artefact.artefact_id, 'implements', 'incoming', source_type='ImplementationItem'
    ) > 0
)
```

**Fail condition**: Released safeguard has no incoming `implements` from an ImplementationItem

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-034: Released safeguard has verification

**Evaluation context**: Each released Safeguard (release_gate only)

**Pass condition**:
```python
artefact.lifecycle_status == 'released' implies (
    db.count_related(
        artefact.artefact_id, 'verifies', 'incoming',
        source_type='TestResult', filter={'verdict': 'pass'}
    ) > 0 or
    db.count_related(
        artefact.artefact_id, 'verifies', 'incoming', source_type='TestSpecification'
    ) > 0
)
```

**Fail condition**: Released safeguard has no test result (pass verdict) or test specification verifying it

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

## 7. Implementation Rules (RULE-040 to RULE-044)

### AAC-RULE-RULE-040: Software unit traces to design and requirement

**Evaluation context**: Each SoftwareUnit

**Pass condition**:
```python
has_design = db.count_related(
    artefact.artefact_id, 'satisfies', 'outgoing', target_type='SoftwareUnitDesign'
) > 0
has_req = (
    db.count_related(artefact.artefact_id, 'implements', 'outgoing',
        target_type='SoftwareRequirement') > 0 or
    db.count_related(artefact.artefact_id, 'implements', 'outgoing',
        target_type='SoftwareSafetyRequirement') > 0
)
has_design and has_req
```

**Fail condition**: SoftwareUnit lacks design trace or requirement trace

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-041: Implementation item references valid source

**Evaluation context**: Each ImplementationItem

**Pass condition**:
```python
artefact.source_references is not None and len(artefact.source_references) > 0 and
all(
    ref.get('reference_type') in ['source_file', 'build_artifact', 'configuration_file'] and
    ref.get('location') is not None
    for ref in artefact.source_references
)
```

**Fail condition**: ImplementationItem has no source references or references lack required fields

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

### AAC-RULE-RULE-042: Build configuration identified

**Evaluation context**: Project scope — BuildConfiguration presence

**Pass condition**:
```python
db.count_active_artefacts(project_id, 'BuildConfiguration') > 0 and
all(
    bc.compiler_version is not None and
    bc.build_flags is not None and
    bc.target_architecture is not None
    for bc in db.get_active_artefacts(project_id, 'BuildConfiguration')
)
```

**Fail condition**: No BuildConfiguration exists, or existing one lacks compiler version, build flags, or target architecture

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-043: Static analysis evidence present or tailored

**Evaluation context**: Project scope (release_gate)

**Pass condition**:
```python
has_result = db.count_active_artefacts(project_id, 'StaticAnalysisResult') > 0
has_tailoring = db.exists(
    artefact_type='TailoringDecision',
    filter={
        'project_id': project_id,
        'target_artefact_type': 'StaticAnalysisResult',
        'tailored_applicability': 'not_applicable',
        'approval_status': 'approved'
    }
)
has_result or has_tailoring
```

**Fail condition**: No StaticAnalysisResult and no accepted not-applicable tailoring

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

### AAC-RULE-RULE-044: Coding guideline compliance evidence present or tailored

**Evaluation context**: Project scope (release_gate)

**Pass condition**:
```python
has_result = db.count_active_artefacts(project_id, 'CodingGuidelineComplianceRecord') > 0
has_tailoring = db.exists_tailoring_not_applicable(
    project_id, 'CodingGuidelineComplianceRecord'
)
has_result or has_tailoring
```

**Fail condition**: No CodingGuidelineComplianceRecord and no accepted not-applicable tailoring

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

## 8. Testing Rules (RULE-050 to RULE-055)

### AAC-RULE-RULE-050: Test specification traces to test basis

**Evaluation context**: Each TestSpecification

**Pass condition**:
```python
artefact.test_basis_refs is not None and len(artefact.test_basis_refs) > 0 and
all(db.artefact_exists(ref) for ref in artefact.test_basis_refs)
```

**Fail condition**: TestSpecification has no test basis references or references non-existent artefacts

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-051: Test case has expected result and pass criteria

**Evaluation context**: Each TestCase

**Pass condition**:
```python
artefact.expected_result is not None and len(artefact.expected_result) > 0 and
artefact.pass_criteria is not None and len(artefact.pass_criteria) > 0
```

**Fail condition**: TestCase lacks `expected_result` or `pass_criteria`

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-052: Test procedure references environment

**Evaluation context**: Each TestProcedure

**Pass condition**:
```python
artefact.test_environment_ref is not None and
db.artefact_exists(artefact.test_environment_ref)
```

**Fail condition**: TestProcedure has no reference to a TestEnvironment artefact

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

### AAC-RULE-RULE-053: Test result references valid test case/spec

**Evaluation context**: Each TestResult

**Pass condition**:
```python
(
    artefact.test_case_ref is not None and db.artefact_exists(artefact.test_case_ref)
) or (
    artefact.test_spec_ref is not None and db.artefact_exists(artefact.test_spec_ref)
)
```

**Fail condition**: TestResult references neither a valid TestCase nor a valid TestSpecification

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-054: Failed test result linked to defect or waiver

**Evaluation context**: Each TestResult with verdict=fail (release_gate)

**Applicability condition**:
```python
artefact.verdict == 'fail'
```

**Pass condition** (when applicable):
```python
has_defect = db.count_related(
    artefact.artefact_id, 'references', 'outgoing', target_type='DefectRecord'
) > 0
has_waiver = artefact.waiver_ref is not None and db.artefact_exists(artefact.waiver_ref)
has_defect or has_waiver
```

**Fail condition**: TestResult with `verdict=fail` has no linked DefectRecord and no waiver reference

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: critical, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-055: Requirements coverage exists

**Evaluation context**: Project scope (release_gate)

**Pass condition**:
```python
# A RequirementsCoverageRecord must exist with coverage >= profile-configured minimum
coverage_records = db.get_active_artefacts(project_id, 'RequirementsCoverageRecord')
len(coverage_records) > 0 and any(
    record.coverage_percentage >= profile.minimum_requirements_coverage_percentage
    for record in coverage_records
)
```

**Fail condition**: No RequirementsCoverageRecord, or all records show coverage below the profile minimum (default: 100% for ASIL D)

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

## 9. Change And Impact Rules (RULE-060 to RULE-063)

### AAC-RULE-RULE-060: Change has impact analysis

**Evaluation context**: Each ChangeSet

**Pass condition**:
```python
db.count_related(
    artefact.artefact_id, 'references', 'outgoing', target_type='ImpactAnalysisResult'
) > 0
```

**Fail condition**: ChangeSet has no associated ImpactAnalysisResult

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: minor, QM: disabled

---

### AAC-RULE-RULE-061: Defect resolution traced

**Evaluation context**: Each DefectRecord (release_gate)

**Pass condition**:
```python
artefact.status in ['closed', 'wont_fix', 'not_reproducible'] or (
    artefact.resolution_description is not None and
    len(artefact.resolution_description) > 0
)
```

**Fail condition**: DefectRecord is not closed and lacks a resolution description

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: info, QM: disabled

---

### AAC-RULE-RULE-062: Configuration items baselined

**Evaluation context**: Project scope at baseline creation

**Pass condition**:
```python
# All released artefacts in scope are included in the baseline snapshot
all(
    db.artefact_in_baseline(artefact_id, baseline_id)
    for artefact_id in db.get_released_artefact_ids(project_id)
)
```

**Fail condition**: One or more released artefacts are absent from the baseline snapshot

**Severity by profile**: critical for all profiles at ASIL A and above; minor for QM

---

### AAC-RULE-RULE-063: Confirmation measure evidence exists

**Evaluation context**: Project scope (release_gate) — per ASIL D

**Applicability condition**:
```python
profile.asil_level in ['ASIL_C', 'ASIL_D']
```

**Pass condition** (when applicable):
```python
db.count_active_artefacts(project_id, 'ConfirmationMeasureRecord') > 0 and
all(
    record.independent_reviewer_id is not None and
    record.independent_reviewer_id != record.primary_author_id
    for record in db.get_active_artefacts(project_id, 'ConfirmationMeasureRecord')
)
```

**Fail condition**: No ConfirmationMeasureRecord, or records lack independent reviewer

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: disabled, ASIL_A: disabled, QM: disabled

---

## 10. UNECE R155/R156 Rules (RULE-070, RULE-071)

### AAC-RULE-RULE-070: Cybersecurity relevant item has CS evidence

**Evaluation context**: Each InterfaceContract and SoftwareComponent

**Applicability condition**:
```python
# Project has cybersecurity relevance AND artefact is flagged as security-relevant
project.has_cybersecurity_relevance == True and (
    artefact.security_relevant == True or
    artefact.artefact_type == 'InterfaceContract' and artefact.security_classification != None
)
```

**Pass condition** (when applicable):
```python
# Must have linked CybersecurityManagementEvidence or CybersecurityInterfaceEvidence
db.count_related(
    artefact.artefact_id, 'references', 'outgoing',
    target_type_in=['CybersecurityManagementEvidence', 'CybersecurityInterfaceEvidence']
) > 0
```

**Fail condition**: Cybersecurity-relevant artefact has no cybersecurity evidence reference

**Severity by profile**: When condition applies → ASIL_D: critical, ASIL_C: critical; otherwise disabled

---

### AAC-RULE-RULE-071: Software update relevant item has SUMS evidence

**Evaluation context**: Project scope — BuildConfiguration and Baseline (release_gate)

**Applicability condition**:
```python
project.has_software_update_relevance == True
```

**Pass condition** (when applicable):
```python
# A SoftwareUpdateManagementEvidence artefact must exist and link to the baseline/build
db.count_active_artefacts(project_id, 'SoftwareUpdateManagementEvidence') > 0 and
db.count_related(
    baseline_id, 'references', 'outgoing', target_type='SoftwareUpdateManagementEvidence'
) > 0
```

**Fail condition**: Project requires SUMS evidence but none is linked to the baseline

**Severity by profile**: When condition applies → critical for all ASIL profiles; otherwise disabled

---

## 11. Suspect And Baseline Rules (RULE-080 to RULE-091)

### AAC-RULE-RULE-080: Released upstream change creates suspect state

**Evaluation context**: Any artefact or relationship change event on a released artefact

**Note**: This rule is not a passive checker — it is a trigger rule. Its evaluation IS the suspect propagation algorithm defined in `suspect_propagation_specification.md`. When this rule fires, it calls the propagation algorithm.

**Pass condition**: No open suspect states downstream of the changed artefact

**Fail condition**: One or more downstream artefacts became suspect (emits ValidationIssue per suspect state created)

**Severity by profile**: ASIL_D: major, ASIL_C: major, ASIL_B: minor, ASIL_A: minor, QM: info

---

### AAC-RULE-RULE-081: Suspect artefact not releasable

**Evaluation context**: Each SuspectState (release_gate)

**Pass condition**:
```python
artefact.status == 'cleared'
# OR
# The suspect artefact is not included in the baseline scope
not db.artefact_in_baseline(suspect_state.artefact_id, baseline_id)
```

**Fail condition**: Open (uncleared) suspect state exists for an artefact in the baseline scope

**Severity by profile**: ASIL_D: critical, ASIL_C: critical, ASIL_B: major, ASIL_A: major, QM: minor

---

### AAC-RULE-RULE-090: Baseline contains no critical issues

**Evaluation context**: Each Baseline (baseline execution mode)

**Pass condition**:
```python
db.count_validation_issues(
    baseline_id=baseline_id,
    severity='critical',
    status='open',
    blocking_contexts_includes='baseline'
) == 0
```

**Fail condition**: Any open critical validation issue exists in the baseline scope with `baseline` in its blocking_contexts

**Severity by profile**: critical for all profiles at ASIL A and above

---

### AAC-RULE-RULE-091: Release gate fails on critical issues

**Evaluation context**: Each ReleaseGateResult (release_gate execution mode)

**Pass condition**:
```python
db.count_validation_issues(
    baseline_id=baseline_id,
    severity='critical',
    status='open',
    blocking_contexts_includes='release_gate'
) == 0
```

**Fail condition**: Any open critical validation issue exists in the baseline scope with `release_gate` in its blocking_contexts

**Severity by profile**: critical for all profiles at ASIL A and above

---

## 12. Artefact Lifecycle State Machine

The following states apply to all artefact types (including the missing state machine from the completeness assessment):

```
draft → under_review → reviewed → approved → released → obsolete
                                ↗
                    rejected (→ back to draft)
```

| State | Description |
|---|---|
| `draft` | Being authored; not yet submitted for review |
| `under_review` | Submitted for review; awaiting reviewer action |
| `reviewed` | Reviewed (with or without comments); not yet approved |
| `approved` | Approved by authorized role; eligible for baseline |
| `released` | Released (final); triggers suspect propagation on change |
| `obsolete` | Soft-deleted; excluded from active processing |

**State transition permissions:**

| Transition | Required Role |
|---|---|
| draft → under_review | User (author) |
| under_review → reviewed | Any project member with reviewer role or higher |
| under_review → rejected → draft | Reviewer |
| reviewed → approved | Project Lead or Admin |
| approved → released | Quality Engineer or Admin |
| any → obsolete | Admin (soft-delete/obsolete path) |
| released → draft | NOT PERMITTED without creating new revision |
