# Valkey Replacement Change Record

## Classification And Authority

- Class `D`: replaces the deployed queue-server technology and its production
  persistence allocation while preserving application protocols and contracts.
- Date: `2026-10-19`.
- User instruction: "replace Replace redis:7-alpine with Valkey. updae the
  requirements first followed by code update."
- This explicit direction approves the scoped broker requirement and selects
  Valkey as the replacement technology. It does not approve the remaining
  full-release licensing proposal or require another general licensing change.

## Gate 1: Requirements

Requirements are updated first in `requirements_baseline.md` and
`release_licensing_requirements.md`: `AAC-LIC-CR-004`, the broker scope of
`AAC-LIC-CR-011`, and new `AAC-LIC-CR-012`, derived from `NEED-LIC-003`.
Acceptance: `ACC-LIC-005`, the broker scope of `ACC-LIC-012`, and
`ACC-LIC-013`/`ACC-LIC-014`. The current user instruction is explicit approval
of this named replacement and the requested requirements-before-code sequence.

Contradiction review found `DEC-TECH-041` requires Redis 7 or later, and
`DEC-DEPLOY-002` identifies Redis as the deployed broker. These are affected
architecture decisions and must be changed at Gate 2 before code. Baseline
`AAC-EVENT-AR-012` and `AAC-VER-FR-002` now identify Valkey for the default
broker. Historical audit/build records remain dated observations.

No API payload, role, lifecycle, job state, event schema, canonical application
data, or application Python dependency is changed by the requirement delta.

## Gate 2: Architecture

After Gate 1, the controlled architecture delta updates `software_architecture.md`
and `backend_architecture_and_technology_decisions.md`. The user explicitly
selected the replacement technology and requested its implementation; that
instruction approves this scoped provider substitution. No additional queue,
client, public API, or application-data redesign is included.

| Concern / stakeholder | Approved allocation and view |
|---|---|
| Licensing / maintainer | Use `valkey/valkey:8.1.10-alpine`, a version listed by the upstream container project, with BSD-3-Clause server terms. Broader image/SBOM compliance is not claimed. |
| Client compatibility / developer | Existing `IJobQueue`, `F-JOB-01`, `F-EVT-02`, ARQ, Redis Python client, settings names, service hostname and port remain the integration boundary. |
| Deployment / operator | Existing `F-DEPLOY-01` and `IDeploymentConfiguration` select Valkey and its `valkey-cli ping` health command in both stacks and the disposable runner. Production uses fresh `valkey_data` storage. |
| Data recovery / operator | Preserve original Redis data/configuration, drain queued and in-flight work before replacement, and document verification/rollback. Never open Redis 7.4 persistence with Valkey. |
| Integrity / quality engineer | PostgreSQL remains authoritative. No schema, payload, state machine, role, audit or transaction change; compatibility and configuration checks provide evidence. |

`DEC-BROKER-001` records alternatives, trade-offs, risks and mitigation. The
runtime/deployment dependency maps now name Valkey behind the existing client
port and show its isolated production storage. There is no new dependency cycle
or application module coupling.

Both applicable approvals are satisfied by the explicit scoped request for the
named provider change. Gate 3 may now update only those allocated deployment,
test-support and operator-documentation surfaces.

## Gate 3: Implementation And Verification

Implementation follows Gates 1 and 2:

- Both Compose stacks and the disposable browser integration runner use
  `valkey/valkey:8.1.10-alpine` and `valkey-cli ping`.
- Production mounts `valkey_data:/data` instead of the original Redis volume.
  No command runs against an existing deployment or deletes/migrates its data.
- Existing service names, URLs, client packages, ARQ settings, queue/job
  contracts, PostgreSQL/upload volumes, security boundaries, and public ports
  remain unchanged.
- README, installer documentation, environment comments, and the dated audit
  follow-up identify Valkey and link the operator migration procedure.
- `documentation/valkey_migration.md` records drain, backup, isolated storage,
  verification, and rollback, including the Redis 7.4 persistence restriction.
- Added Compose compatibility/persistence regression tests and a real-Valkey
  ARQ enqueue/worker/result integration test. The disposable stack runner
  executes the broker test before migrations and the existing browser workflow.
- Traceability links `AAC-LIC-CR-004` and `AAC-LIC-CR-012` to the allocated
  functions/interfaces, changed files, and executable checks. The broader
  `AAC-LIC-CR-011` is not claimed fully implemented by this broker-only change.

### Verification Evidence

