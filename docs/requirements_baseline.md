# Version 1 Requirements Baseline

## 1. Status And Purpose

Document status: **controlled version 1 baseline**

Baseline date: **2026-06-12**

This document resolves cross-document conflicts and defines the requirements that
must be satisfied before implementation changes are accepted. It does not replace
the detailed resource, schema, state-machine, API, or rule specifications. It
defines their authority, closes identified gaps, and supplies requirements that
apply across those documents.

## 2. Requirements Quality And Change Control

AAC-GOV-FR-001
Every proposed change shall be evaluated in this order:

1. requirements;
2. software architecture;
3. implementation and verification.

AAC-GOV-FR-002
A requirement shall be accepted only when it is:

- necessary: represents a stakeholder or system need that justifies its cost;
- unambiguous: has one testable interpretation and controlled terminology;
- complete: includes actors, inputs, conditions, outputs, failure behavior, and
  verification;
- consistent: does not contradict another active requirement;
- singular: expresses one independently verifiable obligation where practical;
- feasible: can be implemented and operated within known technical, schedule,
  security, and regulatory constraints;
- verifiable: has objective pass/fail evidence;
- traceable: links to its source need, architecture allocation, and acceptance
  evidence.

AAC-GOV-FR-003
Every normative requirement shall have a stable identifier and shall trace to at
least one architecture function or interface and one acceptance criterion.

AAC-GOV-FR-004
When a change affects an existing requirement, its architecture allocation,
dependency map, implementation, tests, and user-facing documentation shall be
reviewed for impact before the change is merged.

AAC-GOV-FR-005
Unresolved requirements shall not be implemented. They shall be recorded as an
open decision with an owner and shall remain outside the controlled version 1
baseline.

AAC-GOV-FR-006
For a new application or substantial capability, stakeholder needs shall be
identified before normative requirements are written. For a Class C or Class D
maintenance change, the affected stakeholder needs shall be referenced when
requirements are changed. Class A and Class B maintenance changes do not require
new stakeholder-level derivation when approved requirements already control the
work.

AAC-GOV-FR-007
Each requirement shall identify its abstraction level as stakeholder
requirement (`StRS`), system requirement (`SyRS`), or software requirement
(`SRS`) and its type as functional, performance, interface, security, or
constraint. This classification is required for new or materially changed
requirements, not for Class A or Class B work that creates no requirement.
Multiple levels may be maintained in one controlled document when their IDs and
derivation links remain explicit.

AAC-GOV-FR-008
Each applicable changed gate shall produce a proportionate structured artifact
or an explicit delta to an existing controlled artifact. A Class A record may be
limited to a no-behavioral-impact statement and verification result. A Class B
record may reference existing requirement and architecture IDs. Requirements
artifacts for Class C and Class D changes shall contain the stakeholder needs,
requirements, acceptance criteria, and traceability affected by the change.

AAC-GOV-FR-009
Applicable requirements, architecture, and implementation gates shall remain
sequential. A gate that is not affected may be closed by a documented impact
assessment rather than an artifact rewrite. Independent analysis and
verification work may run in parallel within the active gate. No production
implementation may begin while its controlling requirements or architecture
changes remain unresolved.

AAC-GOV-FR-010
Explicit approval is required before advancing from:

- requirements to architecture when product scope or externally observable
  behavior is added, removed, or materially changed;
- architecture to implementation when responsibilities, interfaces, dependency
  direction, data ownership, state machines, technology, or deployment are
  materially changed.

Routine implementation already covered by approved requirements and architecture
does not require a new approval unless the user or project policy requests one.
An explicit user request to implement such Class B work counts as approval to
proceed.

AAC-GOV-FR-011
Requirements work shall not select internal implementation mechanisms.
Externally observable interface, security, performance, regulatory, and
deployment constraints may be specified because they define required behavior.
Technical feasibility analysis may be performed during requirements work,
including investigation of constraints and candidate approaches, but controlled
architecture selection remains in the architecture gate.

