# Database Requirements

## 1. Architecture Baseline

The Assurance-as-Code platform shall use a server-master architecture.

The back-end server is the authoritative system of record for all canonical assurance data. The back-end shall include and control a database-backed persistence layer that stores all canonical artefacts, relationships, revisions, baselines, validation state, traceability state, audit events, and evidence references.

The front-end shall not directly own or mutate canonical assurance data. All front-end operations shall be performed through back-end APIs.

The back-end shall run on Linux. Front-end clients may run on Linux, Windows, or macOS.

## 2. Scope

These requirements cover the database and persistence responsibilities needed by the Assurance-as-Code platform MVP.

The database shall support:

- canonical artefact storage
- relationship storage
- automatic version and revision history
- baseline snapshots
- traceability queries
- validation issue storage
- impact and suspect state
- test result and evidence references
- audit history
- transactional integrity
- migration, backup, and restore

## 3. Database Ownership Requirements

AAC-DB-DR-001
The back-end shall be the only component permitted to directly read from or write to the database.

AAC-DB-DR-002
The database shall be the authoritative store for canonical artefacts and canonical relationships.

AAC-DB-DR-003
The front-end shall access persisted assurance data only through back-end APIs.

AAC-DB-DR-004
Sphinx-Needs authored content shall not be treated as the canonical database state until imported, normalized, validated, and persisted by the back-end.

AAC-DB-DR-005
Generated reports, dashboards, and published documentation shall be derived from database-backed canonical state or from explicitly versioned exports of that state.

## 4. Platform Requirements

AAC-DB-DR-010
The database service shall be deployable on Linux with the back-end server.

AAC-DB-DR-011
The database shall not require a proprietary runtime dependency for MVP operation.

AAC-DB-DR-012
The database access layer shall be independent of the front-end operating system.

AAC-DB-DR-013
The database shall support API-driven access from front-end clients running on Linux, Windows, or macOS through the back-end.

AAC-DB-DR-014
The database shall support deployment in a local development environment and in a CI/test environment.

## 5. Canonical Artefact Storage Requirements

AAC-DB-DR-020
The database shall store all canonical resource classes defined in `resource_model_and_api_requirements.md`.

At minimum, this includes project/configuration resources, safety planning resources, system-level reference resources, software requirements resources, software architecture and interface resources, software design and implementation resources, software verification resources, analysis and assurance resources, tool/process/qualification resources, issue/defect/change resources, evidence/reporting resources, and audit/history resources.

AAC-DB-DR-021
Each artefact record shall have a globally unique artefact ID.

AAC-DB-DR-022
Each artefact record shall store current metadata including type, title, status, owner, current revision, creation timestamp, update timestamp, source tool, source object ID, and source document reference.

AAC-DB-DR-023
The database shall support artefact payloads with type-specific structured fields.

AAC-DB-DR-024
The database shall preserve source traceability from each canonical artefact back to the authored object or imported source from which it was created.

AAC-DB-DR-025
The database shall support soft deletion of artefacts so that historical baselines and audit history remain valid.

AAC-DB-DR-026
The database shall store standards reference metadata for artefacts, rules, profiles, and mappings where applicable.

AAC-DB-DR-027
The database shall store the review status of each standards-derived mapping.

AAC-DB-DR-028
The database shall support querying artefacts and rules by standards reference.

## 6. Versioning and Revision Requirements

AAC-DB-DR-030
The database shall store immutable historical revisions for each artefact.

AAC-DB-DR-031
The back-end shall create a new artefact revision whenever a persisted artefact payload or release-relevant metadata changes.

AAC-DB-DR-032
The database shall store revision number, changed-by identity, changed-at timestamp, change reason where available, and associated change event ID for each artefact revision.

AAC-DB-DR-033
Historical artefact revisions shall not be overwritten by normal update operations.

AAC-DB-DR-034
The database shall support retrieval of the current revision and any historical revision of an artefact.

AAC-DB-DR-035
The database shall support comparison between two revisions of the same artefact.

AAC-DB-DR-036
The database shall store relationship revisions where relationship changes affect traceability, validation, baseline, or release state.

## 7. Relationship and Graph Requirements

AAC-DB-DR-040
The database shall store typed relationships between canonical artefacts.

AAC-DB-DR-041
Each relationship shall have a unique relationship ID, relationship type, source artefact ID, target artefact ID, status, creation timestamp, update timestamp, and current revision.

