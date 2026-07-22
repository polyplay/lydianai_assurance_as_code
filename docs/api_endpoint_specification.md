# API Endpoint Specification

## 1. Purpose

This document defines the MVP HTTP API endpoint paths, methods, and status reporting expectations.

All endpoints are project-scoped unless explicitly global.

## 2. General API Rules

AAC-API-IR-100
The API base path shall be `/api/v1`.

AAC-API-IR-101
Request and response bodies shall use JSON.

AAC-API-IR-102
All mutable commands shall return operation status information.

AAC-API-IR-103
GET responses shall include the content needed by the front-end for viewing and modification.

AAC-API-IR-104
Successful responses shall use the following envelope:

```json
{
  "status": "success|accepted|requires_user_decision",
  "request_id": "REQ_...",
  "correlation_id": "CORR_...",
  "messages": [],
  "data": {}
}
```

Error responses shall use:

```json
{
  "status": "error",
  "request_id": "REQ_...",
  "correlation_id": "CORR_...",
  "error": {
    "code": "stable_machine_code",
    "message": "sanitized human-readable message",
    "details": {}
  }
}
```

Error responses shall not contain stack traces, SQL text, credentials, internal
paths, or database structure.

AAC-API-IR-105
State-changing endpoints shall include revision, audit, validation, and job references where applicable.

AAC-API-IR-106
Every resource family shall expose a status endpoint or include status data in its read response.

AAC-API-IR-107
Status data shall include lifecycle state, validation summary, current revision, suspect state, baseline association where applicable, and pending job references where applicable.

AAC-API-IR-108
`All project roles` means Admin, Project Lead, Quality Engineer, and User when assigned to the project.

## 2.1 JSON Request And Response Schema Configuration

AAC-API-IR-110
Back-end API request and response payloads shall use JSON for MVP.

AAC-API-IR-111
The front-end may render JSON-backed data through a different visual representation, but the back-end contract shall remain JSON.

AAC-API-IR-112
The project configuration shall define the enabled request and response fields for each artefact type.

AAC-API-IR-113
By default, all defined properties and attributes of an artefact type shall be enabled in API request and response schemas.

AAC-API-IR-114
Project configuration may tailor down enabled properties and attributes for a given artefact type.

AAC-API-IR-115
Tailoring down API-visible fields shall not remove mandatory canonical fields required for identity, versioning, audit, validation, or baseline integrity.

AAC-API-IR-116
If a field is disabled for front-end/API authoring but required internally, the back-end shall either derive it, preserve its existing value, or reject operations that would make the resource invalid.

AAC-API-IR-117
The API shall expose the active schema for a project and artefact type.

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/schemas` | List active API schemas | All project roles |
| GET | `/api/v1/projects/{project_id}/schemas/{artefact_type}` | Get active schema for artefact type | All project roles |
| PUT | `/api/v1/projects/{project_id}/schemas/{artefact_type}` | Tailor active schema | Admin |

AAC-API-IR-118
An active artefact schema response shall include:

```json
{
  "artefact_type": "SoftwareRequirement",
  "schema_version": "1.0",
  "enabled_fields": [
    "id",
    "title",
    "description",
    "status",
    "owner",
    "asil_level",
    "rationale",
    "acceptance_criteria",
    "verification_intent"
  ],
  "disabled_fields": [],
  "mandatory_fields": [
    "id",
    "title",
    "status",
    "asil_level"
  ],
  "readonly_fields": [
    "current_revision_id",
    "created_at",
    "updated_at"
  ],
  "fields": [
    {
      "name": "asil_level",
      "label": "Asil Level",
      "data_type": "string",
      "widget": "select",
      "required": true,
      "readonly": false,
      "allowed_values": ["QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"],
      "item_type": null,
      "help": "Select the applicable automotive safety integrity level."
    }
  ]
}
```

The `fields` collection is backward-compatible presentation metadata for the
same canonical fields. It shall not introduce, remove, or validate payload
properties independently of the canonical schema registry.

## 3. Authentication And Users

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/auth/login` | Start authenticated session or obtain token | Admin, Project Lead, Quality Engineer, User |
| POST | `/api/v1/auth/logout` | End session | Admin, Project Lead, Quality Engineer, User |
| GET | `/api/v1/users/me` | Get current user and roles | Admin, Project Lead, Quality Engineer, User |
| GET | `/api/v1/users` | List users | Admin |
| POST | `/api/v1/users` | Create user | Admin |
| PUT | `/api/v1/users/{user_id}` | Update user/roles | Admin |
| PUT | `/api/v1/users/{user_id}/deactivate` | Deactivate user account | Admin |
| POST | `/api/v1/users/{user_id}/password-reset` | Reset user password | Admin |
| POST | `/api/v1/users/me/password` | Change own password | Admin, Project Lead, Quality Engineer, User |