AAC-GOV-AR-001
An architecture description created or materially changed for a capability
shall identify relevant stakeholders and concerns, select proportionate
viewpoints, and provide the views needed to address those concerns. Viewpoints
may include logical, process, data, deployment, security, and operational views.

AAC-GOV-AR-002
Every significant architecture decision shall record its requirement drivers,
rationale, considered alternatives, trade-offs, risks, and mitigation strategy.

AAC-GOV-FR-012
If a later gate exposes a gap or conflict in an earlier artifact, work shall
return formally to the affected gate, update and re-approve the artifact when
AAC-GOV-FR-010 applies, and then resume from the next gate.

AAC-GOV-FR-013
Every change shall be classified before production modification:

- `Class A`: editorial, formatting, test-only, fixture, or build-support change
  with no product behavioral impact;
- `Class B`: implementation or refactoring fully covered by approved
  requirements and architecture with no externally observable contract change;
- `Class C`: externally observable behavior or contract change that does not
  materially change architecture;
- `Class D`: change to architecture, persistence, security behavior, control, or
  boundary, interoperability, public integration, deployment, or other
  high-impact system concern.

Classification is determined by impact, not by filename or apparent change
size.

AAC-GOV-FR-014
If classification is uncertain, the higher plausible class shall be used and
the reason recorded. A change shall be reclassified when investigation reveals
broader behavioral or architectural impact.

AAC-GOV-FR-015
The minimum process by class is:

- Class A: record no behavioral impact, make the change, and run relevant
  verification;
- Class B: reference approved requirement, acceptance, and architecture IDs,
  then implement and verify;
- Class C: update and approve requirements and acceptance criteria, perform an
  architecture impact assessment, update architecture only when affected, then
  implement and verify;
- Class D: update and approve requirements and architecture before
  implementation and verification.

AAC-GOV-FR-016
Read-only investigation and isolated disposable technical spikes may occur
before gate approval to establish feasibility or discover impact, provided:

- no spike code is merged or treated as production implementation;
- no canonical data or production migration is changed;
- the spike does not become an implicit architecture decision;
- assumptions, findings, risks, and discarded code are returned to the
  appropriate controlled gate.

AAC-GOV-FR-017
Only public, cross-module, persistent, external, security-relevant, or otherwise
behaviorally significant interfaces require full controlled interface
contracts. Private implementation boundaries require documentation only when
their complexity or risk warrants it.

AAC-GOV-FR-018
Verification commands and evidence shall be selected according to the changed
surface and risk class. Full lint, build, migration, deployment, performance,
and security checks are required only when applicable, while every change shall
receive sufficient verification to demonstrate its claimed impact.

AAC-GOV-FR-019
Requirement IDs need not appear in every function, class, or test name when an
authoritative traceability manifest provides the same requirement-to-code-to-test
link.

## 3. Document Authority

The following authority order applies when documents overlap:

1. This baseline controls version 1 scope and cross-document conflict
   resolutions.
2. `authorization_matrix.md` controls operation-level authorization.
3. The relevant state-machine document controls states and transitions.
4. `artefact_json_schemas.md` controls artefact field names, types, required
   fields, and conditional field rules.
5. `canonical_artefact_name_reconciliation.md` controls canonical type names and
   aliases only.
6. `api_endpoint_specification.md` and `async_job_schema.md` control external
   request and response contracts.
7. `logical_database_schema.md` and `database_requirements.md` control persisted
   logical data and integrity constraints.
8. `software_architecture.md` controls function ownership, interfaces, allowed
   dependencies, and transaction boundaries.
9. `mvp_acceptance_criteria.md` controls release verification.

If a lower-authority document conflicts with a higher-authority document, the
higher-authority requirement applies and the conflict is a documentation defect
that must be corrected before implementation changes continue.

## 4. Version 1 Scope

AAC-SCOPE-FR-001
All normative requirements in the controlled `docs/` set are version 1 scope
unless a requirement is explicitly marked `POST-V1`.

AAC-SCOPE-FR-002
Version 1 shall include these end-to-end capabilities:

