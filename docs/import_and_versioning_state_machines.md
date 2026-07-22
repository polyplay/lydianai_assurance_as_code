# Import And Versioning State Machines

## 1. Purpose

This document defines the import and versioning behavior for Sphinx-authored artefacts imported into the back-end.

The back-end owns canonical truth. Sphinx documents are authoring inputs.

## 2. Configuration

AAC-VERSION-FR-001
The project configuration shall define `version_update_mode`.

Allowed values:

- `automatic_new_version`
- `ask_user`

AAC-VERSION-FR-002
In `automatic_new_version` mode, every accepted content change shall create a new revision automatically.

AAC-VERSION-FR-003
In `ask_user` mode, detected changes shall require user decision before revision creation.

AAC-VERSION-FR-004
Unchanged imported artefacts shall not create new revisions.

## 3. Import Run States

AAC-IMPORT-DR-001
An import run shall use these states:

- `created`
- `payload_received`
- `parsed`
- `parse_failed`
- `normalized`
- `normalization_failed`
- `changes_detected`
- `no_changes_detected`
- `waiting_for_user`
- `persisting`
- `persisted`
- `validation_running`
- `completed`
- `completed_with_errors`
- `completed_no_changes_applied`
- `failed`
- `cancelled`

## 4. Import Run Transitions

AAC-IMPORT-DR-010
The normal automatic flow shall be:

```text
created
payload_received
parsed
normalized
changes_detected
persisting
persisted
validation_running
completed
```

AAC-IMPORT-DR-011
The unchanged flow shall be:

```text
created
payload_received
parsed
normalized
no_changes_detected
completed_no_changes_applied
```

AAC-IMPORT-DR-012
The ask-user flow shall be:

```text
created
payload_received
parsed
normalized
changes_detected
waiting_for_user
persisting
persisted
validation_running
completed
```

AAC-IMPORT-DR-013
If a user rejects changes in `ask_user` mode, the flow shall be:

```text
waiting_for_user
completed_no_changes_applied
```

AAC-IMPORT-DR-014
Parse or normalization failures shall transition to `failed`.

AAC-IMPORT-DR-015
An import with non-fatal item errors after all processable batches complete
shall transition to `completed_with_errors`.

## 5. Version Conflict States

AAC-VERSION-DR-010
Artefact version evaluation shall use these states:

- `new_artefact`
- `existing_artefact_loaded`
- `incoming_compared`
- `unchanged`
- `changed_detected`
- `decision_required`
- `accepted_new_revision`
- `rejected_keep_current`
- `stale_source_detected`
- `conflict_error`

## 6. Version Decision Logic

AAC-VERSION-FR-010
If no stored artefact exists for an imported object ID, the back-end shall create revision 1.

AAC-VERSION-FR-011
If the imported canonical payload equals the current stored revision, the back-end shall report `unchanged`.

AAC-VERSION-FR-012
If the imported canonical payload differs from the current stored revision and mode is `automatic_new_version`, the back-end shall create a new revision.

AAC-VERSION-FR-013
If the imported canonical payload differs from the current stored revision and mode is `ask_user`, the back-end shall return a decision request.

AAC-VERSION-FR-014
If the user accepts the decision request, the back-end shall create a new revision.

AAC-VERSION-FR-015
If the user rejects the decision request, the back-end shall keep the current stored revision active.

AAC-VERSION-FR-016
If the import payload declares a base revision that is older than the current stored revision, the back-end shall flag stale source or conflict according to project policy.

## 7. Import Run Output

AAC-IMPORT-IR-001
An import run status response shall include:

```json
{
  "import_run_id": "IMP_RUN_001",
  "project_id": "PROJ_001",
  "state": "waiting_for_user",
  "version_update_mode": "ask_user",
  "summary": {
    "new": 1,
    "changed": 2,
    "unchanged": 4,
    "failed": 0
  },
  "decision_items": [
    {
      "source_object_id": "REQ_SW_001",
      "artefact_id": "REQ_SW_001",
      "current_revision": 3,
      "proposed_revision": 4,
      "change_summary": {}
    }
  ]
}
```

## 8. Audit Requirements

AAC-IMPORT-FR-090
Each import run shall create an audit event.

AAC-IMPORT-FR-091
Each created revision shall reference the import run that caused it.

AAC-IMPORT-FR-092
Rejected updates shall be auditable without modifying canonical artefact state.