AAC-DB-DR-042
The database shall support the canonical relationship types defined by the platform, including allocation, satisfaction, dependency, interface interaction, constraint, assumption, guarantee, protection, implementation, verification, result, derivation, and reference relationships.

AAC-DB-DR-043
The database shall enforce or support back-end enforcement that every relationship endpoint references an existing non-deleted canonical artefact, except where querying historical baselines requires historical references.

AAC-DB-DR-044
The persistence model shall support efficient forward and backward relationship traversal.

AAC-DB-DR-045
The persistence model shall support generation of traceability matrices across requirements, components, interfaces, safeguards, implementation items, tests, and results.

AAC-DB-DR-046
The persistence model shall support impact analysis queries across upstream and downstream relationship paths.

AAC-DB-DR-047
The database shall support storage of derived graph state or query indexes where needed for performance, provided the canonical artefact and relationship records remain authoritative.

## 8. Baseline Requirements

AAC-DB-DR-050
The database shall store baseline records created by the back-end.

AAC-DB-DR-051
Each baseline shall include baseline ID, title, description, status, created-by identity, creation timestamp, eligibility result, and snapshot reference.

AAC-DB-DR-052
A baseline snapshot shall identify the exact artefact revisions and relationship revisions included in the baseline.

AAC-DB-DR-053
A baseline snapshot shall store or reference the validation state, suspect state, coverage state, and release-gate state evaluated for that baseline.

AAC-DB-DR-054
The database shall prevent a baseline from referencing non-existent artefact or relationship revisions.

AAC-DB-DR-055
The database shall support comparison between two baselines, including added, removed, and changed artefacts and relationships.

AAC-DB-DR-056
Baseline snapshots shall remain immutable after creation except for explicitly modelled lifecycle status transitions.

## 9. Validation and Issue Storage Requirements

AAC-DB-DR-060
The database shall store validation issues produced by the back-end rule engine.

AAC-DB-DR-061
Each validation issue shall store rule ID, severity, message, affected artefacts, affected relationships, baseline context where applicable, status, creation timestamp, and resolution timestamp where applicable.

AAC-DB-DR-062
The database shall support querying validation issues by artefact, relationship, rule ID, severity, status, baseline, and time range.

AAC-DB-DR-063
The database shall preserve historical validation issue records needed to explain baseline and release-gate decisions.

AAC-DB-DR-064
The database shall support replacement or supersession of validation issues when a later rule execution resolves or changes the issue state.

## 10. Suspect and Impact State Requirements

AAC-DB-DR-070
The database shall store suspect state for artefacts affected by changes to upstream released or baselined artefacts.

AAC-DB-DR-071
Each suspect state record shall store affected artefact ID, triggering event ID, reason, status, creation timestamp, and clearance metadata where applicable.

AAC-DB-DR-072
The database shall support querying suspect artefacts by component, interface, requirement, baseline, status, and trigger event.

AAC-DB-DR-073
The database shall store or expose impact analysis results containing impacted artefacts, impacted relationships, reasoning paths, and retest recommendations.

## 11. Test Result and Evidence Requirements

AAC-DB-DR-080
The database shall store normalized test result records imported through the back-end.

AAC-DB-DR-081
Each test result shall reference an existing canonical test specification.

AAC-DB-DR-082
Each test result shall reference a build, execution environment, execution timestamp, verdict, and evidence reference.

AAC-DB-DR-083
Where baseline association is required, each test result shall reference an existing baseline.

AAC-DB-DR-084
The database shall store evidence references rather than requiring evidence file content to be stored directly in the database.

AAC-DB-DR-085
The database shall support verification status aggregation by requirement, component, interface, safeguard, test specification, and baseline.

## 12. Audit Requirements

AAC-DB-DR-090
The database shall store audit events for all release-relevant operations.

AAC-DB-DR-091
Audit events shall be stored for artefact creation, artefact update, artefact deletion, relationship changes, revision creation, baseline creation, test result import, validation execution, suspect propagation, and release-gate evaluation.

AAC-DB-DR-092
Each audit event shall store event type, actor type, actor ID, timestamp, affected artefacts, affected relationships, correlation ID where applicable, and event payload.

AAC-DB-DR-093
Audit events shall be append-only under normal operation.

AAC-DB-DR-094
The database shall support querying audit events by artefact, relationship, actor, baseline, event type, and time range.