- authentication, project membership, and role authorization;
- project/profile configuration and tailoring;
- canonical artefact and relationship lifecycle with immutable revisions;
- Sphinx-Needs import, conflict decisions, deletion detection, and validation
  triggering;
- validation, traceability, impact analysis, and suspect propagation;
- baseline creation, release-gate evaluation, approval, and release;
- asynchronous job status and cancellation;
- audit and domain-event processing;
- the three report contracts in `mvp_acceptance_criteria.md`;
- repository integration in `repository_integration_contract.md`;
- web and CLI access to the operational workflows in AAC-UI-FR-001 and
  AAC-UI-FR-002.

AAC-SCOPE-FR-003
Version 1 report output is JSON for traceability matrix, baseline comparison,
and validation summary reports. CSV, HTML, PDF, configurable dashboard layouts,
and external message brokers are `POST-V1`.

AAC-SCOPE-FR-004
The version 1 web dashboard is an API projection of project status, validation
summary, active jobs, baseline status, and release-gate status. It does not
introduce a separate source of truth or a separate dashboard domain model.

AAC-SCOPE-FR-005
A capability listed in version 1 scope shall not be described as partial or
deferred in another controlled requirements document.

## 5. Authorization Requirements

AAC-AUTH-FR-010
Only a Quality Engineer or Admin shall create a new revision of a released
artefact. The operation shall trigger impact analysis and suspect propagation.

AAC-AUTH-FR-011
A Project Lead or Admin may approve a baseline after a current release-gate
pass. Only a Quality Engineer or Admin may release an approved baseline.

AAC-AUTH-FR-012
Only the original requester or Admin may read an individual job by job ID or
cancel it. A project member may list project jobs, but job input, decision, and
error detail shall be returned only to the original requester or Admin.

AAC-AUTH-FR-013
Only the original import submitter, a Quality Engineer, or Admin may submit an
import decision. The submitter must also be authorized for the resulting
artefact operation; a released artefact therefore requires a Quality Engineer
or Admin decision. Only the original requester or Admin may cancel an import.

AAC-AUTH-FR-014
Publishing repository approval is permitted to a Project Lead, Quality Engineer,
or Admin only after the referenced baseline has been released. Publishing an
approval shall not perform or imply baseline release.

AAC-AUTH-FR-015
Every role-sensitive operation shall create an append-only audit event containing
`actor_id`, `role_at_time_of_action`, `operation`, `project_id`,
`correlation_id`, and timestamp.

AAC-AUTH-FR-016
Import workers shall preserve the initiating actor and enforce the same
authorization as the equivalent direct artefact operation. Automatic import
mode shall not bypass released-artefact authorization.

## 6. Import And Job Requirements

AAC-IMPORT-FR-080
The canonical import decision values are:

- `accept_new_revision`;
- `reject_keep_current`.

No external contract shall use `accept_new_version`.

AAC-IMPORT-FR-081
In `ask_user` mode, every changed or stale-source artefact shall have an explicit
decision before its proposed revision is persisted. Unchanged artefacts require
no decision. Type mismatches are errors and cannot be accepted by decision.

AAC-IMPORT-FR-082
The canonical terminal import states are `completed`,
`completed_with_errors`, `completed_no_changes_applied`, `failed`, and
`cancelled`. `completed_with_errors` shall be used when all processable batches
finish but one or more non-fatal item errors remain.

AAC-IMPORT-FR-083
Each import batch is atomic. Failure within a batch shall leave no partial state
from that batch. Previously committed batches may remain and shall be identified
by `last_committed_batch_index`; a resumable run shall not be reported as
completed until all remaining batches and relationships are processed.

AAC-IMPORT-FR-084
Cancellation is cooperative at transaction boundaries. A cancelled job response
shall report whether committed effects exist and identify the last committed
unit of work. Committed effects shall never be ambiguously described as rolled
back.

AAC-IMPORT-FR-085
Import completion shall enqueue validation exactly once for the final committed
import outcome. Duplicate domain-event delivery shall not create duplicate
effective validation runs.

