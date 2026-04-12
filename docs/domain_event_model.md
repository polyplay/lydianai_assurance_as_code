# Domain Event Model Specification

## 1. Purpose

This document resolves blocker B4 identified in the implementation readiness assessment: the absence of a domain event model.

It defines the canonical domain events emitted by the Assurance-as-Code platform, their schemas, producers, consumers, and the trigger contexts in which they are dispatched.

---

## 2. Event Architecture

### 2.1 Event Bus Model

AAC-EVENT-AR-001
The MVP domain event bus shall be internal-only, implemented as an in-process synchronous publish-subscribe dispatcher within the back-end application process.

AAC-EVENT-AR-002
Event publication shall occur immediately after the database transaction that caused the event is committed. Events shall not be published if the originating transaction is rolled back.

AAC-EVENT-AR-003
Events that require long-running processing (validation, impact analysis, traceability update, suspect propagation) shall trigger the creation of an ARQ async job. The async job creation is the consumer action, not the processing itself.

AAC-EVENT-AR-004
Event consumers shall be registered at application startup. Consumer registration shall be declarative (decorator-based) and not require modification of the event dispatcher core.

AAC-EVENT-AR-005
Event publication failures shall be logged as errors but shall not cause the originating API request to fail. Events are advisory triggers; the canonical state is always the database.

AAC-EVENT-AR-006
The event bus is internal-only in the MVP. No external subscriber, webhook, or message broker integration is provided in MVP.

### 2.2 Event Schema

AAC-EVENT-DR-001
Every domain event shall conform to the following base schema:

```json
{
  "event_id": "EVT_<uuid4>",
  "event_type": "<string>",
  "occurred_at": "<ISO8601 timestamp>",
  "actor_id": "<user_id or 'system'>",
  "project_id": "<project_id or null if global>",
  "correlation_id": "<CORR_... from originating request or job>",
  "payload": {}
}
```

AAC-EVENT-DR-002
`event_type` values shall use dot-separated namespaced format: `<resource>.<action>` (e.g., `artefact.created`, `baseline.approved`).

AAC-EVENT-DR-003
`actor_id` shall be `"system"` for events triggered by automated processes (e.g., suspect propagation, scheduled validation).

AAC-EVENT-DR-004
`correlation_id` shall propagate from the originating API request through all downstream events and jobs it triggers.

---

## 3. Event Catalog

### 3.1 Artefact Events

#### `artefact.created`

Emitted when a new artefact is persisted to the database for the first time.

Producer: Repository layer on artefact INSERT.

Payload:
```json
{
  "artefact_id": "string",
  "artefact_type": "string",
  "revision_id": "string",
  "source": "api_direct | sphinx_import | system_generated",
  "import_run_id": "string or null"
}
```

Consumers:
- Validation service: enqueue `immediate` rule evaluation for new artefact
- Traceability service: register artefact in traceability index

#### `artefact.revised`

Emitted when a new artefact revision is created (content change accepted).

Producer: Repository layer on new revision INSERT.

Payload:
```json
{
  "artefact_id": "string",
  "artefact_type": "string",
  "previous_revision_id": "string",
  "new_revision_id": "string",
  "changed_fields": ["list of field names that changed"],
  "source": "api_direct | sphinx_import",
  "import_run_id": "string or null"
}
```

Consumers:
- Validation service: enqueue `immediate` rule evaluation for revised artefact
- Impact service: enqueue impact analysis if artefact is released or in a baseline
- Suspect propagation service: enqueue suspect propagation if artefact is released

#### `artefact.status_changed`

Emitted when an artefact's lifecycle status changes (e.g., draft → under_review → reviewed → approved → released → obsolete).

Producer: Artefact service on status field UPDATE.

Payload:
```json
{
  "artefact_id": "string",
  "artefact_type": "string",
  "previous_status": "string",
  "new_status": "string",
  "actor_id": "string"
}
```

Consumers:
- Validation service: re-evaluate rules that apply to status transitions
- Suspect propagation service: if new_status == "released", trigger downstream suspect check
- Audit service: create AuditEvent record

#### `artefact.deleted`

Emitted when an artefact is soft-deleted (lifecycle status → obsolete/deleted).

Producer: Artefact service on soft-delete operation.

Payload:
```json
{
  "artefact_id": "string",
  "artefact_type": "string",
  "final_revision_id": "string"
}
```

Consumers:
- Validation service: cancel pending immediate validation jobs for artefact
- Traceability service: remove artefact from active traceability index
- Suspect propagation service: clear any open suspect states owned by this artefact

---

### 3.2 Relationship Events

#### `relationship.created`

Emitted when a new relationship is persisted.

Payload:
```json
{
  "relationship_id": "string",
  "relationship_type": "string",
  "source_artefact_id": "string",
  "target_artefact_id": "string"
}
```

