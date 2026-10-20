# Licensing Reference Update Change Record

Date: `2026-10-20`.

## Classification And Requirements Gate

Class `B`: complete the already approved application/broker licensing notices
and reference coverage. The application remains Apache-2.0 and the Valkey server
remains BSD-3-Clause. No license grant, runtime behavior, dependency version,
public API, or application-data contract changes. The explicit user request to
update licenses and their references authorises this covered maintenance work.

Controlling requirements: `AAC-LIC-CR-001`, `AAC-LIC-IR-001`,
`AAC-LIC-CR-002`, `AAC-LIC-CR-003`, and the approved broker-license portion of
`AAC-LIC-CR-004`. Acceptance: `ACC-LIC-001` through `ACC-LIC-004` for source,
metadata, distribution and scope inspections, plus only the license-reference
portion of `ACC-LIC-005`. No new or changed normative requirements are needed.

Affected surfaces: README, operational documentation, dated dependency audit,
license text/reference files, Python license-file packaging, and the backend
image's inclusion of those informational files. Historical audit and initial
adoption results remain historical; earlier verification is not rewritten as a
fresh image or dependency scan.

The contradiction review found that the audit's conditional license-strategy
discussion still presents Redis as the current strategic concern despite the
approved Valkey replacement. Current guidance will identify Apache-2.0 and
Valkey BSD-3-Clause, with the Redis terms confined to historical/legacy use.

## Architecture Gate

Existing `F-VER-01` evidence responsibility and the distribution mechanisms
assessed in `app_licensing_change_record.md` remain controlling. Setuptools
license-file metadata and existing Docker COPY instructions include the updated
notices. No function, runtime interface, data owner, dependency direction,
state machine, technology, deployment topology, or dependency map changes.
The architecture gate closes by this impact assessment without a new decision.

The preserved Valkey license text contains upstream attribution for both Valkey
contributors and Redis Ltd.; retained Redis copyright is not a dependency on the
replaced Redis 7 server. No first-party copyright holder is invented.

## Implementation And Verification

Implemented after the requirements and architecture assessments above:

- Retained canonical root `LICENSE` and all three Python/npm/root-lock
  `Apache-2.0` declarations.
- Added `LICENSES/Valkey-8.1.10.txt`, reproducing both upstream BSD-3-Clause
  copyright/license blocks from the exact selected version.
- Added `THIRD_PARTY_NOTICES.md` to identify application/broker license scope,
  preserve Valkey attribution, and identify selected LGPL/MPL dependencies
  without claiming a complete third-party inventory.
- Updated README, documentation index, installer README, migration guide, and
  dependency audit links. Replaced the audit's obsolete conditional license
  strategy with current Apache-2.0/Valkey guidance while retaining historical
  dependency versions and legacy Redis findings.
- Included the notice and mirrored server license in Python license-file
  metadata and the backend Docker COPY recipe. No server or client dependency
  was changed.
- Linked the changed artifacts and this controlled inspection to the existing
  licensing entries in `verification/requirements_traceability.yaml`.

### Verification

Evidence: `verification/generated/licensing-reference-results.json`.

| Check | Result |
|---|---|
| Canonical application license | Unchanged; SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`. |
| Python/npm/root-lock license parsing | All remain `Apache-2.0`. |
| Valkey license comparison | All 28 lines match the exact-version plaintext source retrieved with the web tool; both copyright blocks retained. Local SHA-256: `73d13bd815e091f71a983696af92b09f8d8e3f7179f9a15825cc8434c153ed76`. |
| Local documentation/notice references | 32 links checked; all targets exist. |
| Actual source distribution and wheel | Built a source archive, then a wheel from its extracted contents. Both include byte-identical `LICENSE`, `THIRD_PARTY_NOTICES.md`, and `LICENSES/Valkey-8.1.10.txt`, with matching `License-File` entries and `License-Expression: Apache-2.0`. |
| Backend image recipe | Copies the application license, notices and `LICENSES` directory to `/app`; actual image not rebuilt. |
| `git diff --check` and `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/python scripts/check_traceability.py --output /tmp/aac-license-references-traceability-status.json` | Passed with zero reference/path errors; path-based status is not treated as proof of unrelated acceptance. |

Archive builds ran offline in `/tmp/aac-license-references-m9cohnc5`, using the
previously isolated build environment at `/tmp/aac-licensing-eeqrjaxz/venv`.
Source inputs were copied from this working tree. Build logs and archives remain
under that inspection directory; hashes are recorded in the JSON evidence.
The shell's raw upstream download failed due to restricted DNS; the successful
upstream-text comparison instead used the web tool's exact-version plaintext
response with its source-line prefixes removed.

These inspections demonstrate the affected source/metadata/archive/reference
portions of `ACC-LIC-001` through `ACC-LIC-004` and the Valkey license-reference
portion of `ACC-LIC-005`. No additional live broker test is needed for this
informational-file/reference maintenance. Existing user-supplied broker
verification remains in `verification/generated/valkey-replacement-results.json`.

### Completion Review

The covered Class B update is complete. No requirement or acceptance definition
changed. Outdated conditional license-strategy references are superseded by the
approved application and broker decisions; dated audit observations remain
distinguishable. Architecture functions, interfaces and dependency maps are
unaffected; runtime code, runtime dependencies and application data are unchanged.

Remaining scope: these targeted notices do not establish a complete third-party
SBOM, source-availability compliance, ownership confirmation, or actual rebuilt
backend-image content verification.

## Controlling Sources

- Application terms: <https://www.apache.org/licenses/LICENSE-2.0>.
- Exact selected Valkey version:
  <https://raw.githubusercontent.com/valkey-io/valkey/8.1.10/COPYING>.
