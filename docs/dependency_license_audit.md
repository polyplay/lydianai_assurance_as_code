# Dependency And License Audit

Audit date: 2026-10-02

Change classification: Class A documentation record. This audit records
dependency, license, and vulnerability findings only. It does not change product
behavior, requirements, architecture, code, data, deployment configuration, or
dependency versions.

This document is an engineering compliance aid, not legal advice.

## Scope

Audited surfaces:

- Python runtime dependencies from `requirements.txt`.
- Python development dependencies from `requirements-dev.txt`.
- JavaScript development dependencies from `package-lock.json`.
- Declared Docker and Compose images from `Dockerfile`, `docker-compose.yml`,
  and `installer/backend/docker-compose.backend.yml`.
- Repository-level license metadata.

Out of scope:

- Full OS package SBOM for container images. No local SBOM scanner such as Syft
  or Trivy was available during the audit.
- Legal review of license obligations.
- A source-code copyright ownership review.

Important reproducibility note: Python dependencies are declared with broad
`>=` specifiers, and Docker images use moving tags. Exact resolved versions can
drift after this audit unless versions and image digests are pinned.

## Application Licensing Follow-Up: 2026-10-19

The application's own code is now licensed under Apache License, Version 2.0
(`Apache-2.0`). The root `LICENSE`, README, Python package metadata, and
JavaScript package metadata record this choice. Python source distributions,
wheels, and the backend image build include the application license text.
See [Application Licensing Change Record](app_licensing_change_record.md) for
the approved requirements, architecture impact assessment, and verification.

This follow-up closes the missing-application-license finding and the first two
recommended actions below. It does not relicense third-party dependencies or
service images, change their versions, or close the other dependency compliance
and distribution findings. The audit results below remain dated observations.

## Valkey Replacement Follow-Up: 2026-10-19

Following the explicit broker replacement request, development and production
Compose files and the disposable web-integration runner now select
`valkey/valkey:8.1.10-alpine` and use `valkey-cli ping`. Valkey's server license
is BSD-3-Clause; this does not relicense other image components or dependencies.
Existing connection settings and the service hostname remain compatible.

Production Valkey uses fresh `valkey_data` storage. Original Redis data is
preserved separately because Redis 7.4 persistence is incompatible with Valkey.
Existing installations must follow `documentation/valkey_migration.md`.
Source configuration and operator documentation address the default Redis image
selection finding. The user subsequently supplied a successful disposable test
run: Valkey image pull/start, the real ARQ enqueue/worker/result test, clean
PostgreSQL migrations, and the real browser workflow passed. The reported image
digest and coverage limits are recorded in `valkey_replacement_change_record.md`
and `verification/generated/valkey-replacement-results.json`. This is
user-supplied execution evidence; no fresh image license scan, production
migration, or complete cancellation verification is claimed here.

## License Reference Follow-Up: 2026-10-20

The application license remains [Apache-2.0](../LICENSE). The selected Valkey
8.1.10 server's complete BSD-3-Clause text, including both upstream copyright
notices, is retained in [LICENSES/Valkey-8.1.10.txt](../LICENSES/Valkey-8.1.10.txt).
[Third-Party License Notices](../THIRD_PARTY_NOTICES.md) identifies the current
application/server distinction and known LGPL/MPL dependency references.
README, operational documentation, Python archive license-file metadata, and
the backend COPY recipe include or link these materials consistently.

This follow-up updates license references and targeted recipient materials. It
does not change the selected licenses, dependency versions, runtime behavior,
or historical audit versions. Full component inventories and redistribution
obligations remain open where the exact shipped artifacts have not been reviewed.
Verification is recorded in
[Licensing Reference Update Change Record](licensing_reference_update_change_record.md).

## Executive Findings At The Audit Date

- At the audit date, the repository did not include a top-level `LICENSE` or
  `COPYING` file. Resolved by the `2026-10-19` follow-up above.
- Python runtime dependencies are mostly permissive. No GPL or AGPL Python
  runtime packages were found.
- The Python runtime license items requiring attention are:
  - `psycopg` and `psycopg-binary`: `LGPL-3.0-only`.
  - `certifi`: `MPL-2.0`.
- JavaScript dependencies are development/test-only. `axe-core` and
  `@axe-core/playwright` are `MPL-2.0`; Playwright packages are `Apache-2.0`.
- The most significant licensing concern is the Redis service image:
  `redis:7-alpine` resolved locally to Redis `7.4.8`, which is licensed under
  RSALv2 or SSPLv1 rather than BSD-3-Clause.
- `pip-audit` and `npm audit` found no known vulnerabilities in the resolved
  Python and JavaScript dependency sets at audit time.
- The application Dockerfile installs `build-essential`, `gcc`, `g++`, `make`,
  and `curl` into the runtime image, increasing the OS package license and
  maintenance surface.

## Runtime Python Dependencies

Runtime dependency resolution found 43 installed Python packages.

Direct runtime dependencies with resolved license metadata:

| Package | Resolved version | License |
|---|---:|---|
| `alembic` | 1.20.0 | MIT |
| `arq` | 0.28.0 | MIT License |
| `asyncpg` | 0.31.0 | Apache-2.0 |
| `bcrypt` | 5.0.0 | Apache Software License |
| `cryptography` | 50.0.2 | Apache-2.0 OR BSD-3-Clause |
| `email-validator` | 2.3.0 | The Unlicense |
| `fastapi` | 0.142.2 | MIT |
| `httpx` | 0.28.1 | BSD License |
| `pydantic` | 2.13.5 | MIT |
| `pydantic-settings` | 2.15.0 | MIT |
| `psycopg` | 3.3.6 | LGPL-3.0-only |
| `psycopg-binary` | 3.3.6 | LGPL-3.0-only |
| `PyJWT` | 2.15.1 | MIT |
| `PyYAML` | 6.0.3 | MIT License |
| `python-multipart` | 0.0.32 | Apache-2.0 |
| `SQLAlchemy` | 2.1.2 | MIT |
| `uvicorn` | 0.54.0 | BSD-3-Clause |

Runtime license summary:

| License metadata | Count |
|---|---:|
| MIT / MIT License / MIT-0 | 20 |
| BSD variants | 11 |
| Apache variants | 7 |
| LGPL-3.0-only | 2 |
| MPL-2.0 | 1 |
| PSF-2.0 | 1 |
| ISC | 1 |
| The Unlicense | 1 |

Copyleft or file-level runtime items:

| Package | Version | License | Notes |
|---|---:|---|---|
| `psycopg` | 3.3.6 | LGPL-3.0-only | Compatible with GPLv3/AGPLv3 strategies; requires notice/compliance if redistributed. |
| `psycopg-binary` | 3.3.6 | LGPL-3.0-only | Bundled binary component; consider source build or documented compliance approach for production distribution. |
| `certifi` | 2026.7.22 | MPL-2.0 | File-level copyleft for the certificate bundle package. |

## Development Dependencies

`requirements-dev.txt` adds 6 packages beyond the runtime set:

| Package | Resolved version | License |
|---|---:|---|
| `Pygments` | 2.21.0 | BSD-2-Clause |
| `iniconfig` | 2.3.0 | MIT |
| `pluggy` | 1.6.0 | MIT License |
| `pytest` | 9.1.1 | MIT |
| `pytest-asyncio` | 1.4.0 | Apache-2.0 |
| `ruff` | 0.16.10 | MIT |

No GPL, AGPL, LGPL, or proprietary Python development package was identified.

## JavaScript Dependencies

`package-lock.json` contains development/test tooling only:

| Package | Version | License |
|---|---:|---|
| `@axe-core/playwright` | 4.11.3 | MPL-2.0 |
| `@playwright/test` | 1.60.0 | Apache-2.0 |
| `axe-core` | 4.11.4 | MPL-2.0 |
| `fsevents` | 2.3.2 | MIT |
| `playwright` | 1.60.0 | Apache-2.0 |
| `playwright-core` | 1.60.0 | Apache-2.0 |

`npm outdated` reported newer available versions for:

- `@axe-core/playwright`: current 4.11.3, latest 4.13.0.
- `@playwright/test`: current 1.60.0, latest 1.63.0.

## Container And Service Images

Declared images:

| Image reference | Observed local version | License note |
|---|---|---|
| `python:3.12-slim` | Python 3.12.13 | Python license plus Debian OS packages. |
| `postgres:16-alpine` | PostgreSQL 16.13 | PostgreSQL License plus Alpine OS packages. |
| `redis:7-alpine` | Redis 7.4.8 | RSALv2 or SSPLv1 for Redis 7.4.x. |
| `nginx:1.27-alpine` | nginx 1.27.5 | nginx license plus Alpine OS packages. |

Observed local image IDs:

| Image | Local image ID |
|---|---|
| `python:3.12-slim` | `sha256:b4acd70b6f4ca3e8fa68f11d4bc6831d141744654e62286f862b3c8ca7bd0467` |
| `postgres:16-alpine` | `sha256:108b27c919e6e7bc124350fb265deea9adac58e118eade428c6d1ad44b90debe` |
| `redis:7-alpine` | `sha256:aa189b5a1954929c393585e6dc5717a75b18f75a931df8bdcc00a3d3bd546be6` |
| `nginx:1.27-alpine` | `sha256:6769dc3a703c719c1d2756bda113659be28ae16cf0da58dd5fd823d6b9a050ea` |

Observed local application images existed but were built on 2026-06-13 and were
not treated as authoritative for current source state:

| Image | Local image ID |
|---|---|
| `lydianai_assurance_as_code-api` | `sha256:a3afcb8f6438037f86d497309abed7e12c54adb9da7c8fa95ed269e10df9fd27` |
| `lydianai_assurance_as_code-worker` | `sha256:23993c5418d516a4806c08f39a25fa07e5bfce92d36ce1e3451693488dde4ba5` |

The local application image contained 161 Debian packages. Notable runtime-layer
packages included `build-essential`, `gcc`, `g++`, `make`, `curl`, and
`libc6-dev`.