## 7. Baseline And Release-Gate Requirements

AAC-BASE-FR-060
A release-gate result is current only when it is the newest completed evaluation
for the baseline and no blocking-relevant event or governing configuration
change occurred after its evaluation cut-off.

AAC-BASE-FR-061
A blocking-relevant event is any event that can change a release-gate outcome,
including an issue whose severity blocks under the active profile, an open
suspect state, a mandatory artefact gap, a required traceability gap, a failed
test condition, or a governing profile/rule/tailoring change.

AAC-BASE-FR-062
If a blocking-relevant event occurs after a gate pass and before release, the
gate status shall become `stale`. If the baseline was approved, approval shall
be invalidated, approval metadata shall be retained in audit history, and the
baseline shall return to `created`.

AAC-BASE-FR-063
A stale baseline shall be re-evaluated and, after a pass, re-approved before
release.

AAC-BASE-FR-064
Release shall perform a transactional final guard that verifies baseline state
is `approved`, the latest gate result is current and `passed`, and no later
blocking-relevant event exists.

AAC-BASE-FR-065
For the ASIL D default profile, both `critical` and `major` issues are
blocking-relevant. For another profile, the active profile's severity policy is
authoritative.

## 8. Security And API Requirements

AAC-SEC-FR-010
Production deployment shall terminate TLS and redirect or reject plain HTTP.
Development-only HTTP shall be explicitly configured and shall not be the
production default.

AAC-SEC-FR-011
CORS shall deny origins by default. Allowed origins shall be supplied by
`AAC_CORS_ORIGINS`; wildcard origins shall be prohibited when credentials are
enabled.

AAC-SEC-FR-012
Import requests shall enforce a 50 MB maximum before reading the complete body
into application memory and shall reject unsupported media types.

AAC-API-IR-160
Successful API responses shall use:

```json
{
  "status": "success",
  "request_id": "string",
  "data": {}
}
```

AAC-API-IR-161
Error API responses shall use:

```json
{
  "status": "error",
  "request_id": "string",
  "error": {
    "code": "stable_machine_code",
    "message": "sanitized human-readable message",
    "details": {}
  }
}
```

Stack traces, SQL text, credentials, internal paths, and database structure shall
not be present in an API error.

AAC-API-IR-162
Authorization failures shall consistently return `401` for missing or invalid
authentication and `403` for an authenticated actor lacking permission. State
precondition failures shall return `409`, and active baseline locks shall return
`423`.

## 9. Event, Revision, And Audit Requirements

AAC-EVENT-AR-010
State changes and their domain-event outbox records shall commit in the same
database transaction. Events shall be dispatched after commit with at-least-once
delivery.

AAC-EVENT-AR-011
Domain-event consumers shall be idempotent by `event_id` or a documented
business idempotency key. A delivery failure shall remain retryable and
observable; it shall not be discarded after logging.

AAC-EVENT-AR-012
The version 1 event bus remains internal to the product. A PostgreSQL outbox,
in-process dispatcher, Valkey through the Redis-compatible protocol, and ARQ
may be used without exposing an external
subscriber contract.

AAC-REV-FR-010
Every artefact and relationship revision after revision 1 shall reference its
immediate predecessor through non-null `previous_revision_id`. Revision 1 shall
have `previous_revision_id = null`.

AAC-REV-FR-011
Revision creation and current-revision pointer update shall occur in one
transaction with optimistic concurrency protection.

AAC-AUDIT-FR-010
Audit events are distinct from domain events. Audit events are immutable records
of actions; domain events are integration messages used to trigger processing.
One operation may create both in the same transaction.

## 10. Canonical Schema Requirements

AAC-SCHEMA-FR-010
`artefact_json_schemas.md` is the sole authority for artefact payload fields,
types, requiredness, and conditional requiredness.

AAC-SCHEMA-FR-011
`canonical_artefact_name_reconciliation.md` shall define names and aliases only.
Its descriptive examples shall not introduce field requirements.

AAC-SCHEMA-FR-012
API schemas, import normalization, database JSON validation, rule inputs, report
projections, and generated UI forms shall derive from or validate against the
same versioned canonical schema registry.

