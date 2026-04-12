# Suspect Propagation And Impact Analysis Specification

## 1. Purpose

This document resolves blocker B8 identified in the implementation readiness assessment: the absence of a suspect propagation algorithm.

It defines the precise rules for when artefacts enter suspect state, which relationship traversals propagate suspects, the transitive closure algorithm, and how suspect states are cleared.

---

## 2. Suspect State Semantics

### 2.1 Definition

AAC-IMPACT-FR-001
An artefact is in **suspect state** when a change has occurred upstream in its traceability chain that may invalidate its content, its verification evidence, or its safety argument, and that change has not yet been reviewed and accepted.

AAC-IMPACT-FR-002
Suspect state is not a validation error. It is a signal that human review is required to confirm the downstream artefact remains valid given the upstream change.

AAC-IMPACT-FR-003
An artefact with unresolved suspect state shall not be included in a releasable baseline (blocked by `AAC-RULE-RULE-081` at release gate).

### 2.2 Suspect State Record

Each suspect state is captured as a `SuspectState` record:

```json
{
  "suspect_state_id": "string",
  "artefact_id": "string",
  "trigger_artefact_id": "string",
  "trigger_revision_id": "string",
  "trigger_event": "artefact.revised | artefact.status_changed | relationship.deleted",
  "propagation_depth": "integer (1 = direct trigger, 2 = indirect, etc.)",
  "propagation_path": ["list of artefact IDs from trigger to suspect"],
  "created_at": "ISO8601 timestamp",
  "status": "open | cleared",
  "cleared_at": "ISO8601 timestamp or null",
  "cleared_by": "string or null",
  "clearing_method": "reviewed_and_accepted | re_verified | not_applicable | null",
  "clearing_evidence_refs": ["list of EvidenceReference IDs"]
}
```

---

## 3. Trigger Conditions

AAC-IMPACT-FR-010
Suspect propagation shall be triggered when any of the following occur to a **released** artefact (lifecycle status = `released`) or an artefact in an **approved or released baseline**:

| Trigger | Description |
|---------|-------------|
| `artefact.revised` | Content of a released artefact changes |
| `artefact.status_changed` (→ obsolete) | A released artefact is deleted/obsoleted |
| `relationship.deleted` | A relationship that provided traceability is deleted |

AAC-IMPACT-FR-011
Changes to artefacts that are `draft` or `reviewed` but not `released` or in an approved/released baseline shall NOT trigger suspect propagation. They may trigger validation issues but not suspect states.

AAC-IMPACT-FR-012
Suspect propagation shall also be triggered when a relationship that is part of the propagation graph is deleted, even if no artefact content changed. Deletion of a verification relationship (`verifies`) between a TestResult and a Requirement is treated as equivalent to the requirement losing its verification evidence.

---

## 4. Propagation Graph Definition

### 4.1 Propagation-Eligible Relationship Types

Not all relationship types propagate suspect states. Only relationships that imply a downstream dependency (i.e., "if the upstream changes, I might need to change too") are eligible.

AAC-IMPACT-FR-020
The following relationship types shall propagate suspect state from source to target:

| Relationship Type | Direction | Rationale |
|---|---|---|
| `allocates_to` | source → target | If requirement changes, component allocation may be invalid |
| `satisfies` | target → source | If source requirement changes, the satisfying artefact may need revision |
| `derives_from` | target → source | If parent requirement changes, derived requirement may be invalid |
| `implements` | target → source | If requirement/design changes, implementation may be invalid |
| `verifies` | target → source | If verified artefact changes, verification result may be invalid |
| `produces_result_for` | target → source | If test case changes, test result is suspect |
| `depends_on` | source → target | If depended-on component changes, dependent component may be affected |
| `constrains` | source → target | If constraint changes, constrained component is suspect |
| `protects` | target → source | If fault scope changes, safeguard may be insufficient |
| `assumes` | source → target | If assumption context changes, downstream is suspect |

AAC-IMPACT-FR-021
The following relationship types shall NOT propagate suspect state (they are informational or configuration references):

