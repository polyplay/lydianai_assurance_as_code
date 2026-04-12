# Release Gate State Machine Specification

## 1. Purpose

This document resolves blocker B9 identified in the implementation readiness assessment: the incomplete release-gate state machine.

It supplements `baseline_state_machine.md` with the formal state machine for release-gate evaluation, the precise transition conditions, the re-evaluation policy, and the integration with the baseline approval and release workflow.

---

## 2. Baseline Lifecycle Integration

The release gate is a sub-process within the baseline lifecycle defined in `baseline_state_machine.md`. The complete integrated lifecycle is:

```
requested
    │
    ▼
update_lock_acquired
    │
    ▼
eligibility_check_running ──────► eligibility_failed ──► (terminal; lock released)
    │
    ▼
creating_snapshot
    │
    ▼
created ◄──────────────────────────────────────────────────────────────────────────┐
    │                                                                               │
    ▼                                                                               │
[Project role triggers] release_gate.evaluation_started                             │
    │                                                                               │
    ▼                                                                               │
release_gate_running ──────────────► release_gate_failed ──► (baseline stays in    │
    │                                                          created state;       │
    ▼                                                          can re-trigger)      │
release_gate_passed                                                                  │
    │                                                                               │
    ▼                                                                               │
approved (by Project Lead or Admin)                                                 │
    │                                                                               │
    ▼                                                                               │
released (by Quality Engineer)     ─────────────────────────────────────────────────┘
                                                                (re-evaluation loops
                                                                back to created)
    │
    ▼
[obsolete — admin only; terminal]
```

---

## 3. Release Gate States

| State | Description |
|-------|-------------|
| `not_evaluated` | Initial state; no release gate evaluation has been run for this baseline |
| `running` | Evaluation is in progress (async job executing) |
| `passed` | All required rules passed; no blocking issues |
| `failed` | One or more blocking issues found |
| `cancelled` | Evaluation cancelled by authorized user before completion |
| `stale` | A previous pass/fail result is no longer current because new blocking-relevant issues were raised |

The `ReleaseGateResult` record captures one evaluation run. A baseline may have multiple `ReleaseGateResult` records (one per evaluation run). The **current** gate result is the most recent one.

---

## 4. State Transitions

### 4.1 Transition: not_evaluated → running

**Trigger**: Any project role calls `POST /api/v1/projects/{project_id}/release-gate/run` with `baseline_id` in the JSON request body

**Pre-conditions**:
- Baseline is in state `created` (not yet approved or released)
- No release gate evaluation is currently `running` for this baseline
- Authorized role: Admin, Project Lead, Quality Engineer, or User assigned to the project

**Action**:
1. Create `ReleaseGateResult` record with `status = running`
2. Enqueue `release_gate_evaluation` async job
3. Emit `release_gate.evaluation_started` event

### 4.2 Transition: running → passed

**Trigger**: `release_gate_evaluation` job completes with no blocking issues

**Conditions**:
- All `release_gate` execution mode rules with `blocking: true` have passed
- No critical validation issues exist for any artefact in the baseline scope
- No open suspect states exist for any artefact in the baseline scope
- All mandatory artefact types (per active profile) are present in the baseline scope or have accepted tailoring decisions
- All required traceability is complete (per profile-mandatory relationship types)

**Action**:
1. Update `ReleaseGateResult.status = passed`
2. Record `evaluated_rules` count, `passed_rules` count
3. Emit `release_gate.completed` event with `result = pass`
4. Transition baseline `release_gate_status = passed`

### 4.3 Transition: running → failed

**Trigger**: `release_gate_evaluation` job completes with one or more blocking issues

**Conditions**: Any of:
- One or more critical validation issues with `blocking_contexts` including `release_gate`
- One or more open suspect states in baseline scope
- One or more mandatory artefact types absent from baseline scope without tailoring decision
- Required traceability links missing

**Action**:
1. Update `ReleaseGateResult.status = failed`
2. Record `blocking_issue_count`, `warning_issue_count`, `evaluated_rules`, list of blocking issue IDs
3. Emit `release_gate.completed` event with `result = fail`
4. Baseline `release_gate_status = failed`; baseline remains in `created` state (NOT moved to a terminal failure state — re-evaluation is possible)

### 4.4 Transition: running → cancelled

**Trigger**: Authorized user cancels a running evaluation job

**Authorized roles**: Quality Engineer, Project Lead, Admin

**Action**:
1. Cancel the ARQ job
2. Update `ReleaseGateResult.status = cancelled`
3. Baseline `release_gate_status` reverts to previous state (`not_evaluated` if first run, or the status from the previous completed run)

### 4.5 Transition: failed → running (Re-evaluation)

**Trigger**: Any project role calls the release-gate run endpoint again after a failed or stale evaluation

**Pre-conditions**:
- Baseline is in state `created`
- Previous gate evaluation is in state `failed` or `cancelled`
- One or more blocking issues have been resolved (not enforced as a pre-condition, but expected)

