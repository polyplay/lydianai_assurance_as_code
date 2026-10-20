# Release Licensing Assurance Requirements

Status: **broker replacement approved; remaining release-licensing scope proposed**.

Date: `2026-10-19`.

This document specifies the requested closure of the six release-licensing gaps
identified after the initial Apache-2.0 adoption. It defines required outcomes;
broker selection, tooling, module structure, and build implementation remain
architecture-gate decisions. `requirements_baseline.md` controls scope and
authority; license texts control the actual third-party terms.

On `2026-10-19` the user explicitly requested replacement of `redis:7-alpine`
with Valkey, with requirements updated before code. This approves
`AAC-LIC-CR-004`, the broker compatibility/upgrade scope of `AAC-LIC-CR-011`,
and `AAC-LIC-CR-012` below. It does not approve or claim completion of the
separate full-release inventory, ownership, locking, or compliance work.

## Stakeholder Needs And Derivation

| Need ID | Stakeholder | Need | Derivation |
|---|---|---|---|
| NEED-LIC-002 | Release maintainer | Associate each release with complete, repeatable component and licensing evidence. | NEED-LIC-001 |
| NEED-LIC-003 | Recipient and operator | Receive usable notices/source-access information and preserve existing operation during licensing remediation. | NEED-LIC-001 |
| NEED-LIC-004 | Copyright holder and contributor | Preserve ownership and distinguish confirmed licensing authority from technical authorship evidence. | NEED-LIC-001 |

## Requirements

AAC-LIC-SR-001 (`StRS`, constraint; derives from `NEED-LIC-002` through
`NEED-LIC-004`)
Application recipients shall receive a release whose application licensing,
third-party terms, component identity, source provenance, and distribution
obligations are documented for the exact supplied artifacts.

AAC-LIC-SY-001 (`SyRS`, constraint; derives from `AAC-LIC-SR-001`)
A release shall be accepted as licensing-complete only when its component
inventories, required notices, applicable source-access obligations, first-party
licensing authority, and built-artifact verification have accepted evidence.
Missing evidence shall remain explicitly unresolved and shall prevent that
release from being reported as licensing-complete.

AAC-LIC-CR-004 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-003`)
The default distributed queue broker shall have a documented OSI-approved
permissive license for the exact supplied version and shall preserve the
existing queue protocol and application job semantics. Existing job state
ownership in PostgreSQL shall remain unchanged.

AAC-LIC-CR-005 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-002`)
Each declared release target shall have resolved direct and transitive package
versions and artifact hashes, including release build dependencies. Base and
service container images shall be identified by immutable digest. Release
evidence shall identify target OS, architecture, Python version, resolved
packages, images, and source state. Input hash mismatches shall fail
verification rather than trigger an unconstrained replacement resolution.

AAC-LIC-IR-002 (`SRS`, interface; derives from `AAC-LIC-SY-001` and
`NEED-LIC-002`)
Each distributed application and service image shall have a machine-readable
SBOM in a declared, schema-validated SPDX or CycloneDX version. The inventory
shall cover shipped application, Python, JavaScript, bundled native, and OS
components, as applicable, with component/version identities, available source
locations, license evidence, and exact artifact digests. Development-only tools
shall be identified separately from shipped runtime components. Unknown or
unmatched components shall be reported rather than silently omitted.

AAC-LIC-CR-006 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-003`)
Recipients shall receive the required license texts, copyright/attribution
notices, and applicable source-access information for the exact redistributed
components. Original upstream notices shall be preserved. Recipient materials
shall distinguish first-party Apache-2.0 code from each dependency's own terms
and shall accompany the relevant source, package, or image distribution.

AAC-LIC-CR-007 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-003`)
Every shipped component with LGPL, MPL, or other distribution conditions shall
have a recorded obligation assessment tied to its exact version, modification
status, and distribution form. The record shall identify applicable license and
notice retention, corresponding-source access, and LGPL modification or
replacement provisions, together with the supplied evidence or an explicitly
unresolved status. A source URL alone shall not be represented as satisfying an
obligation that requires additional materials or availability guarantees.

AAC-LIC-CR-008 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-004`)
Release provenance evidence shall identify first-party source scope, committed
and uncommitted source state, known contributors, copied/external code findings,
and exclusions. The rights holder's identity and authority to license that
scope under Apache-2.0 shall require an explicit recorded confirmation from an
authorised rights holder or representative. Git names, timestamps, code scans,
and AI assistance shall not substitute for that confirmation. Missing authority
or unresolved external-source rights shall remain unverified.

AAC-LIC-CR-009 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-002`)
Release verification shall inspect actual freshly built image contents for the
application license and required recipient materials, and shall exercise
startup, health, migrations, and queue workflows against the selected broker.
Evidence shall identify the tested image digests and outcomes. Source-recipe
inspection, unavailable build access, and unexecuted checks shall not be
reported as successful image verification.

AAC-LIC-CR-010 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-002`)
The release maintainer shall be able to evaluate licensing readiness from the
controlled release evidence. Missing, inconsistent, stale, or unresolved
component/obligation/ownership/image evidence shall produce a failing result
that identifies the affected requirement. Complete accepted evidence shall
produce a passing result. Evaluation shall not change application data or
include credentials or other secrets in its output.

AAC-LIC-CR-011 (`SRS`, constraint; derives from `AAC-LIC-SY-001` and
`NEED-LIC-003`)
Licensing remediation shall preserve existing public API/job contracts, database
contents and migration behavior, documented connection-setting compatibility,
and supported application Python versions. Any broker replacement shall have a
documented upgrade procedure addressing queued/in-flight work, persistent data,
and rollback. Existing broker volumes shall not be automatically deleted or
opened with an unverified incompatible data format.

AAC-LIC-CR-012 (`SRS`, constraint; derives from `NEED-LIC-003` and
`AAC-LIC-CR-004`)
Default development, production, and disposable web-integration deployments
shall use Valkey instead of `redis:7-alpine`. Existing `AAC_REDIS_URL`,
`redis://` connection strings, Compose service hostname `redis`, broker port
6379, and `AAC_REDIS_PORT` development override shall remain compatible.
Existing Redis persistence shall be preserved separately from new Valkey
persistence; an operator shall have documented drain, backup, verification,
and rollback steps before upgrading an existing installation.

## Acceptance And Phase Boundaries

`ACC-LIC-005` through `ACC-LIC-014` in `mvp_acceptance_criteria.md` provide
objective acceptance. The change record controls approvals and requirement
allocation at the subsequent architecture gate. None of these requirements
claims that dependency substitution automatically establishes legal compliance.
Ownership confirmation and actual image execution remain required evidence.

No end-user API, persisted application state, role, application audit event,
or application background job is introduced by these release checks.
Application runtime limits remain governed by existing requirements. Failure
handling for release checks is specified in `AAC-LIC-CR-010`.
