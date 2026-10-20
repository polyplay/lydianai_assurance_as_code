# Release Licensing Remediation Change Record

## Classification And Request

- Date: `2026-10-19`.
- Class: `D`; the requested closure can replace the deployed broker and changes
  release build/distribution interfaces, dependency controls, and verification.
- Request: "can you fix all these issues?", referring to Redis licensing,
  dependency obligations, inventories/notices, reproducibility, ownership, and
  actual container verification.
- Earlier Class C application-license adoption remains a separate completed
  change; its runtime/dependency preservation statement described that adoption.
- Requirements authority: `requirements_baseline.md` and
  `release_licensing_requirements.md`; acceptance authority:
  `mvp_acceptance_criteria.md`.

## Gate 1: Requirements Delta

The proposed requirements add stakeholder needs `NEED-LIC-002` through
`NEED-LIC-004`, stakeholder/system requirements `AAC-LIC-SR-001` and
`AAC-LIC-SY-001`, software constraints `AAC-LIC-CR-004` through
`AAC-LIC-CR-011`, interface requirement `AAC-LIC-IR-002`, and acceptance
criteria `ACC-LIC-005` through `ACC-LIC-012`.

`AAC-LIC-CR-003` is clarified to distinguish the original license adoption's
no-runtime-change scope from subsequent approved release remediations.
The obligation to preserve third-party licenses and notices is retained.
No requirement ID is removed or reused.

| Gap | Requirement allocation at the requirements level | Acceptance |
|---|---|---|
| Default broker license | `AAC-LIC-CR-004`, `AAC-LIC-CR-011` | `ACC-LIC-005`, `ACC-LIC-012` |
| LGPL/MPL and other component obligations | `AAC-LIC-CR-007` | `ACC-LIC-008` |
| Complete inventory and recipient materials | `AAC-LIC-IR-002`, `AAC-LIC-CR-006` | `ACC-LIC-007`, `ACC-LIC-008` |
| Reproducible release inputs | `AAC-LIC-CR-005` | `ACC-LIC-006` |
| Ownership and source provenance | `AAC-LIC-CR-008` | `ACC-LIC-009` |
| Actual image and release verification | `AAC-LIC-CR-009`, `AAC-LIC-CR-010` | `ACC-LIC-010`, `ACC-LIC-011` |

### Contradiction And Impact Review

The controlled `docs/`, operational `documentation/`, verification records,
package manifests, installer files, and source references were searched for
overlapping licensing, copyright, broker, release, and reproducibility rules.

| Surface | Finding and required treatment |
|---|---|
| `requirements_baseline.md`, initial `AAC-LIC-CR-003` | Clarify initial-adoption scope explicitly; retain third-party obligations and prior IDs. |
| `backend_architecture_and_technology_decisions.md` | `DEC-TECH-041` names Redis 7 or later, and `DEC-DEPLOY-002` names its service. A substitute requires an explicit architecture delta and approval; none is selected at Gate 1. |
| `software_architecture.md`, queue/event/job documents | PostgreSQL owns durable job state; broker remediation must preserve application ports, protocol, state machines, and events. Review broker views and dependency maps at Gate 2. |
| Runtime manifests, package locks, Docker/Compose, web integration script | Release inputs are not fully locked and the default broker image is mutable. Any production edit waits for both applicable approvals. |
| Installer, environment examples, manuals | Broker settings, CLI/health behavior, upgrades, recipient materials, and build procedures need coordinated review at Gate 2. |
| `dependency_license_audit.md` and initial adoption record | Preserve historical results. New findings cannot be closed by changing old scan dates or claiming that metadata proves distribution compliance. |
| API/data schemas, authorization, lifecycle state machines | Existing contracts remain controlling; no new application behavior is requested. |
| Traceability and release evidence | Allocate the new requirements to approved architecture and executable checks after their gates; do not record proposed inspections as verified. |

The new requirements specify release outcomes rather than selecting a broker,
scanner, lock generator, or build mechanism. The baseline remains authoritative
for scope, and actual third-party license texts remain authoritative for terms.

### Read-Only Feasibility Findings

