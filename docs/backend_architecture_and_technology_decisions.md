# Back-End Architecture And Technology Decisions

## 1. Purpose

This document records confirmed technology stack, deployment architecture, and back-end design decisions for the Assurance-as-Code platform MVP. It resolves blocker B5 (technology stack) and B6 (deployment specification) identified in the implementation readiness assessment.

These decisions supersede any conflicting exploratory statements in `draft_AssuranceAs_Code.txt`.

---

## 2. Technology Stack

### 2.1 Programming Language

DEC-TECH-001
The back-end shall be implemented in Python 3.11 or later.

Basis: `DEC-TOOL-001` (specification_refinement_decisions.md) confirmed Python as the back-end language.

### 2.2 Web Framework

DEC-TECH-010
The back-end shall use FastAPI as the HTTP API framework.

DEC-TECH-011
FastAPI shall be used with Pydantic v2 for request/response model validation and serialization.

DEC-TECH-012
All API endpoints shall be defined using FastAPI's declarative router pattern.

DEC-TECH-013
FastAPI's built-in OpenAPI schema generation shall be used to publish the API schema at `/api/v1/openapi.json`.

Rationale: FastAPI provides async-native request handling, automatic OpenAPI documentation, and native Pydantic integration. Pydantic v2 provides the validated data model layer consistent with the artefact JSON schemas defined in `artefact_json_schemas.md`.

### 2.3 Database Engine

DEC-TECH-020
The MVP database engine shall be PostgreSQL 15 or later.

DEC-TECH-021
PostgreSQL shall be deployed as a containerized service co-located with the back-end.

DEC-TECH-022
The back-end shall access PostgreSQL exclusively through the SQLAlchemy ORM and Core layer.

DEC-TECH-023
SQLAlchemy 2.x shall be used as the ORM and database access layer.

DEC-TECH-024
All database interactions from application code shall use parameterized queries or ORM-generated SQL. Raw string-interpolated SQL shall not be used.

Rationale: PostgreSQL is the most capable open-source relational database for complex schema requirements, transactional integrity, and recursive query support (required for transitive graph traversal per `DEC-DB-003`). It has no proprietary runtime dependency (`AAC-DB-DR-011`). SQLAlchemy 2.x provides both ORM-level and Core-level access, supporting the mix of structured artefact data and typed relationship table queries.

### 2.4 Database Migrations

DEC-TECH-030
Alembic shall be used as the database schema migration tool.

DEC-TECH-031
All schema changes shall be represented as Alembic migration scripts and version-controlled alongside the application code.

DEC-TECH-032
The migration baseline shall be generated from the schema defined in `logical_database_schema.md`.

DEC-TECH-033
Migration scripts shall be idempotent where possible and shall include upgrade and downgrade procedures.

### 2.5 Async Task Queue

DEC-TECH-040
The back-end shall use ARQ (Async Redis Queue) as the async job queue.

DEC-TECH-041
ARQ shall use Redis 7 or later as its broker and result store.

DEC-TECH-042
All long-running operations defined in `async_job_schema.md` shall be implemented as ARQ worker tasks.

DEC-TECH-043
The ARQ worker process shall run as a separate process from the FastAPI application server.

DEC-TECH-044
Job state transitions defined in `async_job_schema.md` shall be persisted to the PostgreSQL `jobs` table, not stored only in Redis. Redis shall be used for queue and in-flight task coordination only.

Rationale: ARQ is Python-native, async-first, and integrates with the asyncio event loop used by FastAPI. Redis is a well-understood, low-operational-overhead broker. Job durability is maintained in PostgreSQL, ensuring job state survives Redis restarts.

### 2.6 Domain Event Bus

DEC-TECH-050
The MVP domain event bus shall be internal-only, implemented with a PostgreSQL
transactional outbox and an in-process dispatcher.

DEC-TECH-051
The dispatcher shall claim committed outbox records, invoke registered consumers
within the back-end process, and persist delivery or retry state.

DEC-TECH-052
Events that trigger async job creation shall enqueue the job to ARQ through an
idempotent consumer after the triggering database transaction commits.

DEC-TECH-053
The event bus shall not use an external message broker (e.g., Kafka, RabbitMQ) in the MVP.

DEC-TECH-054
The event model specification (`domain_event_model.md`) defines the canonical event types, schemas, and consumption contracts.