## Redis Licensing Concern

At the audit date the Compose files used `redis:7-alpine`, resolving locally to
Redis 7.4.8. The source defaults have since changed to Valkey as recorded above;
these historical Redis terms still matter for existing installations and
retained images. Redis states that:

- Redis 7.2.x and earlier remain BSD-3-Clause.
- Redis 7.4.x to 7.8.x are licensed under RSALv2 or SSPLv1.
- Redis 8 and later add AGPLv3 as a licensing option.

The retained Redis images remain subject to those terms. The default server
selection has already been changed to Valkey; the historical Redis finding is
not an active recommendation to change the application's Apache-2.0 license.

Remediation options considered by the audit:

1. Replace `redis:7-alpine` with Valkey, which is BSD-3-Clause and compatible
   with the Redis protocol used by typical queue/cache integrations.
2. Pin Redis to a BSD-licensed Redis 7.2.x image if Redis specifically is
   required.
3. If staying on Redis 7.4 or later, document the chosen Redis license path and
   legal/commercial rationale.

## Current License Strategy

- The application's own code uses `Apache-2.0`; Python and JavaScript project
  metadata agree with the root `LICENSE`.
- The default `valkey/valkey:8.1.10-alpine` server uses BSD-3-Clause. Its two
  upstream copyright/license blocks are preserved in the local license copy.
- `psycopg` and `psycopg-binary` retain LGPL-3.0-only terms, and `certifi`
  retains MPL-2.0 terms. Applicable distribution/source-access obligations must
  be assessed for the exact shipped packages, independently of the app license.
- JavaScript accessibility tooling is development-only in the current manifest;
  its MPL-2.0 declarations are not replaced by the app's Apache-2.0 declaration.
- Redis RSALv2/SSPLv1 findings apply to the audited/retained legacy Redis images,
  not to the replacement Valkey server. Container OS and bundled native
  components still retain their own licenses.

The earlier GPL/AGPL/MIT/proprietary alternatives were exploratory. They are
superseded by the explicit Apache-2.0 application decision and Valkey broker
selection; the dated dependency-resolution findings above remain historical.

## Vulnerability Audit Results

Commands run:

```bash
pip-audit -r requirements.txt --format=json
pip-audit -r requirements-dev.txt --format=json
npm audit --package-lock-only --json
```

Results:

- Runtime Python dependencies: no known vulnerabilities found.
- Development Python dependencies: no known vulnerabilities found.
- JavaScript dependencies: no known vulnerabilities found.

## Commands Used For Audit

Representative commands:

```bash
python3 -m venv /tmp/lydianai-aac-runtime-clean.../venv
/tmp/lydianai-aac-runtime-clean.../venv/bin/python -m pip install -r requirements.txt
pip-licenses --python=/tmp/lydianai-aac-runtime-clean.../venv/bin/python --format=json --with-urls --with-description

python3 -m venv /tmp/lydianai-aac-dev-clean.../venv
/tmp/lydianai-aac-dev-clean.../venv/bin/python -m pip install -r requirements-dev.txt
pip-licenses --python=/tmp/lydianai-aac-dev-clean.../venv/bin/python --format=json --with-urls --with-description

jq -r '.packages | to_entries[] | select(.key != "") | [.key, .value.version, (.value.license // "UNKNOWN")] | @tsv' package-lock.json
npm audit --package-lock-only --json
docker compose config --images
docker run --rm redis:7-alpine redis-server --version
```

## Recommended Follow-Up

1. Completed `2026-10-19`: select and record `Apache-2.0` for application code.
2. Completed `2026-10-19`: add top-level `LICENSE` and package license metadata.
3. Source defaults updated `2026-10-19`: replace `redis:7-alpine` with Valkey;
   disposable broker/browser verification subsequently passed in the user's
   terminal. Existing installations still require the documented migration
   and deployment-specific checks.
4. Generate a formal SBOM for Python, JavaScript, and container OS packages.
5. Valkey server license/attributions and targeted dependency references added
   `2026-10-20`; complete redistributed package/native/OS notice and source
   obligation coverage still requires the full release inventory.
6. Pin Python dependency versions or introduce a locked requirements workflow.
7. Pin Docker images by digest for release builds.
8. Consider a multi-stage Docker build to remove build tooling from runtime
   images.

## Source References

- Application Apache-2.0 terms: <https://www.apache.org/licenses/LICENSE-2.0>.
- Selected Valkey version's license:
  <https://raw.githubusercontent.com/valkey-io/valkey/8.1.10/COPYING>.
- Local current notices: [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md).
- Redis license overview: <https://redis.io/legal/licenses/>
- Redis official Docker image notes: <https://hub.docker.com/_/redis>
- Valkey project: <https://github.com/valkey-io/valkey>
- Psycopg package metadata: <https://www.psycopg.org/download/>
- Psycopg license: <https://github.com/psycopg/psycopg/blob/master/LICENSE.txt>.
- Mozilla MPL distribution guidance: <https://www.mozilla.org/en-US/MPL/2.0/FAQ/>.