AAC-SCHEMA-FR-013
Each stored revision shall record `schema_version`. A schema change shall define
backward-read behavior and a migration or compatibility policy before use.

## 11. User Interface Requirements

AAC-UI-FR-001
The version 1 web application shall support:

- authentication and project selection;
- artefact and relationship create, read, revise, and lifecycle actions allowed
  to the actor;
- import submission, progress, item diagnostics, and import decisions;
- validation status and issue handling;
- forward and backward traceability;
- impact analysis and suspect-state review/clearance;
- baseline creation, release-gate evaluation, approval, and release;
- report generation/retrieval and job status/cancellation.

AAC-UI-FR-002
The version 1 CLI shall expose the same operational workflows as AAC-UI-FR-001,
except visual dashboard presentation. The CLI shall call supported APIs and
shall not contain an independent business-rule implementation.

AAC-UI-FR-003
The web and CLI shall render authorization and state-transition availability
from API capabilities or shared contract metadata. Hidden or disabled controls
are usability measures and shall not replace server-side authorization.

AAC-UI-FR-004 (`SRS`, functional; derives from `NEED-UI-001` through
`NEED-UI-004`)
The web application shall organize operational capabilities by actor task and
shall automatically load the selected task's current data. It shall provide an
overview of actionable work, blocking conditions, active jobs, validation
status, suspect states, and release readiness without requiring the actor to
manually invoke separate load operations.

AAC-UI-FR-005 (`SRS`, interface; derives from `NEED-UI-001`,
`NEED-UI-004`, and `NEED-DEV-UI-001`)
Guided artefact forms shall derive enabled, mandatory, read-only, type, widget,
allowed-value, label, and help metadata from the versioned canonical schema
registry. Raw JSON editing and transport diagnostics shall remain available in
an explicitly identified advanced view and shall not define an alternative
schema.

AAC-UI-FR-006 (`SRS`, security; derives from `NEED-UI-001` through
`NEED-UI-004`)
The API shall provide the selected project's effective actor roles, named
capabilities, and behaviorally significant resource actions. The web
application shall use this metadata for presentation only and shall submit every
controlled action to the existing authorized API command.

AAC-UI-FR-007 (`SyRS`, constraint; derives from `NEED-UI-005`)
The web application shall conform to WCAG 2.2 Level AA for supported workflows,
including keyboard operation, visible focus, programmatic names and
relationships, contrast, error identification, and status announcements.

AAC-UI-FR-008 (`SRS`, functional; derives from `NEED-UI-001` through
`NEED-UI-005`)
Every asynchronous or failing web operation shall present a distinguishable
loading or progress state and an actionable success, empty, cancellation,
conflict, locked, forbidden, expired-session, or failure result. Request and
correlation identifiers shall be available in advanced error details.

AAC-UI-FR-009 (`SyRS`, constraint; derives from `NEED-UI-001` through
`NEED-UI-005`)
All version 1 workflows shall be usable at viewport widths of 768 CSS pixels or
greater. At narrower widths the application shall support authentication,
overview, status review, monitoring, and simple actions without inaccessible
content; bulk editing and complex graph manipulation need not be optimized.

AAC-UI-FR-010 (`SRS`, constraint; derives from `NEED-DEV-UI-001`)
The web implementation shall use independently testable feature modules behind
a versioned API client. Feature views and reusable components shall not call
the transport directly or implement authorization, lifecycle, release, import,
validation, or schema policy.

## 12. Verification Requirements

AAC-VER-FR-001
Every `MUST PASS` criterion shall identify an executable test ID or a controlled
inspection record. A verification method without a test or inspection reference
is incomplete evidence.

AAC-VER-FR-002
Release evidence shall include:

- unit and integration test results;
- deployed API end-to-end results against PostgreSQL and Valkey;
- migration from an empty database;
- production deployment security checks;
- deterministic performance dataset seed and benchmark results;
- requirements-to-architecture-to-test traceability;
- repository integration acceptance results.

