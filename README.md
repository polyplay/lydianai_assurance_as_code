# LydianAI Assurance-as-Code

LydianAI Assurance-as-Code is a Python backend for managing safety, quality, traceability,
and compliance evidence for software-intensive automotive systems. The tool is designed
around a backend-owned source of truth: artefacts are imported from Sphinx-Needs or created
through the API, versioned automatically, validated against a rule catalog, traced through
relationships, and frozen into project baselines for release-gate evaluation.

The current implementation is a FastAPI service with SQLAlchemy 2, Alembic migrations,
PostgreSQL, Valkey, and ARQ background workers. It includes the backend foundations for:

- Username/password authentication with role-based authorization.
- Project configuration, ASIL/profile configuration, tailoring decisions, and schema management.
- Artefact and relationship CRUD with automatic revision history.
- Sphinx-Needs import, conflict detection, and import-run decision handling.
- Validation rule execution, issue suppression/reopen, and release-gate checks.
- Traceability, impact analysis, suspect-state propagation, baselines, reports, jobs, and audit events.

The detailed requirements and architecture documents are kept in `docs/`.

- [Version 1 Requirements Baseline](docs/requirements_baseline.md)
- [Software Architecture](docs/software_architecture.md)
- [Dependency And License Audit](docs/dependency_license_audit.md)

All project changes are governed by [Project Change Rules](AGENTS.md). Changes
must proceed through requirements, software architecture, and implementation
gates in that order.

Operational and role-based documentation is kept in `documentation/`:

- `documentation/backend_installer_guide.md`
- `documentation/admin_manual.md`
- `documentation/user_manual.md`

Production backend installer assets are kept in `installer/backend/`.

## License

The project's own application code, including the Python backend and web
frontend, is licensed under the Apache License, Version 2.0 (`Apache-2.0`).
See [LICENSE](LICENSE) for the complete terms.

Valkey's server uses BSD-3-Clause; its version-specific
[license and copyright notices](LICENSES/Valkey-8.1.10.txt) are retained separately.
Third-party dependencies, tools, and service images retain their own terms.
See [Third-Party License Notices](THIRD_PARTY_NOTICES.md) for current references
and the [Dependency And License Audit](docs/dependency_license_audit.md) for
dated findings, completed follow-ups, and remaining release obligations.

## Prerequisites

- Python 3.11 or newer for local development.
- Docker and Docker Compose for the containerized setup.
- PostgreSQL and Valkey if running the API locally without Docker Compose.

## Quick Start With Docker Compose

Docker Compose is the simplest way to run the full stack: PostgreSQL, Valkey, API, ARQ worker,
and nginx.

```bash
cp .env.example .env
docker compose up --build
```

The API is available at:

```text
http://127.0.0.1:8000/api/v1
```

The Swagger UI is available at:

```text
http://127.0.0.1:8000/api/v1/docs
```

The role-aware web workspace is available at:

```text
http://127.0.0.1:8000/app
```

The nginx proxy listens on:

```text
http://127.0.0.1:8080
```

If any default host ports are already in use, override them when starting Compose:

```bash
AAC_POSTGRES_PORT=15432 AAC_REDIS_PORT=16379 AAC_API_PORT=18000 AAC_NGINX_PORT=18080 docker compose up --build
```

The API container runs Alembic migrations automatically before starting Uvicorn.

Valkey uses the existing Compose service name `redis`, `AAC_REDIS_URL`,
`redis://` connection strings, and `AAC_REDIS_PORT` override for compatibility.
Existing Redis installations must follow the
[Valkey migration procedure](documentation/valkey_migration.md) before upgrading;
production Valkey uses a separate `valkey_data` volume.

To create the first admin user in the running API container:

```bash
docker compose exec api aac create-admin \
  --username admin \
  --display-name Admin \
  --email admin@example.com \
  --password 'change-me'
```

Stop the stack with:

```bash
docker compose down
```

To remove the PostgreSQL volume as well:

```bash
docker compose down -v
```

## Local Development Setup

Create a virtual environment and install development dependencies:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

Start PostgreSQL and Valkey. You can either run them yourself or start only those services
from Compose:

```bash
docker compose up postgres redis
```

The broker service is still named `redis`. Configure the environment; the
defaults in `.env.example` target local PostgreSQL and Valkey:

```bash
cp .env.example .env
```

Apply migrations:

```bash
.venv/bin/alembic upgrade head
```

Create an admin user:

```bash
.venv/bin/aac create-admin \
  --username admin \
  --display-name Admin \
  --email admin@example.com \
  --password 'change-me'
```

Run the API:

```bash
.venv/bin/uvicorn aac_backend.main:app --reload --host 0.0.0.0 --port 8000
```

Run the ARQ worker in a second shell when testing asynchronous jobs:

```bash
.venv/bin/arq aac_backend.workers.settings.WorkerSettings
```

## Make Targets

The repository includes a small `Makefile` for common development tasks:

```bash
make install       # create .venv and install development dependencies
make migrate       # run Alembic migrations
make dev           # start the FastAPI development server
make worker        # start the ARQ worker
make test          # run pytest
make test-web      # run JavaScript unit tests
make test-web-e2e  # run Playwright workflow, responsive, and accessibility tests
make test-web-integration # run Playwright against disposable PostgreSQL and Valkey services
make test-integration # run PostgreSQL fault/concurrency tests in a disposable container
make lint          # run ruff
make compile       # compile Python files
make compose-up    # run the Docker Compose stack
make compose-down  # stop the Docker Compose stack
make smoke-test    # run the Docker/API end-to-end smoke test
```

Install browser-test dependencies once with `make install-web`.

## Environment Variables

The application reads configuration from environment variables, with `.env` support through
Pydantic settings:

```text
AAC_DATABASE_URL=postgresql+asyncpg://aac:aac@localhost:5432/aac
AAC_REDIS_URL=redis://localhost:6379/0
AAC_JWT_SECRET=change-me-change-me-change-me-change-me
AAC_JWT_EXPIRY_HOURS=8
AAC_SECRET_ENCRYPTION_KEY=
AAC_GITHUB_API_BASE_URL=https://api.github.com
AAC_ENVIRONMENT=development
```

Database integration tests require Docker by default:

```bash
make test-integration
```

To use an existing disposable PostgreSQL instance instead, set
`AAC_TEST_DATABASE_URL`. Its user must be allowed to create and drop temporary
test databases.

For real deployments, replace `AAC_JWT_SECRET` with a strong secret and use environment-specific
database and Valkey credentials. Set `AAC_SECRET_ENCRYPTION_KEY` to a Fernet-compatible key, or to a
strong passphrase that the backend derives into an encryption key, before storing repository connector
secrets such as GitHub App private keys, GitHub access tokens, and webhook secrets.

## API Entry Points

The API is mounted under `/api/v1`. Important entry points include:

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
- `GET /api/v1/projects/{project_id}/repo-connectors`
- `POST /api/v1/projects/{project_id}/repo-connectors`
- `GET /api/v1/projects/{project_id}/repo-connectors/{connector_id}/status`
- `POST /api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan`
- `POST /api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals`
- `POST /api/v1/integrations/github/webhook/{connector_id}`
- `GET /api/v1/projects/{project_id}/artefacts`
- `POST /api/v1/projects/{project_id}/imports/sphinx`
- `POST /api/v1/projects/{project_id}/validation/run`
- `POST /api/v1/projects/{project_id}/baselines`
- `POST /api/v1/projects/{project_id}/release-gate/run`
- `GET /api/v1/projects/{project_id}/traceability-matrix`

Use `/api/v1/docs` for the complete OpenAPI documentation.

## CLI Workflows

The `aac` command supports the same MVP workflows as the web console. Pass `--base-url`
explicitly or set `AAC_API_URL`; pass `--token` or set `AAC_TOKEN` after login.

```bash
.venv/bin/aac login --username admin --password 'change-me'
.venv/bin/aac projects --token "$AAC_TOKEN"
.venv/bin/aac import-sphinx --project-id PROJ_001 --file needs.json --version-update-mode automatic_new_version
.venv/bin/aac validation-run --project-id PROJ_001
.venv/bin/aac trace --project-id PROJ_001 --artefact-id ART_001
.venv/bin/aac baseline-create --project-id PROJ_001 --name "Baseline 1"
.venv/bin/aac release-gate --project-id PROJ_001 --baseline-id BASE_001
```

## Verification

Run the standard checks before committing:

```bash
.venv/bin/ruff check .
.venv/bin/pytest -q
.venv/bin/python -m compileall aac_backend
docker compose config
```

Run the end-to-end smoke test against a running Docker Compose stack:

```bash
AAC_API_BASE_URL=http://127.0.0.1:18000 make smoke-test
```

The smoke test creates a unique admin, an ASIL D + Automotive SPICE PAM 4.0 CL3 project,
project members, a requirement, a test case, a traceability link, then confirms validation
raises ASIL D mandatory artefact gaps and baseline creation is blocked.

At the time of this README update, the test suite covers route contracts, service-level
regressions, and validation rule evaluator pass/fail behavior.