**Action**: Same as `not_evaluated → running`

**Policy**: Re-evaluation always creates a new `ReleaseGateResult` record. The baseline may accumulate multiple gate result records. The most recent is the authoritative current status.

### 4.6 Transition: passed → approved

**Trigger**: Project Lead or Admin calls `POST /api/v1/projects/{project_id}/baselines/{baseline_id}/approve`

**Pre-conditions**:
- Baseline `release_gate_status = passed`
- Authorized role: Project Lead, Admin

**Action**:
1. Set `baseline.status = approved`
2. Record `approved_by`, `approval_timestamp`
3. Emit `baseline.approved` event

### 4.7 Transition: approved → released

**Trigger**: Quality Engineer or Admin calls `POST /api/v1/projects/{project_id}/baselines/{baseline_id}/release`

**Pre-conditions**:
- Baseline `status = approved`
- Authorized role: Quality Engineer, Admin

**Action**:
1. Set `baseline.status = released`
2. Record `released_by`, `release_timestamp`
3. Emit `baseline.released` event
4. Trigger post-release suspect propagation evaluation

### 4.8 Transition: any → re-evaluation required after new issues

AAC-BASE-FR-040
If new validation issues are raised against artefacts in a baseline that has already passed its release gate (but is not yet released), the Quality Engineer shall be notified and the `release_gate_status` shall be reset to `stale`.

AAC-BASE-FR-041
A baseline with `release_gate_status = stale` shall require re-evaluation before it can be approved.

AAC-BASE-FR-042
The `stale` status is triggered by any `validation.issue_raised` event for an artefact in the baseline scope that has `severity = critical`.

---

## 5. Release Gate Evaluation Rule Set

The release gate evaluation job shall execute rules with `execution_modes` including `release_gate`.

### 5.1 Mandatory Rule Checks

In addition to the loaded catalog rules, the release gate shall perform these structural checks:

| Check | Condition For Failure |
|---|---|
| Mandatory artefact presence | Any mandatory artefact type (per active profile) has zero artefacts in scope with no accepted tailoring decision |
| Traceability completeness | Any SSR has no `verifies` relationship pointing to a TestResult with `verdict = pass` |
| Open suspects | Any artefact in scope has `SuspectState.status = open` |
| Unresolved defects | Any `DefectRecord` linked to an artefact in scope has `status != closed or wont_fix` |
| Incomplete tailoring | Any `TailoringDecision` for this baseline is missing `rationale`, `approver_id`, or `approval_timestamp` |
| Failed test results | Any `TestResult` in scope has `verdict = fail` with no linked `DefectRecord` (rule RULE-054) |

### 5.2 Blocking vs Warning Classification

| Severity | Blocking? | Description |
|---|---|---|
| `critical` | Yes (by default) | Prevents release gate from passing |
| `major` | Configurable per profile | Blocks by default for ASIL D; warning for lower profiles |
| `minor` | No (warning only) | Recorded but does not block |
| `info` | No | Informational only |

AAC-BASE-FR-050
The ASIL D profile default shall treat both `critical` and `major` severity issues as blocking at the release gate.

AAC-BASE-FR-051
Lower ASIL profiles (ASIL A, B, C) may configure `major` issues as non-blocking at the release gate via profile configuration.

AAC-BASE-FR-052
`critical` issues shall always be blocking regardless of profile configuration.

---

## 6. ReleaseGateResult Schema

```json
{
  "release_gate_result_id": "string",
  "baseline_id": "string",
  "project_id": "string",
  "evaluation_number": "integer (1-based, per baseline)",
  "triggered_by": "string (user_id)",
  "started_at": "ISO8601 timestamp",
  "completed_at": "ISO8601 timestamp or null",
  "status": "running | passed | failed | cancelled | stale",
  "result": "pass | fail | null (if not yet completed)",
  "evaluated_rules_count": "integer",
  "passed_rules_count": "integer",
  "blocking_issues": [
    {
      "issue_id": "string",
      "rule_id": "string",
      "severity": "string",
      "artefact_id": "string or null",
      "summary": "string"
    }
  ],
  "warning_issues": ["same structure as blocking_issues"],
  "mandatory_artefact_gaps": [
    {
      "artefact_type": "string",
      "required_by_profile": "string",
      "tailoring_decision_id": "string or null"
    }
  ],
  "open_suspect_states": [
    {
      "suspect_state_id": "string",
      "artefact_id": "string",
      "trigger_artefact_id": "string"
    }
  ],
  "job_id": "string"
}
```

---

## 7. API Endpoints For Release Gate

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/projects/{project_id}/release-gate/run` | Trigger release gate evaluation for `baseline_id` in request body | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results` | List all gate evaluation results for baseline | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/latest` | Get most recent gate result | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/{result_id}` | Get specific gate result | All project roles |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/approve` | Approve baseline (after gate passed) | Project Lead, Admin |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release` | Release baseline (after approved) | Quality Engineer, Admin |
