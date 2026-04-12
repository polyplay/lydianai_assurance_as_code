# LydianAI Assurance-as-Code

This repository contains the stabilized requirements documents and the initial Python backend
implementation scaffold for the Assurance-as-Code tool.

## Backend Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
alembic upgrade head
aac create-admin --username admin --display-name Admin --email admin@example.com --password 'change-me'
uvicorn aac_backend.main:app --reload
```

The API docs are available at:

```text
http://127.0.0.1:8000/api/v1/docs
```

## Current Implementation Coverage

- FastAPI application factory and route structure.
- SQLAlchemy logical schema and Alembic initial migration.
- Username/password authentication with bcrypt and JWT.
- Project, artefact, relationship, Sphinx import, validation, traceability, baseline,
  release-gate, evidence/report, job, and audit foundations.
- Rule catalog seed for the first MVP blocking rules.