- Both Compose stacks and the web integration runner reference `redis:7-alpine`.
- The current Python environment contains LGPL `psycopg` and `psycopg-binary`
  and MPL `certifi`; migration configuration explicitly uses the psycopg
  SQLAlchemy driver. Removing that dependency would affect migrations.
- These three installed distributions already contain upstream license files.
  The outstanding work is complete release coverage and obligation evidence;
  their presence is not evidence that those license files are missing.
- Installed dependency versions differ from the older audit snapshot, confirming
  that its versions must not be treated as the current release inventory.
- Valkey's upstream `COPYING` declares BSD-3-Clause. It is a candidate for the
  broker requirement, not an approved architecture decision.
- Valkey's migration guidance states that Redis CE 7.4 and later persistence
  files are incompatible. The previously observed Redis 7.4.8 data must not be
  assumed safe to open in a replacement broker. This informs
  `AAC-LIC-CR-011` and must be resolved in the architecture/upgrade design.
- Git history lists six commits by `polyplay`. This is authorship evidence,
  not copyright ownership or permission evidence. No source-header origin
  notices were found by the initial search; absence is not proof of ownership.
- Docker CLI `29.1.3` is present, but daemon access failed with
  `permission denied while trying to connect to the docker API at unix:///var/run/docker.sock`.
  No actual image build/inspection can be claimed from that environment state.

### Decisions And Inputs Pending

- Explicit requirements approval under `GOV-GATE-003` and `AAC-GOV-FR-010`.
- Rights-holder name, authority confirmation, and any exceptions. Requested
  from the user; not inferred from the Git author or application brand.
- Actual Docker daemon access for image execution, or equivalent verified
  externally produced build evidence. The current denial is recorded as a
  verification limit, not a successful check.

Requirements approval: **pending**. No production dependency, broker, lock,
deployment, or release-tool implementation has changed for this Class D scope.

### Scoped Valkey Approval

The later user instruction explicitly requests replacement of `redis:7-alpine`
with Valkey, requirements first and code afterward. This approves only
`AAC-LIC-CR-004`, the broker scope of `AAC-LIC-CR-011`, and the explicit
compatibility requirement `AAC-LIC-CR-012`, with `ACC-LIC-005`, the broker
scope of `ACC-LIC-012`, and `ACC-LIC-013`/`ACC-LIC-014`. The original pending
status above describes the broader six-gap proposal and its investigation
date; it does not prevent this subsequently authorised subset from proceeding.

The sequential requirements, architecture, and implementation deltas for that
subset are controlled in `valkey_replacement_change_record.md`. Other release
requirements and unrelated licensing findings remain pending. Earlier Redis
architecture decisions are updated by that scoped change rather than being
silently treated as already compatible with a different server implementation.

### Requirements Verification

- `git diff --check`: passed.
- Executed a requirements-document inspection: all 11 new requirements have
  unique stable IDs, explicit StRS/SyRS/SRS levels, and constraint/interface
  types; all eight new acceptance criteria occur exactly once.
- No runtime tests or image checks are claimed at this gate. Production
  architecture, code, deployment, and application data remain unchanged by
  this Class D requirements delta.

## Gate 2: Architecture

Pending requirements approval. This gate must allocate functions and interfaces,
update dependency/runtime/deployment views, define evidence schemas and release
inputs, record the selected options and alternatives, address broker data
compatibility, and obtain architecture approval before implementation.

## Gate 3: Implementation And Verification

Pending the preceding approvals. No release-licensing gap is marked closed by
this proposed requirements artifact. Requirements/documentation inspection is
the only verification applicable to the current gate.

## Source References

- Valkey's actual upstream license:
  <https://raw.githubusercontent.com/valkey-io/valkey/unstable/COPYING>.
- Valkey migration and persistence compatibility:
  <https://valkey.io/topics/migration/>.
- Redis version-specific licensing:
  <https://redis.io/legal/licenses/>.
- Mozilla's distribution FAQ:
  <https://www.mozilla.org/en-US/MPL/2.0/FAQ/>.
- SPDX specification:
  <https://spdx.github.io/spdx-spec/v2.3.1/>.
