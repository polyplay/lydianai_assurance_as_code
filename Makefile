.PHONY: install lint test compile migrate dev worker compose-up compose-down

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/pytest -q

compile:
	python3 -m compileall aac_backend tests

migrate:
	.venv/bin/alembic upgrade head

dev:
	.venv/bin/uvicorn aac_backend.main:app --reload --host 0.0.0.0 --port 8000

worker:
	.venv/bin/arq aac_backend.workers.settings.WorkerSettings

compose-up:
	docker compose up --build

compose-down:
	docker compose down