Consumers:
- Validation service: enqueue `immediate` rules for both source and target artefacts
- Traceability service: update traceability index
- Suspect propagation service: check if new relationship creates a suspect propagation path

#### `relationship.deleted`

Emitted when a relationship is soft-deleted.

Payload:
```json
{
  "relationship_id": "string",
  "relationship_type": "string",
  "source_artefact_id": "string",
  "target_artefact_id": "string"
}
```

Consumers:
- Validation service: re-evaluate rules that required this relationship
- Traceability service: update traceability index
- Suspect propagation service: check for newly unresolved suspects

---

### 3.3 Import Events

#### `import.started`

Emitted when an import run job is enqueued and begins.

Payload:
```json
{
  "import_run_id": "string",
  "project_id": "string",
  "source_document": "string",
  "artefact_count_submitted": "integer"
}
```

Consumers: Audit service.

#### `import.completed`

Emitted when an import run job finishes successfully.

Payload:
```json
{
  "import_run_id": "string",
  "project_id": "string",
  "artefacts_created": "integer",
  "artefacts_revised": "integer",
  "artefacts_unchanged": "integer",
  "artefacts_deleted": "integer",
  "conflicts_detected": "integer",
  "conflicts_requiring_decision": "integer"
}
```

Consumers:
- Validation service: enqueue project-scope `import` rule execution
- Traceability service: refresh traceability index for affected artefacts
- Audit service: create AuditEvent record

#### `import.decision_required`

Emitted when an import run pauses for user decision (ask_user mode, conflict detected).

Payload:
```json
{
  "import_run_id": "string",
  "job_id": "string",
  "pending_decisions": [
    {
      "decision_id": "string",
      "artefact_id": "string",
      "artefact_type": "string",
      "conflict_summary": "string",
      "options": ["accept_new_version", "reject_keep_current"]
    }
  ]
}
```

Consumers: Job service (transition job to `waiting_for_user` state).

#### `import.failed`

Emitted when an import run fails with an unrecoverable error.

Payload:
```json
{
  "import_run_id": "string",
  "error_type": "string",
  "error_message": "string",
  "partial_commit": "boolean"
}
```

Consumers: Audit service; if partial_commit is true, suspect propagation service shall evaluate affected artefacts.

---

### 3.4 Validation Events

#### `validation.run_completed`

Emitted when a validation run job finishes.

Payload:
```json
{
  "validation_run_id": "string",
  "project_id": "string",
  "scope": "project | artefact | baseline",
  "scope_id": "string",
  "critical_issues": "integer",
  "major_issues": "integer",
  "minor_issues": "integer",
  "info_issues": "integer"
}
```

Consumers: Audit service; baseline service (if validation was triggered by baseline creation).

#### `validation.issue_raised`

Emitted when a new validation issue is persisted.

Payload:
```json
{
  "issue_id": "string",
  "rule_id": "string",
  "severity": "critical | major | minor | info",
  "artefact_id": "string or null",
  "relationship_id": "string or null",
  "blocking_contexts": ["list of contexts this issue blocks"]
}
```

Consumers: Audit service.

#### `validation.issue_resolved`

Emitted when a validation issue transitions to resolved state.

Payload:
```json
{
  "issue_id": "string",
  "rule_id": "string",
  "resolution_method": "fixed | suppressed | tailored_away",
  "resolved_by": "string"
}
```

Consumers: Audit service; baseline service (may unblock a pending baseline).

---

### 3.5 Baseline Events

#### `baseline.creation_requested`

Emitted when a Project Lead or Admin requests baseline creation.

Payload:
```json
{
  "baseline_id": "string",
  "project_id": "string",
  "requested_by": "string",
  "baseline_name": "string",
  "baseline_type": "string"
}
```

Consumers: Baseline service (enqueue baseline creation job).

#### `baseline.lock_acquired`

Emitted when the project update lock is acquired for baseline creation.

Payload:
```json
{
  "baseline_id": "string",
  "project_id": "string",
  "lock_acquired_at": "ISO8601 timestamp"
}
```

Consumers: Audit service.

#### `baseline.created`

Emitted when a baseline snapshot is successfully created.

Payload:
```json
{
  "baseline_id": "string",
  "project_id": "string",
  "artefact_revision_count": "integer",
  "relationship_revision_count": "integer",
  "eligibility_passed": "boolean",
  "blocking_issue_count": "integer"
}
```

Consumers: Audit service; report service (may trigger automatic baseline report generation).

#### `baseline.approved`

Emitted when a baseline is approved by authorized role.

Payload:
```json
{
  "baseline_id": "string",
  "approved_by": "string",
  "approval_timestamp": "ISO8601 timestamp"
}
```