Rationale: A PostgreSQL outbox prevents lost post-commit triggers while retaining
an internal dispatcher and avoiding an external message broker for version 1.

### 2.7 Authentication

DEC-TECH-060
The back-end shall implement username/password authentication per `DEC-AUTHN-001`.

DEC-TECH-061
Passwords shall be hashed using bcrypt with a minimum cost factor of 12.

DEC-TECH-062
Authenticated sessions shall use JSON Web Tokens (JWT) with a configurable expiry (default: 8 hours).

DEC-TECH-063
JWT tokens shall be signed using HS256 with a secret key loaded from the environment configuration.

DEC-TECH-064
The back-end shall not issue or accept refresh tokens in the MVP.

DEC-TECH-065
Token validation shall be implemented as a FastAPI dependency injected into all protected route handlers.

### 2.8 HTTP Transport

DEC-TECH-070
The back-end shall require HTTPS for all API communication in production deployments.

DEC-TECH-071
In production, TLS termination shall be performed by a reverse proxy (e.g., nginx) in front of the FastAPI application server.

DEC-TECH-072
The FastAPI application server shall bind to localhost only in production; external access shall be through the reverse proxy.

DEC-TECH-073
In local development mode, HTTP without TLS is permitted.

### 2.9 Sphinx-Needs Import

DEC-TECH-080
The Sphinx-Needs import pipeline shall accept a JSON export of Sphinx-Needs objects as its primary input format.

DEC-TECH-081
The Sphinx-Needs JSON export format shall be generated by the `sphinxcontrib-needs` export functionality.

DEC-TECH-082
The import pipeline shall not require a running Sphinx build to be present on the back-end server.

DEC-TECH-083
The canonical mapping from Sphinx-Needs types and fields to platform artefact types and fields is defined in `sphinx_needs_mapping_specification.md`.

### 2.10 Configuration Management

DEC-TECH-090
Application configuration shall be loaded from environment variables.

DEC-TECH-091
The following environment variables are required for back-end operation:

```
AAC_DATABASE_URL          PostgreSQL DSN (e.g., postgresql+asyncpg://user:pass@host/db)
AAC_REDIS_URL             Redis connection URL (e.g., redis://localhost:6379/0)
AAC_JWT_SECRET            Secret key for JWT signing (min 32 characters)
AAC_JWT_EXPIRY_HOURS      Token expiry in hours (default: 8)
AAC_ENVIRONMENT           Deployment environment: development | staging | production
AAC_LOG_LEVEL             Logging level: DEBUG | INFO | WARNING | ERROR
AAC_CORS_ORIGINS          Comma-separated list of allowed CORS origins
AAC_HTTPS_REQUIRED        Whether to enforce HTTPS: true | false (default: true in production)
```

DEC-TECH-092
Sensitive configuration values (database credentials, JWT secret) shall never be written to application logs, error messages, or API responses.

DEC-TECH-093
A `.env` file may be used in development environments. `.env` files shall not be committed to version control.

---

## 3. Project Structure

Function ownership, interfaces, dependency direction, and transaction boundaries
are controlled by `software_architecture.md`. The package tree below is a
technology-oriented deployment layout and shall conform to that architecture.

DEC-TECH-100
The back-end shall be organized as a Python package with the following top-level structure:

```
aac_backend/
├── main.py                    # FastAPI application factory
├── config.py                  # Environment configuration loader
├── database.py                # SQLAlchemy engine and session factory
├── models/                    # SQLAlchemy ORM models (one file per table group)
├── schemas/                   # Pydantic request/response schemas (one file per artefact family)
├── api/                       # FastAPI routers (one file per endpoint family)
│   ├── auth.py
│   ├── projects.py
│   ├── artefacts.py
│   ├── relationships.py
│   ├── imports.py
│   ├── validation.py
│   ├── traceability.py
│   ├── baselines.py
│   ├── tests.py
│   ├── reports.py
│   └── jobs.py
├── services/                  # Business logic services
│   ├── import_service.py      # Sphinx import pipeline
│   ├── validation_service.py  # Rule engine
│   ├── traceability_service.py # Graph traversal
│   ├── impact_service.py      # Impact and suspect propagation
│   ├── baseline_service.py    # Baseline creation and release gate
│   ├── report_service.py      # Report generation
│   └── event_service.py       # Domain event dispatcher
├── workers/                   # ARQ async job definitions
│   ├── import_worker.py
│   ├── validation_worker.py
│   ├── baseline_worker.py
│   ├── impact_worker.py
│   └── report_worker.py
├── rules/                     # Rule catalog and evaluator
│   ├── catalog.py             # Rule definitions loaded from rule_semantics.py
│   ├── evaluator.py           # Rule condition expression evaluator
│   └── rule_semantics.py      # Formalized rule conditions (generated from spec)
└── migrations/                # Alembic migration scripts
    ├── env.py
    └── versions/
```

