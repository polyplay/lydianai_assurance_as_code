# Authorization Matrix

## 1. Purpose

This document resolves blocker B2 identified in the implementation readiness assessment: the absence of a per-operation authorization enforcement model.

It defines the required role, pre-conditions, resulting state, and audit event for every state-changing operation in the Assurance-as-Code platform.

---

## 2. Role Definitions

Per `specification_refinement_decisions.md` DEC-AUTHZ-001 through DEC-AUTHZ-009:

| Role | Description |
|------|-------------|
| `Admin` | Full configuration access; can delete any artefact (soft); can create users and assign roles |
| `Project Lead` | Can create and approve baselines; can approve tailoring decisions |
| `Quality Engineer` | Can release artefacts and baselines; can trigger release gate evaluation |
| `User` | Standard operational access: create/edit artefacts, run imports, validate, trace, query |

All roles can be assigned project-scope (membership) or globally (Admin only is global).

There is no general role hierarchy between Project Lead and Quality Engineer. Admin has global administrative privileges. Project Lead and Quality Engineer have distinct controlled responsibilities.

Global roles are read only from the user account's global-role assignment.
Project memberships from other projects shall not be included in global roles
and shall not authorize access to the selected project. Effective project roles
are the union of true global roles and memberships for that project only.

---

## 3. Authorization Convention

For each API operation:
- **Required Role**: exact permitted role set for the operation
- **Pre-condition**: database/state condition that must hold before the operation is attempted
- **Post-state**: what changes in the database after the operation
- **Audit Event**: the AuditEvent.event_type recorded
- **Scope**: `project` (user must be a member of the project) or `global` (Admin only)

A 403 Forbidden response is returned when the caller's role is insufficient.
A 409 Conflict response is returned when a pre-condition is not met.

---

## 4. User And Role Management Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event | Scope |
|-----------|----------|---------------|---------------|------------|-------------|-------|
| Create user account | POST /api/v1/users | Admin | username unique | user created, inactive until password set | user.created | global |
| Assign/change user role | PUT /api/v1/users/{id} | Admin | user exists | role updated | user.role_changed | global |
| Add user to project | POST /api/v1/projects/{id}/members | Admin or Project Lead | user exists; not already member | membership created | project.member_added | project |
| Remove user from project | DELETE /api/v1/projects/{id}/members/{user_id} | Admin or Project Lead | membership exists | membership removed | project.member_removed | project |
| Deactivate user account | PUT /api/v1/users/{id}/deactivate | Admin | user exists; not last admin | user deactivated | user.deactivated | global |

---

## 5. Project Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event | Scope |
|-----------|----------|---------------|---------------|------------|-------------|-------|
| Create project | POST /api/v1/projects | Admin | project_id unique | project created | project.created | global |
| Update project metadata | PUT /api/v1/projects/{id} | Admin or Project Lead | project exists; not locked | project updated | project.updated | project |
| Configure project profile | PUT /api/v1/projects/{id}/config | Admin | project exists | configuration updated | project.configuration_changed | project |
| Archive project | POST /api/v1/projects/{id}/archive | Admin | project exists; no active jobs | project archived | project.archived | global |
| Delete project (soft) | DELETE /api/v1/projects/{id} | Admin | project exists; no released baselines | project marked deleted | project.deleted | global |

---

## 6. Artefact Operations

### 6.1 Create And Edit

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Create artefact (direct) | POST /api/v1/projects/{id}/artefacts | User, Project Lead, Quality Engineer, or Admin | source_object_id unique in project | artefact created (draft), revision created | artefact.created |
| Update artefact fields | PUT /api/v1/projects/{id}/artefacts/{art_id} | User, Project Lead, Quality Engineer, or Admin | artefact exists; not in released or obsolete state; no baseline lock active | new revision created or fields updated | artefact.revised |
| Update released artefact | PUT /api/v1/projects/{id}/artefacts/{art_id} | Quality Engineer or Admin | artefact exists; status=released; no baseline lock active | new revision created; impact analysis and suspect propagation triggered | artefact.revised |

### 6.2 Lifecycle Status Transitions

| Transition | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| draft → under_review | POST .../artefacts/{id}/submit-for-review | User (own artefact), Quality Engineer, or Admin | artefact.status = draft; required metadata present | status = under_review | artefact.status_changed |
| under_review → reviewed | POST .../artefacts/{id}/mark-reviewed | Quality Engineer, Project Lead, or Admin | artefact.status = under_review | status = reviewed; reviewer recorded | artefact.status_changed |
| under_review → rejected | POST .../artefacts/{id}/reject | Quality Engineer, Project Lead, or Admin | artefact.status = under_review | status = draft; rejection reason recorded | artefact.status_changed |
| reviewed → approved | POST .../artefacts/{id}/approve | Project Lead or Admin | artefact.status = reviewed | status = approved; approver recorded | artefact.status_changed |
| approved → released | POST .../artefacts/{id}/release | Quality Engineer or Admin | artefact.status = approved; no open critical validation issues for this artefact | status = released; suspect propagation evaluated | artefact.status_changed |
| any → obsolete (soft delete) | DELETE /api/v1/projects/{id}/artefacts/{art_id} | Admin | baseline lock not active | status = obsolete | artefact.deleted |
| released → obsolete | DELETE /api/v1/projects/{id}/artefacts/{art_id} | Admin only | — | status = obsolete; all relationships soft-deleted; suspect propagation for dependents | artefact.deleted |