AAC-API-IR-120
The MVP authentication API shall use username and password credentials.

AAC-API-IR-121
Only Admin shall create user accounts.

AAC-API-IR-122
Only Admin shall assign or modify roles.

AAC-API-IR-123
Password values shall be accepted only on account creation, password reset, or password change endpoints and shall not be returned by any API response.

## 4. Projects

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects` | List visible projects | All |
| POST | `/api/v1/projects` | Create project | Admin |
| GET | `/api/v1/projects/{project_id}` | Get project details | All project roles |
| PUT | `/api/v1/projects/{project_id}` | Update project metadata | Admin, Project Lead |
| POST | `/api/v1/projects/{project_id}/archive` | Archive project | Admin |
| DELETE | `/api/v1/projects/{project_id}` | Soft-delete project | Admin |
| GET | `/api/v1/projects/{project_id}/status` | Get project assurance status | All project roles |
| GET | `/api/v1/projects/{project_id}/workspace` | Get effective roles, capabilities, actionable-work summaries, active work, and release readiness | All project roles |
| GET | `/api/v1/projects/{project_id}/members` | List project members | All project roles |
| POST | `/api/v1/projects/{project_id}/members` | Add project member | Admin, Project Lead |
| DELETE | `/api/v1/projects/{project_id}/members/{user_id}` | Remove project member | Admin, Project Lead |

AAC-API-IR-131
The workspace projection shall be read-only. Named capabilities and resource
`allowed_actions` are presentation metadata derived from the same role,
ownership, and lifecycle constraints enforced by command endpoints. Omission or
presence of an action shall not bypass or replace command authorization.

AAC-API-IR-130
`POST /api/v1/projects` shall accept an optional `assurance_configuration` object. If supplied, the back-end shall create a project-specific derived assurance profile and make it the active profile.

```json
{
  "project_key": "SW_ITEM_01",
  "name": "Software item assurance",
  "description": "Project scope",
  "active_profile_id": "ASIL_B_DEFAULT",
  "assurance_configuration": {
    "project_type": "software_system",
    "asil_level": "ASIL_B",
    "aspice_model": "ASPICE_PAM_4_0",
    "aspice_default_capability_level": 2,
    "aspice_scoped_processes": ["SWE.1", "SWE.2", "SWE.3", "SWE.4", "SWE.5", "SWE.6", "SUP.8", "SUP.9", "SUP.10"],
    "aspice_process_overrides": {
      "SUP.8": 3
    },
    "r155_applicable": false,
    "r156_applicable": false,
    "test_scope": ["unit", "integration", "software_qualification"],
    "visibility_policy": "relevant_first"
  }
}
```

## 5. Project Configuration And Profiles

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/config` | Read project config | All project roles |
| PUT | `/api/v1/projects/{project_id}/config` | Update project config | Admin |
| GET | `/api/v1/projects/{project_id}/profiles` | List profiles | All project roles |
| POST | `/api/v1/projects/{project_id}/profiles` | Create project profile | Admin |
| GET | `/api/v1/projects/{project_id}/profiles/{profile_id}` | Get profile | All project roles |
| PUT | `/api/v1/projects/{project_id}/profiles/{profile_id}` | Update profile | Admin |
| POST | `/api/v1/projects/{project_id}/profiles/{profile_id}/evaluate` | Evaluate profile applicability | Admin, Project Lead, Quality Engineer, User |
| POST | `/api/v1/projects/{project_id}/tailoring-decisions` | Request/make tailoring decision | Project Lead, Admin |
| GET | `/api/v1/projects/{project_id}/tailoring-decisions` | List tailoring decisions | All project roles |
| POST | `/api/v1/projects/{project_id}/tailoring-decisions/{tailoring_decision_id}/revoke` | Revoke tailoring decision | Admin |
| GET | `/api/v1/projects/{project_id}/standards-references` | List standards references | All project roles |
| POST | `/api/v1/projects/{project_id}/standards-references` | Create standards reference | Admin |
| PUT | `/api/v1/projects/{project_id}/standards-references/{standards_reference_id}` | Update standards reference/review status | Admin |
| GET | `/api/v1/projects/{project_id}/standards-mappings` | Query artefact/rule standards mappings | All project roles |
| PUT | `/api/v1/projects/{project_id}/standards-mappings` | Update artefact/rule standards mappings | Admin |

AAC-API-IR-150
`GET /api/v1/projects/{project_id}/config` shall return the current `assurance_configuration` in addition to baseline, validation, and reporting policy.

