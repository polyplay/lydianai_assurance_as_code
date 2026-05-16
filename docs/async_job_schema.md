# Async Job Schema

## 1. Purpose

This document defines the asynchronous job model used by the back-end for long-running operations.

The web app and CLI shall use the same job model.

## 2. Job Scope

AAC-JOB-FR-001
The back-end shall represent long-running operations as jobs.

AAC-JOB-FR-002
The following operations shall be eligible for asynchronous execution:

- Sphinx import
- validation run
- baseline creation
- baseline comparison
- impact analysis
- repository scan
- report generation
- evidence bundle generation
- release-gate evaluation

AAC-JOB-FR-003
Jobs shall be project-scoped when the operation affects a project.

AAC-JOB-FR-004
Jobs shall be globally scoped only for administrative or system operations that are not tied to one project.

## 3. Job States

AAC-JOB-DR-001
A job shall use these states:

- `queued`
- `running`
- `waiting_for_user`
- `blocked`
- `completed`
- `failed`
- `cancelled`

AAC-JOB-DR-002
`waiting_for_user` shall be used when execution cannot continue until a user decision is supplied.

AAC-JOB-DR-003
`blocked` shall be used when execution cannot continue because another project-scoped lock or prerequisite prevents progress.

## 4. Job Schema

AAC-JOB-DR-010
A job shall conform to this logical schema:

```json
{
  "job_id": "JOB_000123",
  "project_id": "PROJ_001",
  "job_type": "baseline_create",
  "state": "running",
  "priority": "normal",
  "submitted_by": "USER_001",
  "submitted_at": "2026-04-12T10:30:00Z",
  "started_at": "2026-04-12T10:30:05Z",
  "completed_at": null,
  "correlation_id": "CORR_001",
  "causation_id": "AUDIT_001",
  "progress": {
    "percent": 45,
    "current_step": "eligibility_check_running",
    "total_steps": 5
  },
  "input_ref": {
    "resource_type": "BaselineRequest",
    "resource_id": "BASE_REQ_001"
  },
  "result_ref": null,
  "decision_requests": [],
  "locks": [],
  "messages": [],
  "error": null
}
```

## 5. Priority And Locking

AAC-JOB-FR-010
Baseline creation jobs shall acquire a project-scoped update lock before snapshot creation.

AAC-JOB-FR-011
While a baseline creation job holds the update lock, artefact and relationship update jobs for the same project shall be blocked.

AAC-JOB-FR-012
Read/query jobs for the same project shall remain allowed while a baseline job is running.

AAC-JOB-FR-013
The MVP shall not define a separate scheduler priority policy for read/query jobs during baseline creation.

AAC-JOB-FR-014
A project-scoped update lock shall not block operations for other projects.

## 6. Decision Requests

AAC-JOB-FR-020
Jobs may contain user decision requests.

AAC-JOB-FR-021
Version decisions in `ask_user` mode shall be represented as job decision requests.

AAC-JOB-DR-020
A decision request shall conform to this logical schema:

```json
{
  "decision_id": "DECISION_001",
  "decision_type": "version_update",
  "state": "pending",
  "required_role": "user",
  "artefact_id": "REQ_SW_001",
  "current_revision_id": "AR_REV_003",
  "proposed_change_ref": "IMPORT_ITEM_001",
  "options": [
    "accept_new_revision",
    "reject_keep_current"
  ],
  "created_at": "2026-04-12T10:31:00Z",
  "decided_by": null,
  "decided_at": null
}
```

## 7. Job API

AAC-JOB-IR-001
The API shall expose job status through:

```text
GET /api/v1/jobs/{job_id}
```

AAC-JOB-IR-002
The API shall expose project job listing through:

```text
GET /api/v1/projects/{project_id}/jobs
```

AAC-JOB-IR-003
The API shall allow cancellation of cancellable jobs through operation-specific endpoints or:

```text
POST /api/v1/jobs/{job_id}/cancel
```

AAC-JOB-IR-004
Only the original requester or Admin shall cancel a cancellable job.

## 8. Audit Requirements

AAC-JOB-FR-030
Job creation, start, completion, failure, cancellation, and user decision events shall create audit events.

AAC-JOB-FR-031
A job shall preserve correlation and causation IDs so that job activity can be traced back to the API command or domain event that caused it.