Consumers: Audit service.

#### `baseline.released`

Emitted when a baseline is released (final state).

Payload:
```json
{
  "baseline_id": "string",
  "released_by": "string",
  "release_timestamp": "ISO8601 timestamp"
}
```

Consumers:
- Audit service
- Suspect propagation service: evaluate post-release suspect states

---

### 3.6 Release Gate Events

#### `release_gate.evaluation_started`

Emitted when release gate evaluation begins.

Payload:
```json
{
  "release_gate_result_id": "string",
  "baseline_id": "string",
  "triggered_by": "string"
}
```

Consumers: Audit service.

#### `release_gate.completed`

Emitted when release gate evaluation finishes.

Payload:
```json
{
  "release_gate_result_id": "string",
  "baseline_id": "string",
  "result": "pass | fail",
  "blocking_issue_count": "integer",
  "warning_issue_count": "integer"
}
```

Consumers: Audit service; baseline service (gate result stored on baseline).

---

### 3.7 Suspect Propagation Events

#### `suspect.propagated`

Emitted when an artefact enters suspect state due to upstream change.

Payload:
```json
{
  "suspect_state_id": "string",
  "artefact_id": "string",
  "artefact_type": "string",
  "trigger_artefact_id": "string",
  "trigger_revision_id": "string",
  "propagation_path": ["list of artefact IDs in propagation chain"]
}
```

Consumers:
- Audit service
- Validation service: re-evaluate any rules that check for unresolved suspects

#### `suspect.cleared`

Emitted when an artefact's suspect state is cleared.

Payload:
```json
{
  "suspect_state_id": "string",
  "artefact_id": "string",
  "cleared_by": "string",
  "clearing_method": "reviewed_and_accepted | re_verified | not_applicable",
  "evidence_refs": ["list of evidence reference IDs"]
}
```

Consumers: Audit service; baseline service (may unblock pending baseline).

---

### 3.8 Impact Analysis Events

#### `impact_analysis.completed`

Emitted when an impact analysis job finishes.

Payload:
```json
{
  "impact_analysis_run_id": "string",
  "trigger_artefact_id": "string",
  "affected_artefact_count": "integer",
  "affected_relationship_count": "integer",
  "new_suspect_states_created": "integer"
}
```

Consumers: Audit service.

---

### 3.9 Audit Events

The `AuditEvent` record is created by the audit consumer in response to all events listed above. This is distinct from domain events: domain events are transient in-process signals; `AuditEvent` records are the persistent, append-only audit trail stored in the database.

#### Audit Event Schema

```json
{
  "audit_event_id": "string",
  "event_type": "string (domain event type that triggered this audit entry)",
  "project_id": "string or null",
  "actor_id": "string",
  "occurred_at": "ISO8601 timestamp",
  "resource_type": "string",
  "resource_id": "string",
  "previous_state": "string or null",
  "new_state": "string or null",
  "summary": "string",
  "correlation_id": "string",
  "metadata": {}
}
```

---

## 4. Event-To-Async-Job Trigger Map

The following table defines which domain events trigger the creation of which async jobs:

| Domain Event | Async Job Type | Conditions |
|---|---|---|
| `artefact.created` | `validation_run` (scope=artefact) | execution_mode includes `immediate` |
| `artefact.revised` | `validation_run` (scope=artefact) | execution_mode includes `immediate` |
| `artefact.revised` | `impact_analysis` | artefact was in a released baseline |
| `artefact.status_changed` (→ released) | `impact_analysis` | always |
| `relationship.created` | `validation_run` (scope=relationship) | execution_mode includes `immediate` |
| `relationship.deleted` | `validation_run` (scope=relationship) | execution_mode includes `immediate` |
| `import.completed` | `validation_run` (scope=project, mode=import) | always |
| `import.completed` | `impact_analysis` | if any revised artefacts were in released baselines |
| `baseline.creation_requested` | `baseline_creation` | always |
| `release_gate.evaluation_started` | `release_gate_evaluation` | always |
| `suspect.propagated` | `validation_run` (scope=artefact) | rule AAC-RULE-RULE-080 re-check |

---

## 5. Event Ordering And Idempotency

AAC-EVENT-FR-001
Domain events shall be published after database transaction commit. An event shall never be published for a transaction that was rolled back.

AAC-EVENT-FR-002
Event consumers that create async jobs shall be idempotent: creating the same job type for the same resource within a configurable deduplication window (default: 5 seconds) shall not create a duplicate job.

AAC-EVENT-FR-003
The event dispatcher shall not guarantee ordering between events published in the same transaction. Consumers shall not assume event ordering.

AAC-EVENT-FR-004
Consumer failures shall be logged but shall not prevent other consumers from receiving the same event.