AAC-VER-FR-003
All `MUST PASS` criteria shall pass. A `SHOULD PASS` failure requires a dated,
approved waiver with owner, rationale, risk, and expiry. Informational criteria
do not block release.

## 13. Resolution Of The Ten Review Findings

| Finding | Resolution |
|---|---|
| 1. Version 1 scope was uncontrolled | AAC-SCOPE-FR-001 through 005 |
| 2. Acceptance was not provable | AAC-GOV-FR-003 and AAC-VER-FR-001 through 003 |
| 3. Authorization documents conflicted | AAC-AUTH-FR-010 through 014 |
| 4. Release-gate stale logic was incomplete | AAC-BASE-FR-060 through 065 |
| 5. Import contracts were inconsistent | AAC-IMPORT-FR-080 through 085 |
| 6. Security requirements were unmet or ambiguous | AAC-SEC-FR-010 through 012 and AAC-API-IR-160 through 162 |
| 7. Event architecture was unreliable | AAC-EVENT-AR-010 through 012 |
| 8. Revision and audit data was incomplete | AAC-REV-FR-010 through 011 and AAC-AUDIT-FR-010 |
| 9. Canonical schema authority was unclear | AAC-SCHEMA-FR-010 through 013 |
| 10. Front-end workflows were incomplete | AAC-UI-FR-001 through 003 |

## 14. Application Code Licensing

Stakeholder need `NEED-LIC-001`: application maintainers and recipients need an
explicit Apache License, Version 2.0 grant for the project's own application code
and consistent licensing information in distributed application packages.

AAC-LIC-CR-001 (`SRS`, constraint; derives from `NEED-LIC-001`)
The project's own application code shall be licensed under the Apache License,
Version 2.0 (`Apache-2.0`). The source repository shall contain the complete,
unmodified license text in a top-level `LICENSE` file, and its README shall
identify that license and link to that file.

AAC-LIC-IR-001 (`SRS`, interface; derives from `NEED-LIC-001`)
The Python and JavaScript project package metadata shall identify the application
license as Apache License, Version 2.0. The JavaScript root package lock metadata
shall agree with its package manifest.

AAC-LIC-CR-002 (`SRS`, constraint; derives from `NEED-LIC-001`)
Application Python source distributions, wheels, and backend container images
shall include the complete application `LICENSE` text for their recipients.

AAC-LIC-CR-003 (`SRS`, constraint; derives from `NEED-LIC-001`)
Application licensing declarations shall distinguish the project's own code
from third-party dependencies, tools, and service images, whose existing
licenses and required notices shall be preserved. During the initial application
license adoption, runtime dependency versions and runtime application behavior
shall remain unchanged. Later, explicitly approved release-licensing changes
are governed by `release_licensing_requirements.md`; third-party license and
notice preservation remains mandatory.

Acceptance criteria are `ACC-LIC-001` through `ACC-LIC-004` in
`mvp_acceptance_criteria.md`. The licensing gate decisions, document impact
assessment, and verification evidence are controlled in
`app_licensing_change_record.md`.

## 15. Release Licensing Assurance

`release_licensing_requirements.md` controls the proposed release-distribution
licensing capability, including default broker licensing, reproducible release
inputs, component inventories, third-party obligations, source provenance,
built-image verification, and release acceptance evidence. Its stakeholder
needs derive from `NEED-LIC-001` and distinguish release recipients, operators,
and rights holders. The user has approved the Valkey broker replacement in
`AAC-LIC-CR-004`, the broker scope of `AAC-LIC-CR-011`, and `AAC-LIC-CR-012`.
The remaining release-licensing scope is proposed pending approval, as recorded
in `release_licensing_change_record.md`. The broker change is controlled in
`valkey_replacement_change_record.md`.

The initial application-license adoption record remains historical evidence.
It does not establish third-party distribution compliance or ownership of
unreviewed source code. Release licensing acceptance is defined by
`ACC-LIC-005` through `ACC-LIC-014` in `mvp_acceptance_criteria.md`.