AAC-API-IR-151
`PUT /api/v1/projects/{project_id}/config` shall accept `assurance_configuration`. Updating it shall regenerate derived artefact applicability, rule policy, and profile payload, then record an audit event. If the update changes `aspice_default_capability_level`, `aspice_scoped_processes`, or the derived expected capability target of any configured in-scope ASPICE process, the request shall include `tailoring_rationale` and at least one `tailoring_evidence_refs` entry. The service shall record approved tailoring decisions for each ASPICE process-scope or process-capability change.

AAC-API-IR-152
`POST /api/v1/projects/{project_id}/profiles/{profile_id}/evaluate` shall return `visible_artefact_types`, `mandatory_artefact_types`, `conditional_artefact_types`, `optional_artefact_types`, `not_applicable_artefact_types`, `enabled_rules`, `disabled_rules`, and `assurance_configuration`.

## 6. Artefacts

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/artefacts` | List/search artefacts | All project roles |
| POST | `/api/v1/projects/{project_id}/artefacts` | Create artefact | Admin, Project Lead, Quality Engineer, User |
| GET | `/api/v1/projects/{project_id}/artefacts/{artefact_id}` | Get artefact content | All project roles |
| PUT | `/api/v1/projects/{project_id}/artefacts/{artefact_id}` | Update artefact | Admin, Project Lead, Quality Engineer, User |
| DELETE | `/api/v1/projects/{project_id}/artefacts/{artefact_id}` | Soft-delete/obsolete artefact | Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/submit-for-review` | Submit artefact for review | Owner, Quality Engineer, Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/mark-reviewed` | Mark artefact reviewed | Project Lead, Quality Engineer, Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/reject` | Reject artefact review | Project Lead, Quality Engineer, Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/approve` | Approve artefact | Project Lead, Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/release` | Release artefact | Quality Engineer, Admin |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/status` | Change lifecycle status | Admin, Project Lead, Quality Engineer |
| GET | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/status` | Get artefact status | All project roles |

For `PUT` on a released artefact, the permitted roles narrow to Quality Engineer
and Admin. Other roles receive `403`.

## 7. Artefact Revisions

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/revisions` | List revisions | All project roles |
| GET | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/revisions/{revision_id}` | Get revision content | All project roles |
| POST | `/api/v1/projects/{project_id}/artefacts/{artefact_id}/compare` | Compare revisions | All project roles |

## 8. Relationships

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/relationships` | List/search relationships | All project roles |
| POST | `/api/v1/projects/{project_id}/relationships` | Create relationship | Admin, Project Lead, Quality Engineer, User |
| GET | `/api/v1/projects/{project_id}/relationships/{relationship_id}` | Get relationship | All project roles |
| PUT | `/api/v1/projects/{project_id}/relationships/{relationship_id}` | Update relationship | Admin, Project Lead, Quality Engineer, User |
| DELETE | `/api/v1/projects/{project_id}/relationships/{relationship_id}` | Soft-delete relationship | Admin |
| GET | `/api/v1/projects/{project_id}/relationships/{relationship_id}/revisions` | List relationship revisions | All project roles |

## 9. Imports

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/projects/{project_id}/imports/sphinx` | Start Sphinx import | Admin, Project Lead, Quality Engineer, User |
| GET | `/api/v1/projects/{project_id}/imports` | List import runs | All project roles |
| GET | `/api/v1/projects/{project_id}/imports/{import_run_id}` | Get import status/details | All project roles |
| POST | `/api/v1/projects/{project_id}/imports/{import_run_id}/decisions` | Submit version decisions | Admin, Project Lead, Quality Engineer, User |
| POST | `/api/v1/projects/{project_id}/imports/{import_run_id}/cancel` | Cancel import | Original requester, Admin |

