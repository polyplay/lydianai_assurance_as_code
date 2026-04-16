# LydianAI Assurance-as-Code

LydianAI Assurance-as-Code is a Python backend for managing safety, quality, traceability,
and compliance evidence for software-intensive automotive systems. The tool is designed
around a backend-owned source of truth: artefacts are imported from Sphinx-Needs or created
through the API, versioned automatically, validated against a rule catalog, traced through
relationships, and frozen into project baselines for release-gate evaluation.

The current implementation is a FastAPI service with SQLAlchemy 2, Alembic migrations,
PostgreSQL, Redis, and ARQ background workers. It includes the backend foundations for:

- Username/password authentication with role-based authorization.
- Project configuration, ASIL/profile configuration, tailoring decisions, and schema management.
- Artefact and relationship CRUD with automatic revision history.
- Sphinx-Needs import, conflict detection, and import-run decision handling.
- Validation rule execution, issue suppression/reopen, and release-gate checks.
- Traceability, impact analysis, suspect-state propagation, baselines, reports, jobs, and audit events.

The detailed requirements and architecture documents are kept in `docs/`.

## Prerequisites

- Python 3.11 or newer for local development.
- Docker and Docker Compose for the containerized setup.
- PostgreSQL and Redis if running the API locally without Docker Compose.

## Quick Start With Docker Compose

Docker Compose is the simplest way to run the full stack: PostgreSQL, Redis, API, ARQ worker,
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

The lightweight web console is available at:

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

Start PostgreSQL and Redis. You can either run them yourself or start only those services
from Compose:

```bash
docker compose up postgres redis
```

Configure the environment. The defaults in `.env.example` target local PostgreSQL and Redis:

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
make lint          # run ruff
make compile       # compile Python files
make compose-up    # run the Docker Compose stack
make compose-down  # stop the Docker Compose stack
make smoke-test    # run the Docker/API end-to-end smoke test
```

## Environment Variables

The application reads configuration from environment variables, with `.env` support through
Pydantic settings:

```text
AAC_DATABASE_URL=postgresql+asyncpg://aac:aac@localhost:5432/aac
AAC_REDIS_URL=redis://localhost:6379/0
AAC_JWT_SECRET=change-me-change-me-change-me-change-me
AAC_JWT_EXPIRY_HOURS=8
AAC_ENVIRONMENT=development
```

For real deployments, replace `AAC_JWT_SECRET` with a strong secret and use environment-specific
database and Redis credentials.

## API Entry Points

The API is mounted under `/api/v1`. Important entry points include:

- `GET /api/v1/health`
- `POST /api/v1/auth/login`
- `GET /api/v1/projects`
- `POST /api/v1/projects`
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