---

## 4. Deployment Specification

### 4.1 Containerization

DEC-DEPLOY-001
The MVP shall be deployable using Docker Compose.

DEC-DEPLOY-002
The Docker Compose configuration shall define the following services:

```yaml
services:
  api:           # FastAPI application server (uvicorn)
  worker:        # ARQ worker process
  postgres:      # PostgreSQL 15 database
  redis:         # Redis 7 broker
  nginx:         # Reverse proxy with TLS termination (production only)
```

DEC-DEPLOY-003
Each service shall have a defined health check.

DEC-DEPLOY-004
The `api` and `worker` services shall share the same application Docker image.

DEC-DEPLOY-005
Database data shall be persisted to a named Docker volume. Container restarts shall not cause data loss.

### 4.2 Database Initialization

DEC-DEPLOY-010
On first deployment, the database schema shall be created by running Alembic migrations.

DEC-DEPLOY-011
The `api` service startup script shall run pending Alembic migrations before starting the application server.

DEC-DEPLOY-012
An initial Admin user shall be created by a one-time seed script run after migration.

### 4.3 Backup And Restore

DEC-DEPLOY-020
Database backup shall use `pg_dump` in the custom format.

DEC-DEPLOY-021
Backup scripts shall be provided as shell scripts in the `ops/` directory.

DEC-DEPLOY-022
A restore procedure script shall be provided alongside the backup script.

DEC-DEPLOY-023
Backup frequency and retention policy are deployment-operator responsibilities and are not enforced by the tool.

### 4.4 Local Development Environment

DEC-DEPLOY-030
Local development shall use `docker compose up` with the development profile to start PostgreSQL and Redis only. The FastAPI application and ARQ worker shall run outside Docker in a Python virtual environment.

DEC-DEPLOY-031
A `Makefile` shall provide standard targets: `make dev`, `make migrate`, `make test`, `make lint`.

DEC-DEPLOY-032
A `requirements.txt` and `requirements-dev.txt` shall be maintained for production and development dependencies respectively.

---

## 5. Performance Benchmarks

DEC-PERF-001
The following response time targets apply for MVP at the scale defined in `database_requirements.md` (500 requirements, 100 components, 5,000 test results, 10,000 relationships):

| Operation | Target P95 Latency |
|-----------|-------------------|
| GET single artefact | < 100 ms |
| POST/PUT artefact (non-async) | < 200 ms |
| Forward/backward trace (single artefact, depth ≤ 5) | < 500 ms |
| Full traceability matrix (project scope) | < 5 seconds (async job) |
| Validation run (project scope) | < 30 seconds (async job) |
| Baseline creation (project scope) | < 60 seconds (async job) |
| Impact analysis (single artefact) | < 2 seconds (async job) |
| Sphinx import (500 artefacts) | < 120 seconds (async job) |

DEC-PERF-002
Performance tests shall use a seeded dataset of the scale defined in `database_requirements.md`.

DEC-PERF-003
If any benchmark exceeds its target by more than 2x in CI, it shall be treated as a blocking defect.

---

## 6. Security Requirements

DEC-SEC-001
All API endpoints except `/api/v1/auth/login` shall require a valid JWT.

DEC-SEC-002
SQL injection shall be prevented by exclusive use of parameterized queries through SQLAlchemy.

DEC-SEC-003
The application shall deny cross-origin requests by default. Allowed origins
shall be configured via `AAC_CORS_ORIGINS`; wildcard origins shall not be used
with credentials.

DEC-SEC-004
The API shall not expose internal stack traces, SQL errors, or database structure in error responses. Errors shall be logged server-side and a sanitized message returned to the client.

DEC-SEC-005
File upload endpoints (e.g., Sphinx JSON import) shall validate content type and
reject input above 50 MB before buffering the complete body in application
memory.

DEC-SEC-006
The audit trail shall be append-only. No API endpoint shall permit deletion or modification of audit events.