| Relationship Type | Rationale |
|---|---|
| `references` | Informational only; not a dependency |
| `interacts_via` | Interface contract is separately validated; no automatic suspect |
| `guarantees` | Guarantee is separately verified; no automatic propagation |
| `mitigates` | Reviewed separately; not automatically propagated |
| `traces_to` | General traceability link; reviewed on a case-by-case basis |

### 4.2 Propagation Direction

AAC-IMPACT-FR-025
Suspect propagation follows the **downstream dependency direction** from the changed artefact toward artefacts that depend on it.

AAC-IMPACT-FR-026
The propagation direction for each relationship type is:

- For `verifies`, `derives_from`, `satisfies`, `implements`, `produces_result_for`, `protects`, `assumes`: propagation flows from the target artefact TOWARD any artefact that has a dependency on the target (i.e., follow the relationship backwards: if A `verifies` B and B changes, then A becomes suspect)
- For `allocates_to`, `depends_on`, `constrains`: propagation flows from the source artefact forward toward its targets

The rule: **"if I depend on you and you changed, I become suspect."**

---

## 5. Transitive Closure Algorithm

AAC-IMPACT-FR-030
Suspect propagation shall use a breadth-first traversal of the propagation graph starting from the trigger artefact.

```python
def propagate_suspects(trigger_artefact_id, trigger_revision_id, trigger_event, db):
    """
    Breadth-first suspect propagation from trigger artefact.
    Returns list of new SuspectState records created.
    """
    visited = set()
    queue = deque([(trigger_artefact_id, [], 0)])  # (artefact_id, path, depth)
    new_suspects = []

    while queue:
        current_id, path, depth = queue.popleft()

        if current_id in visited:
            continue
        visited.add(current_id)

        # Find all artefacts that depend on current_id via propagation-eligible relationships
        dependents = db.get_dependents(current_id, PROPAGATION_ELIGIBLE_RELATIONSHIPS)

        for dependent_id, relationship_type in dependents:
            if dependent_id == trigger_artefact_id:
                continue  # No circular suspects back to trigger

            if dependent_id in visited:
                continue

            if depth + 1 > MAX_PROPAGATION_DEPTH:
                continue  # Depth limit reached; log warning

            propagation_path = path + [current_id]

            # Check if suspect state already exists and is open
            existing = db.get_open_suspect_state(dependent_id, trigger_artefact_id)
            if existing:
                continue  # Already suspect from this trigger

            suspect = SuspectState(
                artefact_id=dependent_id,
                trigger_artefact_id=trigger_artefact_id,
                trigger_revision_id=trigger_revision_id,
                trigger_event=trigger_event,
                propagation_depth=depth + 1,
                propagation_path=propagation_path + [dependent_id],
                status="open"
            )
            db.insert(suspect)
            new_suspects.append(suspect)

            # Emit event
            emit(Event("suspect.propagated", payload=suspect.to_dict()))

            # Continue propagation from dependent
            queue.append((dependent_id, propagation_path + [dependent_id], depth + 1))

    return new_suspects
```

AAC-IMPACT-FR-031
The maximum propagation depth (`MAX_PROPAGATION_DEPTH`) shall be configurable per project, with a default of **10 hops**.

AAC-IMPACT-FR-032
If the propagation depth limit is reached, the back-end shall log a warning-level audit event noting the truncated propagation chain and listing the artefact where depth limit was hit.

AAC-IMPACT-FR-033
The propagation algorithm shall only traverse **active** (non-deleted, non-obsolete) relationships and artefacts. Soft-deleted artefacts and relationships shall be excluded from traversal.

---

## 6. Clearing Suspect State

### 6.1 Clearing Methods

AAC-IMPACT-FR-040
A suspect state may be cleared by one of the following methods:

| Method | Description | Who |
|--------|-------------|-----|
| `reviewed_and_accepted` | Human review confirmed the suspect artefact remains valid despite upstream change | Any authorized project member |
| `re_verified` | A new verification run (test or analysis) produced a passing result after the upstream change | Quality Engineer or User |
| `not_applicable` | The upstream change does not affect this artefact's scope; rationale provided | Project Lead |