---

## 7. Relationship Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Create relationship | POST /api/v1/projects/{id}/relationships | User, Project Lead, Quality Engineer, or Admin | source and target artefacts exist; relationship type allowed | relationship created | relationship.created |
| Update relationship | PUT /api/v1/projects/{id}/relationships/{rel_id} | User, Project Lead, Quality Engineer, or Admin | relationship exists; no baseline lock active | relationship revision created | relationship.revised |
| Delete relationship | DELETE /api/v1/projects/{id}/relationships/{rel_id} | Admin | relationship exists; no baseline lock active | relationship soft-deleted; suspect propagation triggered where applicable | relationship.deleted |

---

## 8. Import Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Submit Sphinx import | POST /api/v1/projects/{id}/imports/sphinx | User, Project Lead, Quality Engineer, or Admin | project exists; no active import job for same source document | import job enqueued | import.started |
| Submit import decision (ask_user mode) | POST /api/v1/projects/{id}/imports/{import_id}/decisions | Original submitter, Quality Engineer, or Admin | import job in waiting_for_user state; decision_id valid; actor authorized for resulting artefact operation | decision recorded; job resumes | import.decision_submitted |
| Cancel import | POST /api/v1/projects/{id}/imports/{import_id}/cancel | User (own) or Admin | import job in queued or running state | job cancelled | import.cancelled |

---

## 9. Validation Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Trigger validation run | POST /api/v1/projects/{id}/validation/run | User, Project Lead, Quality Engineer, or Admin | project exists; no active validation run for same scope | validation job enqueued | validation.run_started |
| Suppress validation issue | POST /api/v1/projects/{id}/validation/issues/{issue_id}/suppress | Admin | issue exists; status=open; suppression rationale provided | issue status = suppressed | validation.issue_suppressed |
| Reopen suppressed issue | POST /api/v1/projects/{id}/validation/issues/{issue_id}/reopen | Admin | issue status = suppressed | issue status = open | validation.issue_reopened |

---

## 10. Tailoring Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Create tailoring decision | POST /api/v1/projects/{id}/tailoring-decisions | Project Lead or Admin | target artefact type/rule exists in profile; rationale and evidence_refs present | tailoring decision created | tailoring.created |
| Update tailoring decision | PUT /api/v1/projects/{id}/tailoring-decisions/{td_id} | Project Lead or Admin | tailoring decision exists and is not obsolete | decision updated | tailoring.updated |
| Revoke tailoring decision | POST /api/v1/projects/{id}/tailoring-decisions/{td_id}/revoke | Admin | decision is approved | decision revoked; original applicability restored | tailoring.revoked |

---

## 11. Baseline Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Request baseline creation | POST /api/v1/projects/{id}/baselines | Project Lead or Admin | no baseline creation job currently running for project | baseline job enqueued; update lock acquired | baseline.creation_requested |
| Cancel baseline creation | POST /api/v1/projects/{id}/baselines/{bid}/cancel | Project Lead or Admin | baseline in requested or creating_snapshot state | baseline cancelled; lock released | baseline.cancelled |
| Trigger release gate evaluation | POST /api/v1/projects/{id}/release-gate/run | User, Project Lead, Quality Engineer, or Admin | no gate evaluation currently running for requested scope | gate evaluation job enqueued | release_gate.evaluation_started |
| Approve baseline | POST /api/v1/projects/{id}/baselines/{bid}/approve | Project Lead or Admin | baseline in created state; latest gate result is current and passed | baseline approved | baseline.approved |
| Release baseline | POST /api/v1/projects/{id}/baselines/{bid}/release | Quality Engineer or Admin | baseline in approved state; latest gate result is still current and passed | baseline released | baseline.released |
| Mark baseline obsolete | POST /api/v1/projects/{id}/baselines/{bid}/obsolete | Admin | baseline exists; not in released state | baseline obsolete | baseline.obsoleted |

---

## 12. Impact Analysis Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Trigger impact analysis | POST /api/v1/projects/{id}/impact | User, Project Lead, Quality Engineer, or Admin | artefact exists | impact analysis job enqueued | impact_analysis.started |
| Clear suspect state | POST /api/v1/projects/{id}/suspect-states/{ss_id}/clear | Project Lead, Quality Engineer, or Admin | suspect state exists; status=open; clearing_method and evidence_refs provided | suspect state cleared | suspect.cleared |

---

