# Application Licensing Change Record

## Classification And Scope

- Date: `2026-10-19`.
- Change class: `Class C`. Selecting the application license adds an externally
  observable distribution contract without changing runtime behavior. The higher
  plausible class is used instead of treating license documents as editorial.
- Request: "put a Apache 2.0 licence on the app code" and update requirements
  before application updates.
- Stakeholders: maintainers who distribute the application and recipients who
  need explicit reuse terms (`NEED-LIC-001`).
- Scope: the project's own application code, source license, package licensing
  metadata, distribution of the license text, and supporting documentation.
- Third-party dependencies and service images retain their own licenses.

## Gate 1: Requirements

The requirements delta adds `AAC-LIC-CR-001`, `AAC-LIC-IR-001`,
`AAC-LIC-CR-002`, and `AAC-LIC-CR-003` to `requirements_baseline.md`, with
`ACC-LIC-001` through `ACC-LIC-004` in `mvp_acceptance_criteria.md`.
All are SRS constraints or interface requirements derived from `NEED-LIC-001`.
No existing requirement is removed or superseded.

Document impact and contradiction review:

| Controlled surface | Assessment |
|---|---|
| Requirements baseline and acceptance criteria | Add the explicit application licensing contract and objective distribution checks. |
| README and package manifests | Currently contain no application license declaration; update after requirements approval and architecture assessment. |
| `dependency_license_audit.md` | Its `2026-10-02` observation of a missing application license is historical. Add a dated follow-up after implementation; preserve dependency findings. |
| Software architecture and technology decisions | Assess at Gate 2 after requirements approval. |
| API, data schemas, state machines, authorization, security, and operational deployment contracts | No product behavior changes are requested; their existing requirements remain authoritative. |
| Requirements traceability | Add licensing-to-distribution-artifact and controlled-inspection links at implementation completion. |

A search across controlled `docs/`, operational `documentation/`, verification
records, application code, and package manifests found no existing conflicting
application license grant. References to licensed standards and dependency
licenses do not grant a license for application code. The requirements baseline
controls application licensing scope; `LICENSE` will contain the license terms.

Requirements approval: on `2026-10-19`, after the requirements delta was
presented for approval, the user instructed: "update the app now based on the
requirements". This explicitly authorizes the recorded licensing scope under
`GOV-GATE-003` and `AAC-GOV-FR-010`.

## Gate 2: Architecture

Controlling requirements: Gate 1 above. Controlling architecture:
`software_architecture.md`, including existing `F-VER-01` release-evidence
responsibility. The architecture gate closes with this impact assessment:
runtime component responsibilities, application interfaces, data ownership,
state machines, technology selection, and deployment topology are unaffected.
No additional architecture approval is required under `GOV-GATE-003`.

Stakeholder concerns and views:

| Stakeholder / concern | View and assessment |
|---|---|
| Maintainer / consistent distribution | Existing setuptools, npm manifests, and Docker build recipe carry the same license declaration and text. |
| Recipient / usable license terms | Source, Python archives, and backend images include the complete license; README identifies the scope. |
| Developer / change isolation | No backend or browser runtime modules change. The existing setuptools backend remains; its build-only minimum becomes `77.0.3` to support PEP 639 license metadata. Runtime dependencies stay unchanged. |
| Quality engineer / traceability | Existing `F-VER-01` produces controlled inspection evidence for all four licensing criteria. |

Allocation and distribution contract:

| Requirements | Existing artifact owner / provider | Inputs and outputs | Verification owner |
|---|---|---|---|
| `AAC-LIC-CR-001` | Maintainer; root `LICENSE` and README | Official Apache text becomes the source license and linked application declaration. | `F-VER-01`, `INS-LIC-001` |
| `AAC-LIC-IR-001` | Existing Python and JavaScript package manifests | Python `project.license` and JavaScript root `license` are `Apache-2.0`; Python `project.license-files` includes `LICENSE`; root lock entry agrees. | `F-VER-01`, `INS-LIC-002` |
| `AAC-LIC-CR-002` | Existing setuptools and Docker build recipes | Root `LICENSE` is included unchanged in source distributions, wheel license data, and `/app/LICENSE` in the backend image. | `F-VER-01`, `INS-LIC-003` |
| `AAC-LIC-CR-003` | Maintainer; README and historical audit follow-up | Explicit application scope preserves upstream declarations and records the superseded missing-license finding. | `F-VER-01`, `INS-LIC-004` |

The callers of the package metadata contract are build tools and package
recipients; the providers are the existing package manifests. SPDX license
expressions and PEP 639 license-file metadata are the standard schemas. There
are no new API fields, authentication rules, retries, transactions, events,
jobs, or audit records. Missing license text fails distribution inspection.
Package names, versions, commands, and runtime compatibility stay unchanged.

The following artifact flow makes the licensing dependencies visible. It adds
no runtime dependency or cycle and does not change the runtime maps in
`software_architecture.md`:

```mermaid
flowchart LR
    LICENSE[Root LICENSE] --> README[README application declaration]
    LICENSE --> PYTHON[Existing setuptools build]
    PYPROJECT[pyproject.toml license metadata] --> PYTHON
    PYTHON --> ARCHIVES[Source distribution and wheel]
    LICENSE --> DOCKER[Existing backend image build]
    DOCKER --> IMAGE[/app/LICENSE]
    PACKAGE[package.json license] --> LOCK[Root package-lock.json license]
    ARCHIVES --> VERIFY[F-VER-01 controlled inspection]
    IMAGE --> VERIFY
    LOCK --> VERIFY
    README --> VERIFY
```