## 10. Validation And Rules

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/projects/{project_id}/validation/run` | Run validation | All project roles |
| GET | `/api/v1/projects/{project_id}/validation/status` | Get validation status | All project roles |
| GET | `/api/v1/projects/{project_id}/validation/issues` | List issues | All project roles |
| GET | `/api/v1/projects/{project_id}/validation/issues/{issue_id}` | Get issue | All project roles |
| POST | `/api/v1/projects/{project_id}/validation/issues/{issue_id}/suppress` | Suppress issue | Admin |
| POST | `/api/v1/projects/{project_id}/validation/issues/{issue_id}/reopen` | Reopen suppressed issue | Admin |
| GET | `/api/v1/projects/{project_id}/rules` | Get rule catalog | All project roles |

AAC-API-IR-260
`POST /api/v1/projects/{project_id}/validation/run` shall accept an optional JSON body containing validation scope and mode. If omitted, the endpoint shall run project-level baseline validation.

```json
{
  "type": "project",
  "mode": "baseline"
}
```

## 11. Traceability And Impact

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/trace/{artefact_id}` | Get trace for artefact | All project roles |
| GET | `/api/v1/projects/{project_id}/trace/{artefact_id}/forward` | Get forward trace | All project roles |
| GET | `/api/v1/projects/{project_id}/trace/{artefact_id}/backward` | Get backward trace | All project roles |
| GET | `/api/v1/projects/{project_id}/traceability-matrix` | Get trace matrix | All project roles |
| POST | `/api/v1/projects/{project_id}/impact` | Run impact analysis | All project roles |
| GET | `/api/v1/projects/{project_id}/impact/{impact_id}` | Get impact result | All project roles |
| GET | `/api/v1/projects/{project_id}/suspect-states` | List suspect states | All project roles |
| POST | `/api/v1/projects/{project_id}/suspect-states/{suspect_id}/clear` | Clear suspect state | Project Lead, Quality Engineer, Admin |

## 12. Baselines

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/projects/{project_id}/baselines` | Request baseline creation | Project Lead, Admin |
| GET | `/api/v1/projects/{project_id}/baselines` | List baselines | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}` | Get baseline | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/status` | Get baseline status | All project roles |
| POST | `/api/v1/projects/{project_id}/baselines/compare` | Compare baselines | All project roles |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/cancel` | Cancel baseline creation | Project Lead, Admin |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/approve` | Approve baseline | Project Lead, Admin |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release` | Release baseline | Quality Engineer, Admin |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/obsolete` | Mark baseline obsolete | Admin |

## 13. Test Results, Evidence, Reports

| Method | Path | Purpose | Roles |
|---|---|---|---|
| POST | `/api/v1/projects/{project_id}/test-results/import` | Import results | All project roles |
| GET | `/api/v1/projects/{project_id}/test-results` | List results | All project roles |
| POST | `/api/v1/projects/{project_id}/evidence` | Create evidence reference | All project roles |
| GET | `/api/v1/projects/{project_id}/evidence/{evidence_id}` | Get evidence reference | All project roles |
| POST | `/api/v1/projects/{project_id}/reports` | Generate report | All project roles |
| GET | `/api/v1/projects/{project_id}/reports` | List reports | All project roles |
| GET | `/api/v1/projects/{project_id}/reports/{report_id}` | Get report metadata/content link | All project roles |
| DELETE | `/api/v1/projects/{project_id}/reports/{report_id}` | Soft-delete generated report | Admin, Quality Engineer |
| POST | `/api/v1/projects/{project_id}/release-gate/run` | Run release gate | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results` | List release-gate results for baseline | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/latest` | Get latest release-gate result | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/{result_id}` | Get release-gate result | All project roles |

## 14. Repository Integrations

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/projects/{project_id}/repo-connectors` | List configured repository connectors | All project roles |
| POST | `/api/v1/projects/{project_id}/repo-connectors` | Create GitHub repository connector | Admin |
| GET | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Get repository connector metadata | All project roles |
| PUT | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Update connector metadata or rotate secrets | Admin |
| DELETE | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Soft-delete repository connector | Admin |
| POST | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/test` | Test GitHub connectivity | Admin |
| GET | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/status` | Read repository commit, checks, and statuses | All project roles |
| POST | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan` | Trigger manual repository scan | Admin, Project Lead |
| GET | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scans/{scan_id}` | Get repository scan status | All project roles |
| GET | `/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals` | List repository approvals published for a baseline | All project roles |
| POST | `/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals` | Publish release approval to repository checks/statuses | Admin, Project Lead, Quality Engineer |
| GET | `/api/v1/projects/{project_id}/repo-checks/{check_id}` | Get repository approval/check publication status | All project roles |
| POST | `/api/v1/integrations/github/webhook/{connector_id}` | Receive GitHub webhook delivery | System |

The detailed connector schemas, mapping file schema, state machines, GitHub check semantics, and deployment acceptance criteria are controlled by [Repository Integration Contract](repository_integration_contract.md).

## 15. Jobs And Audit

| Method | Path | Purpose | Roles |
|---|---|---|---|
| GET | `/api/v1/jobs/{job_id}` | Get async job status | Original requester, Admin |
| POST | `/api/v1/jobs/{job_id}/cancel` | Cancel cancellable job | Original requester, Admin |
| GET | `/api/v1/projects/{project_id}/jobs` | List project jobs | All project roles |
| GET | `/api/v1/projects/{project_id}/audit-events` | Query audit events | Admin, Project Lead, Quality Engineer |

Project job listings shall redact input, decision, and error detail unless the
caller is the original requester or Admin.
