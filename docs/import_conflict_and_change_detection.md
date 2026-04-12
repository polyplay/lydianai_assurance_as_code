# Import Conflict And Change Detection Specification

## 1. Purpose

This document resolves blocker B3 identified in the implementation readiness assessment: the absence of an import change detection algorithm and conflict resolution semantics.

It supplements `import_and_versioning_state_machines.md` with the precise computational definitions for change detection, conflict identification, atomic rollback semantics, and edge-case handling.

---

## 2. Import Processing Overview

An import run processes a Sphinx-Needs JSON export document. The back-end compares each submitted object against the current canonical database state and classifies each as one of:

- `new` — no artefact with this external ID exists in the database
- `unchanged` — artefact exists and content is identical
- `changed` — artefact exists and content differs; no conflict
- `conflict` — artefact exists, content differs, and the submitted revision's base is stale
- `deleted` — artefact previously existed in this source document but is absent from this import
- `type_mismatch` — artefact exists but the submitted type does not match the stored type

---

## 3. Canonical Identity

### 3.1 Artefact Identity Key

AAC-IMPORT-FR-001
Each imported Sphinx-Needs object is identified by the compound key:

```
identity_key = (project_id, source_document, source_object_id)
```

Where:
- `project_id` is the project this import run belongs to
- `source_document` is the relative path of the `.rst` file within the Sphinx project
- `source_object_id` is the `id` field of the Sphinx-Needs directive (e.g., `SWREQ_001`)

AAC-IMPORT-FR-002
The back-end shall maintain a `source_identity` index on the `artefacts` table keyed on `(project_id, source_document, source_object_id)` to support O(1) lookup during import.

AAC-IMPORT-FR-003
Two artefacts from different source documents with the same `source_object_id` shall be treated as distinct artefacts if their `source_document` differs.

### 3.2 Content Fingerprint

AAC-IMPORT-FR-010
The back-end shall compute a content fingerprint for each imported object and each stored artefact revision to detect changes.

AAC-IMPORT-FR-011
The content fingerprint shall be computed as:

```python
import hashlib, json

def compute_fingerprint(canonical_fields: dict) -> str:
    """
    canonical_fields: the normalized field dict produced by the Sphinx-Needs mapper,
    excluding system-managed fields (artefact_id, revision_id, created_at,
    updated_at, import_run_id, fingerprint itself).
    """
    # Sort keys for deterministic serialization
    serialized = json.dumps(canonical_fields, sort_keys=True, ensure_ascii=True)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()
```

AAC-IMPORT-FR-012
The fingerprint shall be computed over the normalized canonical field representation, not the raw Sphinx-Needs JSON. Normalization (type mapping, field mapping, default injection) is applied before fingerprinting.

AAC-IMPORT-FR-013
The stored fingerprint of an artefact revision shall be the fingerprint computed at the time of that revision's creation. It shall be stored in the `artefact_revisions` table as `content_fingerprint`.

AAC-IMPORT-FR-014
The `artefacts` table shall store the `current_fingerprint` of the current (active) revision to avoid joining to `artefact_revisions` during import comparison.

---

## 4. Change Classification Algorithm

For each submitted Sphinx-Needs object in an import run, the back-end shall execute the following classification:

```
INPUT:
  submitted_object: normalized canonical field dict (produced by Sphinx-Needs mapper)
  project_id: string
  import_run_id: string

STEP 1 — Identity lookup:
  existing = db.lookup_by_source_identity(
    project_id,
    submitted_object.source_document,
    submitted_object.source_object_id
  )

STEP 2 — Classify:
  if existing is None:
    classification = "new"

  elif existing.artefact_type != submitted_object.artefact_type:
    classification = "type_mismatch"

  elif existing.current_fingerprint == compute_fingerprint(submitted_object.fields):
    classification = "unchanged"

  elif submitted_object.base_revision_id is None:
    # No base revision declared — treat as non-conflicting change
    classification = "changed"

  elif existing.current_revision_id == submitted_object.base_revision_id:
    # Submitted object was based on the current stored revision
    classification = "changed"

  else:
    # Submitted object was based on a revision that is no longer current
    # (i.e., the stored artefact has advanced since the author last synced)
    classification = "conflict"

OUTPUT: classification ∈ {new, unchanged, changed, conflict, type_mismatch}
```

### 4.1 The `base_revision_id` Field

AAC-IMPORT-FR-020
The Sphinx-Needs JSON export may optionally include a `_aac_base_revision_id` field on each needs object. This field is set by the platform when it exports canonical artefact state back to Sphinx documentation.

AAC-IMPORT-FR-021
If `_aac_base_revision_id` is absent from a submitted object, the back-end shall treat the import as not declaring a base revision (non-conflicting change when content differs). This is the expected case for first-time imports from existing Sphinx documentation.

AAC-IMPORT-FR-022
If `_aac_base_revision_id` is present and does not match the current stored revision ID, the import shall be classified as `conflict`.

---

## 5. Conflict Handling

AAC-IMPORT-FR-030
The behavior on `conflict` classification depends on the project's `version_update_mode` configuration:

| Configuration | Conflict Handling |
|---|---|
| `automatic_new_version` | Treat conflict as `changed`; create new revision; log a warning-level audit event noting the stale base |
| `ask_user` | Pause the import job; emit `import.decision_required` event; require user decision |

AAC-IMPORT-FR-031
In `ask_user` mode, when a conflict is detected, the import job shall transition to `waiting_for_user` state. Processing of other artefacts in the same import run shall continue, but no revision shall be created for conflicting artefacts until a decision is received.

AAC-IMPORT-FR-032
The user decision for each conflict shall be one of:

- `accept_new_version`: Create a new revision with the submitted content. The stale base is logged in the audit event.
- `reject_keep_current`: Discard the submitted content. The current stored revision remains active. The ImportRunItem shall record `rejected_by_user`.

AAC-IMPORT-FR-033
After all decisions are submitted, the import job shall resume processing and complete.

---

## 6. Deleted Artefact Handling

AAC-IMPORT-FR-040
An artefact is considered deleted from a source document if:
- It was previously imported from `source_document`
- It does not appear in the current import submission from that same document
- The import run's `source_document` matches (i.e., deletions are document-scoped, not project-scoped)

AAC-IMPORT-FR-041
Deleted artefacts shall be soft-deleted (lifecycle status → `obsolete`) rather than physically removed.

AAC-IMPORT-FR-042
Before soft-deleting an artefact, the back-end shall check whether the artefact is:
- Referenced in any active baseline (revision snapshot)
- A source or target of any active relationship

AAC-IMPORT-FR-043
If the artefact is in an active baseline, soft-deletion shall proceed but shall create a validation issue of severity `major` indicating the artefact is referenced in a baseline while marked obsolete.

AAC-IMPORT-FR-044
If the artefact has active relationships, soft-deletion shall proceed but all outgoing and incoming relationships shall be soft-deleted simultaneously, triggering `relationship.deleted` events for each.

AAC-IMPORT-FR-045
Soft-deletion of an artefact shall emit `artefact.deleted` and `artefact.status_changed` (→ obsolete) domain events.

---

## 7. Type Mismatch Handling

AAC-IMPORT-FR-050
If a submitted object's Sphinx-Needs type maps to a different canonical artefact type than the stored artefact, this is a `type_mismatch`.

AAC-IMPORT-FR-051
Type mismatches shall never be automatically resolved. They shall always create an import error recorded in the `ImportRunItem` with classification `type_mismatch` and no artefact update.

AAC-IMPORT-FR-052
The import run shall complete with an overall status of `completed_with_errors` if any type mismatches occurred.

AAC-IMPORT-FR-053
The user must manually resolve a type mismatch by either:
- Correcting the Sphinx-Needs type in the source document and re-importing
- Administratively deleting the stored artefact (if it was an error) and re-importing

---

## 8. Atomic Transaction Semantics

AAC-IMPORT-FR-060
The import pipeline shall process artefacts and relationships in batches. Each batch shall be wrapped in a single database transaction.

AAC-IMPORT-FR-061
The default batch size shall be 50 artefacts per transaction.

AAC-IMPORT-FR-062
If a batch transaction fails due to a database error, the transaction shall be rolled back completely. No partial state from that batch shall persist.

AAC-IMPORT-FR-063
Subsequent batches shall continue processing unless the error was fatal (e.g., database connection lost).

AAC-IMPORT-FR-064
The `ImportRun` record shall track `last_committed_batch_index` so that a resumed import (after a fatal failure) can skip already-committed batches.

AAC-IMPORT-FR-065
Relationship imports shall be processed after all artefact imports complete (to ensure source and target artefacts exist before relationship creation).

AAC-IMPORT-FR-066
The `import.completed` domain event shall only be emitted after all batches, including relationship batches, have committed successfully.

---

## 9. Post-Import Processing

AAC-IMPORT-FR-070
After all artefact and relationship batches commit, the back-end shall:

1. Update the `ImportRun` record with final counts (created / revised / unchanged / deleted / conflicts / errors)
2. Update `ImportRun.status` to `completed`, `completed_with_errors`, or `waiting_for_user`
3. Emit `import.completed` domain event (if not `waiting_for_user`)
4. The `import.completed` consumer enqueues a validation run (execution mode = `import`) for the project

AAC-IMPORT-FR-071
In `ask_user` mode with pending decisions, post-import processing (validation run, audit events) shall be deferred until after all user decisions are resolved and the import job resumes.

---

## 10. Import Run Item Schema

Each `ImportRunItem` record captures the per-artefact outcome:

```json
{
  "import_run_item_id": "string",
  "import_run_id": "string",
  "source_object_id": "string",
  "source_document": "string",
  "artefact_type": "string",
  "classification": "new | unchanged | changed | conflict | deleted | type_mismatch | error",
  "artefact_id": "string or null",
  "previous_revision_id": "string or null",
  "new_revision_id": "string or null",
  "decision": "accepted | rejected_by_user | pending_decision | not_applicable",
  "error_message": "string or null",
  "fingerprint_submitted": "string",
  "fingerprint_stored_before": "string or null"
}
```
