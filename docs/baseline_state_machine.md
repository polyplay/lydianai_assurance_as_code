# Baseline State Machine

## 1. Purpose

This document defines baseline behavior.

A baseline is a manual snapshot of project artefact and relationship revisions. The platform supports multiple projects in parallel.

## 2. Roles

AAC-BASE-FR-001
Baseline creation may be triggered by:

- Admin
- Project Lead

AAC-BASE-FR-002
The User role may view baselines and query baseline-derived reports.

AAC-BASE-FR-003
The User role shall not delete, obsolete, approve, release, or create baselines.

AAC-BASE-FR-004
Admin may mark a baseline obsolete.

AAC-BASE-FR-005
Project Lead may create baselines for projects assigned to them.

AAC-BASE-FR-006
Project Lead or Admin may approve a created baseline only after a current
release-gate pass.

AAC-BASE-FR-007
Quality Engineer or Admin may release an approved baseline only while the latest
release-gate pass remains current.

## 3. Project Scope

AAC-BASE-FR-010
Each baseline shall belong to exactly one project.

AAC-BASE-FR-011
Baseline creation shall snapshot all selected artefacts and relationships belonging to the project scope.

AAC-BASE-FR-012
A baseline shall reference exact artefact revision IDs and relationship revision IDs.

AAC-BASE-FR-013
The system shall support multiple project baselines in parallel.

## 4. Update Lock During Baselining

AAC-BASE-FR-020
The system shall block artefact and relationship updates for a project while baseline creation is in progress for that project.

AAC-BASE-FR-021
Read operations shall remain available during baseline creation.

AAC-BASE-FR-022
The MVP shall not define a separate scheduler priority policy for reads during baseline creation.

AAC-BASE-FR-023
The update lock shall be project-scoped, not global across all projects.

## 5. Baseline States

AAC-BASE-DR-001
A baseline shall use these states:

- `requested`
- `update_lock_acquired`
- `eligibility_check_running`
- `eligibility_failed`
- `creating_snapshot`
- `created`
- `approved`
- `released`
- `obsolete`
- `failed`
- `cancelled`

## 6. Baseline Transitions

AAC-BASE-DR-010
The normal creation flow shall be:

```text
requested
update_lock_acquired
eligibility_check_running
creating_snapshot
created
```

AAC-BASE-DR-011
The failed eligibility flow shall be:

```text
requested
update_lock_acquired
eligibility_check_running
eligibility_failed
```

AAC-BASE-DR-012
A created baseline may transition to `approved`.

AAC-BASE-DR-013
An approved baseline may transition to `released`.

AAC-BASE-DR-013A
If an approved baseline's release-gate result becomes stale, approval shall be
invalidated and the baseline shall transition back to `created`.

AAC-BASE-DR-014
Admin may transition a baseline to `obsolete`.

AAC-BASE-DR-015
Failed or cancelled baseline creation shall release the project update lock.

## 7. Baseline Snapshot Contents

AAC-BASE-DR-020
A baseline snapshot shall include:

- project ID
- baseline ID
- baseline title
- baseline status
- created by
- created at
- selected scope
- included artefact revisions
- included relationship revisions
- profile used
- tailoring decisions applied
- validation summary
- coverage summary
- suspect summary
- release-gate result
- audit event references

## 8. Baseline Eligibility

AAC-BASE-FR-030
The back-end shall evaluate baseline eligibility before snapshot creation.

AAC-BASE-FR-031
Baseline creation shall fail if critical blocking issues exist in the selected scope.

AAC-BASE-FR-032
Baseline creation shall report all blocking issues to the requester.

AAC-BASE-FR-033
No partial baseline snapshot shall be created if eligibility fails.
