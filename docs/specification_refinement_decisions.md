# Specification Refinement Decisions

## 1. Purpose

This document records confirmed architecture and requirements decisions for stabilizing the Assurance-as-Code specification pack.

These decisions supersede conflicting exploratory statements in `draft_AssuranceAs_Code.txt`.

## 2. Confirmed Architecture Baseline

DEC-ARCH-001
The system shall use a server-master architecture.

DEC-ARCH-002
The back-end shall own the canonical truth for all persisted assurance data.

DEC-ARCH-003
The back-end shall include a database-backed persistence layer.

DEC-ARCH-004
The back-end shall run on Linux.

DEC-ARCH-005
The front-end shall support Linux, Windows, and macOS clients through API-based access.

DEC-ARCH-006
The front-end shall not directly access or mutate the database.

## 3. Source Of Truth

DEC-TRUTH-001
The back-end database shall be the authoritative source of truth for all canonical artefacts, relationships, revisions, baselines, validation state, traceability state, suspect state, audit events, and evidence references.

DEC-TRUTH-002
Sphinx documentation shall be an authoring source, not the canonical operational source of truth.

DEC-TRUTH-003
Conflicts between authored documentation and database state shall be handled through automatic versioning.

DEC-TRUTH-004
Any imported update to an authored document or authored artefact shall create a new persisted version or revision in the back-end database.

DEC-TRUTH-005
The system shall preserve previous persisted versions so that the history of documentation-derived artefacts remains auditable.

DEC-TRUTH-006
The back-end shall determine whether an imported authored object is new, changed, unchanged, deleted, or conflicting relative to the current database state.

DEC-TRUTH-007
The back-end shall record the source document, source object ID, import event, actor/process, timestamp, and change summary for each document-derived version.

## 4. Authoring Flow

DEC-FLOW-001
Users shall author or edit lifecycle artefacts in Sphinx documentation first.

DEC-FLOW-002
The system shall import Sphinx-authored artefacts into the back-end.

DEC-FLOW-003
The import process shall normalize Sphinx-authored objects into canonical artefacts and relationships.

DEC-FLOW-004
The import process shall persist normalized artefacts and relationships into the database under automatic version control.

DEC-FLOW-005
The import process shall trigger validation, traceability update, impact analysis, and suspect propagation as required.

DEC-FLOW-006
The back-end shall expose import results, diagnostics, and created revisions through the web app and CLI.

## 5. MVP Front-End

DEC-FE-001
The MVP shall provide a web application front-end.

DEC-FE-002
The MVP shall provide a CLI front-end.

DEC-FE-003
The web application and CLI shall both communicate with the back-end through supported APIs.

DEC-FE-004
The CLI shall be a client of the same back-end capabilities used by the web application, not an independent local execution engine.

DEC-FE-005
The MVP front-ends shall support at minimum import, validation status, traceability query, baseline command, impact query, report generation, and release-gate command workflows.

## 6. Database Choice And Model Depth

DEC-DB-001
The MVP shall use a relational-plus-graph-query model.

DEC-DB-002
The canonical persisted model shall be relational.

DEC-DB-003
Graph behavior shall be implemented through typed relationship tables, indexes, traversal queries, and a back-end graph service.

DEC-DB-004
The MVP shall not require a dedicated graph database.

DEC-DB-005
A dedicated graph database may be reconsidered later only if scale, performance, or query complexity justifies it.

## 7. Controlled Requirement ID Scheme

All stable requirements shall use one controlled ID scheme:

`AAC-<AREA>-<TYPE>-<NNN>`

Where:

- `AAC` identifies the Assurance-as-Code platform.
- `<AREA>` identifies the requirement area.
- `<TYPE>` identifies whether the item is a functional requirement, non-functional requirement, interface requirement, data requirement, architecture requirement, or rule.
- `<NNN>` is a zero-padded sequence number unique within the area and type.

Allowed `<TYPE>` values:

- `FR` functional requirement
- `NFR` non-functional requirement
- `AR` architecture requirement
- `IR` interface requirement
- `DR` data/database requirement
- `RULE` validation, consistency, impact, or gate rule
- `DEC` confirmed design or scope decision

Initial `<AREA>` values:

- `SYS` system-level behavior
- `AUTH` Sphinx authoring and import
- `FE` front-end behavior
- `API` API behavior
- `CORE` canonical core behavior
- `DATA` data model and database persistence
- `DB` database persistence
- `GRAPH` relationship graph and traceability
- `RULE` validation and consistency rules
- `PROFILE` assurance profile configuration
- `STD` standards traceability
- `SNEEDS` Sphinx-Needs mapping
- `IMPORT` import behavior
- `VERSION` versioning behavior
- `BASE` baselines
- `IMPACT` impact and suspect propagation
- `TEST` test result and evidence handling
- `AUDIT` audit and history
- `REPORT` reporting and exports
- `OPS` deployment, migration, backup, and operations

Examples:

- `AAC-SYS-FR-001`
- `AAC-DATA-DR-001`
- `AAC-DB-DR-001`
- `AAC-GRAPH-FR-001`
- `AAC-RULE-RULE-001`
- `AAC-API-IR-001`
- `AAC-OPS-NFR-001`

Rules for ID governance:

- IDs shall not be reused after deletion.
- Superseded requirements shall be marked obsolete, not removed from controlled baselines.
- Requirement IDs shall be stable across document reorganizations.
- Draft IDs from earlier material may be mapped to final IDs in a migration table.

## 8. Document Set

The stable specification pack shall be split into multiple controlled documents.

Each document shall cover one functional or architectural concern.

Recommended documents:

1. Product Vision And Scope
2. System Requirements Specification
3. Authoring And Import Requirements
4. Web Front-End Requirements
5. CLI Requirements
6. API Requirements
7. Canonical Data Model Specification
8. Database Requirements
9. Relationship Graph And Traceability Specification
10. Validation Rule Catalog
11. Baseline And Release Gate Specification
12. Impact And Suspect Propagation Specification
13. Test Result And Evidence Specification
14. Audit And Versioning Specification
15. Back-End Architecture Specification
16. Front-End Architecture Specification
17. Event Model Specification
18. Deployment And Operations Specification
19. Sphinx-Needs Mapping Specification
20. MVP Acceptance Criteria

## 9. MVP Boundary

DEC-MVP-001
Everything captured in the stable requirements set shall be included in version 1 of the tool.

DEC-MVP-002
The requirements stabilization process shall therefore avoid placing aspirational or speculative functionality into the stable version 1 requirements unless it is intended for first release delivery.

DEC-MVP-003
Later functionality shall be recorded in a separate post-v1 backlog, not in the v1 requirement baseline.

## 10. Open Specification Work

The following areas previously required further specification. All are now resolved:

| Item | Status | Resolved In |
|------|--------|-------------|
| precise rule semantics | **RESOLVED** | `rule_semantics_specification.md` |
| API contracts | **RESOLVED** | `api_endpoint_specification.md` + `authorization_matrix.md` |
| domain event model | **RESOLVED** | `domain_event_model.md` |
| database logical schema | **RESOLVED** | `logical_database_schema.md` |
| import conflict semantics | **RESOLVED** | `import_conflict_and_change_detection.md` |
| version/revision policy | **RESOLVED** | `import_conflict_and_change_detection.md` + `import_and_versioning_state_machines.md` |
| authorization model for MVP | **RESOLVED** | `authorization_matrix.md` |
| report and dashboard data contracts | **RESOLVED** — version 1 JSON reports and API-projected dashboard defined | `requirements_baseline.md` + `resource_model_and_api_requirements.md` |
| release-gate state model | **RESOLVED** | `release_gate_state_machine.md` |
| migration and backup procedures | **RESOLVED** | `backend_architecture_and_technology_decisions.md` §4.3 |

**Explicit post-v1 items:**
- CSV, HTML, and PDF report formats beyond the version 1 JSON contracts
- Configurable dashboard layouts beyond the version 1 API-projected operational dashboard
- External message broker integration (Kafka/RabbitMQ for post-MVP scale)
- GDPR/data retention policy

## 11. Authorization Model Decision

DEC-AUTHZ-001
The MVP shall support four roles:

- Admin
- Project Lead
- Quality Engineer
- User

DEC-AUTHZ-002
An Admin shall be able to configure the tool.

DEC-AUTHZ-003
An Admin shall be able to delete any artefact, subject to audit and database history preservation rules.

DEC-AUTHZ-004
A User shall be able to use all normal tool functionality except administrative configuration and unrestricted artefact deletion.

DEC-AUTHZ-005
Admin, Project Lead, Quality Engineer, and User roles shall be able to trigger normal operational workflows, including import, validation, traceability queries, impact analysis, report generation, and release-gate evaluation unless later restricted by project policy.

DEC-AUTHZ-006
All role-sensitive actions shall be audited.

DEC-AUTHZ-007
A Project Lead shall be able to create project baselines.

DEC-AUTHZ-008
A Quality Engineer shall be able to release artefacts.

DEC-AUTHZ-009
Artefact deletion shall mean soft deletion by transition to obsolete or equivalent deleted lifecycle state. Physical deletion shall not be used for normal artefact deletion.

DEC-AUTHZ-010
Only a Quality Engineer or Admin shall revise a released artefact.

DEC-AUTHZ-011
A Project Lead or Admin shall approve a baseline. A Quality Engineer or Admin shall release an approved baseline.

DEC-AUTHN-001
The MVP shall use username and password authentication.

DEC-AUTHN-002
Only Admin shall be able to create user accounts.

DEC-AUTHN-003
Only Admin shall be able to assign or change user roles.

DEC-AUTHN-004
Passwords shall not be stored in plaintext.

## 12. Version Conflict Decision

DEC-VERSION-001
The tool shall detect when an imported or edited artefact differs from the current stored artefact revision.

DEC-VERSION-002
The tool shall support a project configuration option named `version_update_mode`.

DEC-VERSION-003
The version update behavior shall support at least:

- automatic_new_version
- ask_user

DEC-VERSION-004
When configured as `automatic_new_version`, the back-end shall create a new artefact revision for every accepted update that changes canonical content.

DEC-VERSION-005
When configured as `ask_user`, the back-end shall report detected changes and require user confirmation before creating a new artefact revision.

DEC-VERSION-006
If the user declines to create a new version in `ask_user` mode, the current stored revision shall remain active and the rejected update shall not modify canonical artefact state.

DEC-VERSION-007
Unchanged imports shall not create a new artefact revision.

## 13. Baseline Decision

DEC-BASE-001
Baseline creation shall be a manual process.

DEC-BASE-002
Baseline creation may be triggered by a Project Lead or an Admin.

DEC-BASE-003
A baseline shall save a snapshot of all selected artefacts and relationships belonging to a project scope.

DEC-BASE-004
The tool shall support multiple projects in parallel.

DEC-BASE-005
Each baseline shall belong to exactly one project.

DEC-BASE-006
Baseline snapshots shall reference exact artefact revisions and relationship revisions, not mutable latest artefact records.

## 14. Tooling Decision

DEC-TOOL-001
Python shall be the development environment for the back-end and tool implementation unless a later controlled architecture decision changes this.
