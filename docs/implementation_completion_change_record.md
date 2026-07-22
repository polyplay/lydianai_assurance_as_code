# Implementation Completion Change Record

## Classification And Approval

- Change class: `Class D`
- Date: `2026-06-13`
- Approval: the user explicitly requested implementation after the requirements,
  architecture, findings, and implementation sequence were reviewed.
- Controlling requirements: `requirements_baseline.md`,
  `mvp_acceptance_criteria.md`, and the detailed specifications under `docs/`.
- Controlling architecture: `software_architecture.md`.

## Scope

This change completes the approved blocker sequence:

- immutable artefact and relationship revision chains with schema version and
  audit linkage;
- optimistic concurrency tokens for mutable evidence records;
- transactional audit/outbox coverage for governing mutations;
- standard API error envelopes, explicit CORS, and bounded streaming input;
- production TLS termination and internal-only database, Redis, and API ports;
- consistent baseline comparison inputs across API, web, and CLI;
- operational CLI parity;
- deterministic requirements/acceptance inventory, database recovery,
  backup/restore, deployed workflow, and performance evidence.

## Architecture Delta

The existing `F-ART-01`, `F-ART-02`, `F-REL-01`, `F-EVT-01`, `F-GATE-02`,
`F-API-01`, `F-WEB-01`, `F-CLI-01`, and `F-VER-01` allocations remain
authoritative. The architecture now also defines:

- `F-VER-02` for complete status inventory;
- `F-PERF-01` for deterministic seed and benchmark evidence;
- `F-DEPLOY-01` for production TLS and network isolation;
- `IVerificationInventory` and `IDeploymentConfiguration`.

The dependency direction remains presentation/deployment adapters to API and
application interfaces, then ports and persistence. Verification tooling reads
controlled specifications and evidence; it does not mutate product state.

## Decisions And Trade-offs

1. Revision predecessors are persisted as self-referencing foreign keys.
   Revision 1 has no predecessor; every later revision points to the prior
   immutable revision.
2. Lifecycle changes append revisions instead of changing only the mutable
   current projection.
3. Import and evidence limits are enforced while streaming. This adds bounded
   temporary-file I/O for uploads and avoids unbounded memory use.
4. Production installation requires operator-supplied TLS material. Automatic
   self-signed production certificates were rejected because they do not
   establish a trusted service identity.
5. The status inventory reports uncovered IDs as `missing`. It does not infer
   implementation from prose or silently treat absent evidence as complete.
6. Performance evidence uses a fixed seed and database-path measurements.
   Deployed browser/API behavior is verified separately against PostgreSQL and
   Redis.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Existing clients omit revision tokens | Standard 422/409 errors, updated web and CLI clients, contract tests |
| Migration runs on fresh metadata-created databases | Introspection-safe column and foreign-key creation |
| Governing mutations leave passed gates apparently current | Blocking-event registry plus release-time outbox sequence guard |
| Oversized chunked input bypasses `Content-Length` | Count bytes while streaming |
| Production service starts with development secrets | Runtime fail-closed validation |
| Documentation coverage is overstated | Generated inventory explicitly records 639 missing requirements and 126 missing acceptance criteria |

## Verification Evidence

The controlled evidence manifest is
`verification/release_evidence.yaml`. Generated results are under
`verification/generated/`.

- Backend: 122 passed; 3 integration tests skipped in the ordinary suite.
- PostgreSQL integration: 3 passed, including database fault injection,
  concurrent release ordering, and revision-chain persistence.
- Web unit: 6 passed.
- Browser workflows: 11 passed.
- Deployed PostgreSQL/Redis browser workflow: 1 passed.
- Clean migration through `0006_revision_integrity`: passed.
- Full PostgreSQL backup and restore: passed.
- Performance seed: 6,500 artefacts, 10,000 relationships, 5 baselines, and
  50,000 audit events.
- All five measured P95 performance targets passed.
- Live local stack: healthy on `http://127.0.0.1:18080/app/`, database at
  migration head `0006_revision_integrity`.