## 13. Report Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Generate report | POST /api/v1/projects/{id}/reports | User, Project Lead, Quality Engineer, or Admin | project exists | report generation job enqueued | report.generation_started |
| Delete generated report | DELETE /api/v1/projects/{id}/reports/{report_id} | Admin or Quality Engineer | report exists | report soft-deleted | report.deleted |

---

## 14. Standards Reference Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Add standards reference | POST /api/v1/projects/{id}/standards-references | Admin | standard reference ID unique in project | reference created | standards_ref.created |
| Update review status | PUT /api/v1/projects/{id}/standards-references/{ref_id} | Admin | reference exists | review status updated | standards_ref.updated |

---

## 15. Schema Configuration Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| Tailor artefact schema (disable fields) | PUT /api/v1/projects/{id}/schemas/{artefact_type} | Admin | schema exists; fields to disable are not mandatory canonical fields | schema configuration updated | schema.tailored |
| Tailor ASPICE process scope/capability | PUT /api/v1/projects/{id}/config | Admin | ASPICE process scope/capability changes include rationale and evidence_refs | assurance configuration updated; approved tailoring decisions recorded | project.aspice_tailoring_updated, tailoring.approved |

---

## 16. Repository Integration Operations

| Operation | Endpoint | Required Role | Pre-condition | Post-state | Audit Event |
|-----------|----------|---------------|---------------|------------|-------------|
| View repository connectors | GET /api/v1/projects/{id}/repo-connectors | User, Project Lead, Quality Engineer, or Admin | project exists | connectors returned without secrets | none |
| Create repository connector | POST /api/v1/projects/{id}/repo-connectors | Admin | GitHub App or access-token config and secrets provided | connector created; secrets encrypted | repository_connector.created |
| Update repository connector | PUT /api/v1/projects/{id}/repo-connectors/{connector_id} | Admin | connector exists | connector updated; optional secret rotation | repository_connector.updated |
| Soft-delete repository connector | DELETE /api/v1/projects/{id}/repo-connectors/{connector_id} | Admin | connector exists | connector status deleted | repository_connector.deleted |
| Test repository connector | POST /api/v1/projects/{id}/repo-connectors/{connector_id}/test | Admin | connector exists | connectivity result returned | none |
| Read repository status | GET /api/v1/projects/{id}/repo-connectors/{connector_id}/status | User, Project Lead, Quality Engineer, or Admin | connector exists | repository metadata, commit, checks, and statuses returned | none |
| Trigger repository scan | POST /api/v1/projects/{id}/repo-connectors/{connector_id}/scan | Admin or Project Lead | connector active | repository scan job enqueued | repository_scan.completed |
| List repository approvals | GET /api/v1/projects/{id}/baselines/{baseline_id}/repository-approvals | User, Project Lead, Quality Engineer, or Admin | baseline exists | approval publication history returned | none |
| Publish repository approval | POST /api/v1/projects/{id}/baselines/{baseline_id}/repository-approvals | Admin, Project Lead, or Quality Engineer | baseline released; target commit equals baseline snapshot | approval check or status sent to repository | repository_approval.published |
| Receive GitHub webhook | POST /api/v1/integrations/github/webhook/{connector_id} | System | connector active | delivery recorded; scan job enqueued when event applies | repository_webhook.received |

---

## 17. Cross-Cutting Authorization Rules

AAC-AUTH-FR-001
All project-scoped operations require the caller to be a member of the target project with one of the explicitly permitted roles for the operation.

AAC-AUTH-FR-002
Admin role is global and does not require project membership for project-scoped operations.

AAC-AUTH-FR-003
Read operations (GET) are available to any project member unless a more specific
operation rule restricts sensitive detail. Individual job status is restricted
to the original requester or Admin; project job listings may be read by project
members with sensitive detail redacted.

AAC-AUTH-FR-004
All role-sensitive write operations shall be logged as AuditEvents with actor_id, role_at_time_of_action, operation, and timestamp.

AAC-AUTH-FR-005
Only a Quality Engineer or Admin may create a new revision of a released
artefact through update or import workflows. Updating a released artefact shall
trigger impact analysis and suspect propagation.

AAC-AUTH-FR-006
Baseline creation acquires a project-scoped update lock (per `baseline_state_machine.md`). During the lock, all artefact and relationship write operations for the project shall return 423 Locked with `retry_after` hint.

AAC-AUTH-FR-007
The baseline update lock shall be released when baseline creation completes (success or failure) or is cancelled.

AAC-AUTH-FR-008
Read operations (GET, traceability queries, impact analysis reads) shall not be blocked by the baseline update lock.

AAC-AUTH-FR-009
Only the original requester or Admin may read an individual job by job ID or
cancel that job.

AAC-AUTH-FR-020
Import processing shall preserve the initiating actor and enforce authorization
for every resulting create, revise, lifecycle, and delete operation. Automatic
mode shall not bypass released-artefact authorization.