AAC-IMPACT-FR-041
Clearing a suspect state requires:
- `cleared_by`: user ID of the person clearing
- `clearing_method`: one of the values above
- `clearing_evidence_refs`: at least one EvidenceReference ID (except for `reviewed_and_accepted` where the audit event itself is the evidence)

AAC-IMPACT-FR-042
Clearing a suspect state shall emit a `suspect.cleared` domain event.

AAC-IMPACT-FR-043
Clearing a suspect state shall create an AuditEvent with the clearing method, evidence, and actor.

### 6.2 Automatic Clearing

AAC-IMPACT-FR-050
The system shall automatically clear a suspect state when:

1. A new revision of the suspect artefact is created that was authored after the trigger revision was created. (The author has implicitly reviewed the upstream change by producing a new revision.)
2. The trigger artefact itself is rolled back (its revision is reverted) to the pre-change revision. This is an admin operation.
3. The suspect artefact is soft-deleted (obsolete). A deleted artefact cannot remain suspect.

AAC-IMPACT-FR-051
Automatic clearing shall set `clearing_method = "system_auto"` and `cleared_by = "system"`.

### 6.3 Cascade Clearing

AAC-IMPACT-FR-055
When a suspect state is cleared, the system shall NOT automatically clear downstream suspect states that were propagated from the same trigger through the now-cleared artefact. Each artefact's suspect state must be independently cleared.

Rationale: The downstream artefact may have additional reasons to be suspect, or the reviewer of the downstream artefact needs to make their own determination.

---

## 7. Impact Analysis

### 7.1 Purpose

Impact analysis is a related but distinct operation from suspect propagation. While suspect propagation automatically creates suspect states on artefact change, impact analysis provides a user-initiated, on-demand analysis of the potential scope of impact before a change is made.

### 7.2 Impact Analysis Algorithm

AAC-IMPACT-FR-060
An impact analysis shall compute the full transitive set of artefacts that would become suspect if the specified artefact were changed, using the same propagation graph as suspect propagation.

AAC-IMPACT-FR-061
An impact analysis shall also compute artefacts that depend on the target artefact through non-propagating relationships (for informational purposes), marking them as `affected_informational`.

AAC-IMPACT-FR-062
The impact analysis result shall categorize affected artefacts by:
- Impact severity: `direct` (depth=1) vs `indirect` (depth>1)
- Artefact type distribution
- Baseline membership (artefacts in active baselines are highest priority)
- Verification coverage (whether the affected artefact has test results)

### 7.3 Impact Analysis Result Schema

```json
{
  "impact_analysis_run_id": "string",
  "trigger_artefact_id": "string",
  "trigger_artefact_type": "string",
  "analysis_timestamp": "ISO8601 timestamp",
  "triggered_by": "string",
  "affected_artefacts": [
    {
      "artefact_id": "string",
      "artefact_type": "string",
      "impact_type": "suspect_propagation | informational",
      "propagation_depth": "integer",
      "propagation_path": ["list of artefact IDs"],
      "in_released_baseline": "boolean",
      "has_open_test_results": "boolean"
    }
  ],
  "summary": {
    "total_affected": "integer",
    "direct_dependencies": "integer",
    "in_released_baselines": "integer",
    "artefact_type_counts": {}
  }
}
```

---

## 8. Interaction With Baseline And Release Gate

AAC-IMPACT-FR-070
A baseline shall not be released if any artefact included in the baseline has an open `SuspectState`. This is enforced by rule `AAC-RULE-RULE-081` at the release gate.

AAC-IMPACT-FR-071
The release gate evaluation shall query for open suspect states across all artefacts in the baseline scope.

AAC-IMPACT-FR-072
If a suspect state exists for an artefact that was excluded from the baseline scope via a not-applicable tailoring decision, the suspect state shall not block the release gate for that baseline.

AAC-IMPACT-FR-073
The baseline creation snapshot shall record the count of open suspect states at the time of baseline creation, even if they are not blocking (e.g., for non-released artefacts).