| Check | Result |
|---|---|
| `.venv/bin/pytest -q tests/test_broker_deployment.py tests/integration/test_valkey_queue.py tests/test_new_contracts.py::test_production_compose_exposes_only_tls_proxy` | 4 passed; 1 real-broker test skipped because no disposable Valkey URL was supplied. |
| Development and production `docker compose ... config --format json`, followed by parsed image/health/storage assertions | Passed without requiring daemon access; production used non-secret verification placeholders. |
| `.venv/bin/ruff check .` | Passed. |
| `git diff --check` | Passed. |
| `bash -n scripts/run_web_integration_tests.sh` | Passed. |
| `.venv/bin/python scripts/check_traceability.py --output /tmp/aac-valkey-traceability-status.json` | Zero reference/path errors. This validates links; its path-based status labels do not prove that skipped live criteria passed. |
| `bash scripts/run_web_integration_tests.sh`, initial agent execution | Blocked before containers started: Docker socket permission denied. |
| Same command, subsequently executed by the user outside the restricted agent session | Passed: Valkey pulled and started; 1 ARQ integration test passed; fresh migrations reached `0006_revision_integrity`; 1 real-stack browser test passed. See follow-up below. |

### User-Supplied Live Verification Follow-Up

Evidence recorded on `2026-10-19` from the user's terminal transcript for
`bash scripts/run_web_integration_tests.sh`. This is accepted as user-supplied
execution evidence, not represented as an agent rerun. The agent session's
Docker restriction remains unchanged.

The pulled `valkey/valkey:8.1.10-alpine` image reported registry digest
`sha256:081c2f5cb575efc901aa80ff9cdbd1ec6a301682fd35e1ebb4b0990a4a4a8507`.
This records the tested pull identity; deployment files remain tag-based and
are not silently changed to digest-pinned references by this evidence update.

- Real Valkey/ARQ test: 1 passed in 0.07 seconds. The test checks Valkey server
  identity, enqueues an isolated job, executes it with an ARQ worker, and checks
  its returned result and worker completion/failure counts.
- Fresh PostgreSQL migrations: all six revisions completed through
  `0006_revision_integrity`; initial administrator creation succeeded.
- Real API/worker browser workflow: 1 passed in 3.0 seconds. It covers login,
  project creation, evidence creation, validation submission, and visibility of
  the validation job. Its assertions do not establish that the application
  validation job reached a completed state.
- One upstream ARQ `DeprecationWarning` originated in `arq/worker.py:873`, where
  ARQ calls the Redis client's deprecated `close()` method. It did not fail the
  test. No dependency upgrade or application workaround is included.

Machine-readable evidence:
`verification/generated/valkey-replacement-results.json`.

This follow-up is Class `A`: verification/documentation only, with no product
behavioral impact. Existing requirements, acceptance definitions, architecture,
dependency maps, code, deployment configuration, and canonical application data
are unchanged. Controlling references remain Gates 1 and 2 above; the evidence
updates the observed coverage of `ACC-LIC-005` and `ACC-LIC-013` without claiming
that every obligation in those criteria passes. The earlier blocked status is
retained as historical evidence and resolved for this disposable verification
run by the supplied execution results.

### Acceptance And Completion Limits

Source configuration and the requested code/documentation replacement are
implemented. Configuration tests demonstrate the image, health command,
unchanged connection contract, internal production exposure, and isolation of
old Redis persistence (`ACC-LIC-013`/`ACC-LIC-014` configuration portions).
Operator-procedure inspection covers the documented drain/backup/rollback
portion of the broker scope in `ACC-LIC-012` and `ACC-LIC-014`.

The user's successful disposable run establishes basic live Valkey/ARQ
enqueue/execution/result compatibility, broker image pull/start, clean database
migrations, and the browser workflow described above. These resolve the
previously unexecuted disposable integration checks.

Cancellation against Valkey, completion of the browser-submitted validation
job, actual production Compose deployment, application-image content inspection,
and existing-installation upgrade/rollback verification remain unverified.
`ACC-LIC-005` is therefore only partially demonstrated; `ACC-LIC-013` has
configuration and disposable-integration evidence, not a complete production
deployment run. `ACC-LIC-012` and `ACC-LIC-014` retain their earlier inspection
coverage. Perform the documented controlled migration verification before
upgrading an existing deployment. No existing deployment was changed by this
verification follow-up.

The upstream-selected version is explicit, but registry digest pinning and
complete third-party image licensing/SBOM verification remain outside the
approved broker replacement. The other release-licensing requirements remain
proposed. Application ownership and standards-content findings are not closed
by this provider substitution.

## Sources

- Upstream image versions:
  <https://raw.githubusercontent.com/valkey-io/valkey-container/mainline/versions.json>.
- Selected version 8.1.10 server license:
  <https://raw.githubusercontent.com/valkey-io/valkey/8.1.10/COPYING>, retained in
  [LICENSES/Valkey-8.1.10.txt](../LICENSES/Valkey-8.1.10.txt).
- Protocol and persistence compatibility:
  <https://valkey.io/topics/migration/>.