## 13. Transaction and Consistency Requirements

AAC-DB-DR-100
The database shall support transactional updates for operations that modify artefacts, relationships, revisions, validation state, baseline state, or audit state.

AAC-DB-DR-101
Artefact update, revision creation, relationship update where applicable, and audit event creation shall occur within a consistent back-end transaction or an equivalent reliable unit of work.

AAC-DB-DR-102
Baseline creation shall be transactional with respect to baseline metadata, included revision references, eligibility result, and audit event creation.

AAC-DB-DR-103
The database shall prevent partial persistence of command outcomes that would leave canonical state inconsistent.

AAC-DB-DR-104
The database shall support concurrent access from multiple front-end clients through the back-end without corrupting canonical state.

AAC-DB-DR-105
The persistence layer shall support optimistic or equivalent concurrency control for artefact and relationship updates.

## 14. Query and Reporting Requirements

AAC-DB-DR-110
The database shall support query patterns required by the back-end API, including artefact lookup, revision lookup, relationship traversal, trace chain lookup, validation issue lookup, baseline lookup, impact lookup, and audit lookup.

AAC-DB-DR-111
The database shall support report generation for traceability, consistency, coverage, baseline comparison, interface assurance, validation status, and release-gate status.

AAC-DB-DR-112
The database shall support filtering report data by component, interface, requirement type, ASIL level, lifecycle status, baseline, validation severity, and suspect status.

AAC-DB-DR-113
The database shall support machine-readable exports of canonical artefacts, relationships, validation results, baseline snapshots, impact reports, and gate results.

## 15. Security and Access Requirements

AAC-DB-DR-120
The database shall not be exposed directly to front-end clients.

AAC-DB-DR-121
All user-facing database operations shall be mediated by authenticated and authorized back-end APIs where authentication and authorization are enabled.

AAC-DB-DR-122
The database shall preserve actor identity for audited changes.

AAC-DB-DR-123
The persistence layer shall support least-privilege database credentials for application runtime and migration operations.

## 16. Backup, Restore, and Migration Requirements

AAC-DB-DR-130
The database shall support backup and restore procedures suitable for project data recovery.

AAC-DB-DR-131
The system shall provide a database migration mechanism for schema changes.

AAC-DB-DR-132
Database migrations shall be versioned.

AAC-DB-DR-133
Database migrations shall be executable in Linux deployment and CI environments.

AAC-DB-DR-134
The system shall detect database schema version mismatches at back-end startup.

AAC-DB-DR-135
The system shall fail startup or enter a safe degraded mode if the database schema version is incompatible with the running back-end version.

## 17. Performance and Scale Requirements

AAC-DB-DR-140
The database shall support MVP repositories containing at least:

- 500 requirements
- 100 software components
- 300 interface contracts
- 300 safeguards
- 1000 test specifications
- 5000 test results
- 10000 relationships
- 100 baselines

AAC-DB-DR-141
The database shall support traceability queries for a single artefact within an interactive response time suitable for front-end use under MVP-scale data.

AAC-DB-DR-142
The database shall support baseline comparison within a practical review workflow time budget under MVP-scale data.

AAC-DB-DR-143
The database shall support incremental update patterns so that ordinary artefact changes do not require full recomputation of all persisted derived states unless explicitly requested.

## 18. Database Technology Constraints

AAC-DB-DR-150
The selected database technology shall run on Linux in the supported back-end deployment environment.

AAC-DB-DR-151
The selected database technology shall support transactional integrity.

AAC-DB-DR-152
The selected database technology shall support structured queries over artefacts, relationships, revisions, baselines, validation issues, audit events, and test results.

AAC-DB-DR-153
The selected database technology shall support indexes required for relationship traversal, traceability reporting, baseline lookup, and audit queries.

AAC-DB-DR-154
The MVP database choice shall favor operational simplicity and maintainability over specialized infrastructure.

## 19. Derived Design Guidance

For MVP implementation, a relational database is the preferred default because the platform requires strong transactional behavior, revision history, baseline snapshots, auditability, and structured reporting.

Graph-style behavior shall be implemented through typed relationship tables, indexes, and a graph service in the back-end unless later scale or query complexity justifies adding a dedicated graph database.

The front-end operating system does not affect database selection because all canonical persistence is accessed through Linux-hosted back-end APIs.