The standard PEP 639 representation is preferred to deprecated license tables
and classifiers. Increasing the setuptools build-only minimum is the limited
compatibility cost; isolated builds and archive inspection validate it. A
wholesale source-header rewrite and changes to third-party dependencies are
unnecessary for the approved repository and distribution licensing scope.

## Gate 3: Implementation And Verification

Implementation follows the approved Gate 1 requirements and Gate 2 impact
assessment above:

- Added the complete canonical Apache License, Version 2.0 in root `LICENSE`.
- Added the application licensing scope and license link to the README.
- Declared `Apache-2.0` in Python and JavaScript metadata and the root lock
  entry. Python `license-files` explicitly includes `LICENSE`; setuptools now
  requires `>=77.0.3` for the PEP 639 representation.
- Included `LICENSE` in the existing backend Docker `COPY` instruction.
- Added a dated follow-up to the dependency audit, preserving its historical
  findings and marking the application license actions complete.
- Added all four requirement-to-acceptance-to-`F-VER-01`-to-artifact-to-inspection
  links in `verification/requirements_traceability.yaml`.

No runtime source, runtime dependency version, database data, migration, API
contract, authorization rule, audit event, or asynchronous job changed.

### Controlled Inspection Results

Inspection date: `2026-10-19`. All four acceptance criteria pass using their
specified methods. The machine-readable inspection evidence is
`verification/generated/application-licensing-results.json`.

| Inspection / acceptance | Method and observed result |
|---|---|
| `INS-LIC-001` / `ACC-LIC-001` | Byte comparison against the system's canonical Apache text and SHA-256 verification pass. `LICENSE` is 11,358 bytes with SHA-256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`. README scope and license link pass. |
| `INS-LIC-002` / `ACC-LIC-002` | TOML/JSON parsing confirms matching `Apache-2.0` declarations. Actual source-distribution `PKG-INFO` and wheel `METADATA` both contain `License-Expression: Apache-2.0` and `License-File: LICENSE`. |
| `INS-LIC-003` / `ACC-LIC-003` | Built a source archive and then built a wheel from that extracted archive. Both contain license bytes identical to the source. Docker `WORKDIR /app`, `COPY ... LICENSE ./`, and unchanged `.dockerignore` include `/app/LICENSE`. |
| `INS-LIC-004` / `ACC-LIC-004` | Diff and parsed-metadata comparisons confirm all third-party lock entries, runtime dependencies, service image declarations, and runtime source remain unchanged. README preserves third-party scope; the audit clearly dates the resolved finding. |

The archives were built in `/tmp/aac-licensing-eeqrjaxz` using an isolated,
offline temporary environment with cached setuptools `84.0.0`, wheel `0.48.0`,
and packaging `26.3`. Build inputs were exact copies of the repository's
`pyproject.toml`, `LICENSE`, README, and backend package sources. Setuptools'
`build_sdist` produced `lydianai_assurance_as_code-0.1.0.tar.gz`; its extracted
source was then passed to `build_wheel` to produce
`lydianai_assurance_as_code-0.1.0-py3-none-any.whl`. Python's `tarfile`, `zipfile`,
and email metadata parser verified the archive contents. Build logs are retained
at `/tmp/aac-licensing-eeqrjaxz/build.log`; archive hashes are in the controlled
JSON evidence. No build packages were installed into the application environment.

Additional checks:

| Command | Result |
|---|---|
| `git diff --check` | Passed. |
| `.venv/bin/ruff check .` | Passed. |
| `.venv/bin/python scripts/check_traceability.py --output /tmp/aac-licensing-traceability-status.json` | Passed with zero errors; all four licensing requirements and acceptance criteria have verified evidence links. |
| `.venv/bin/pytest -q tests/test_web_architecture.py` | 3 passed. |
| `npm run test:web:unit` | 1 Node test-file entry passed; zero failures. |

### Completion Review And Remaining Limits

The Class C change is complete for the approved licensing scope. Requirements,
acceptance criteria, metadata, documentation, traceability, and inspection
evidence agree. The earlier audit's missing-license statement is preserved as
a historical observation and closed by the dated follow-up. No unresolved
application licensing contradiction was found.

Runtime architecture functions, interfaces, ownership, and dependency maps are
unchanged; the licensing artifact flow is documented in Gate 2. No runtime
behavior, persistence, migration, security, or performance change requires
additional verification.

The Docker image was not rebuilt; container license inclusion was verified by
the build-recipe and ignore-file inspection required by `ACC-LIC-003`.
The overall traceability inventory still reports 642 missing requirement links
and 127 missing acceptance links outside this change. These are not closed by
the licensing work. Third-party compliance and service-image findings remain
tracked in `dependency_license_audit.md` and are not resolved by licensing the
application code.

## References

- Official license text: <https://www.apache.org/licenses/LICENSE-2.0.txt>.
- Apache guidance on applying the license:
  <https://www.apache.org/foundation/license-faq.html#Apply-My-Software>.
- Setuptools PEP 639 metadata and build-version support:
  <https://setuptools.pypa.io/en/stable/userguide/license_migration.html>.
