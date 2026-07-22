.PHONY: install install-web lint test test-web test-web-e2e test-web-integration test-integration compile migrate dev worker compose-up compose-down smoke-test

install:
	python3 -m venv .venv
	.venv/bin/pip install -r requirements-dev.txt

install-web:
	npm ci
	npx playwright install chromium

lint:
	.venv/bin/ruff check .

test:
	.venv/bin/pytest -q

test-web:
	npm run test:web:unit

test-web-e2e:
	npm run test:web:e2e

test-web-integration:
	npm run test:web:integration

test-integration:
	bash scripts/run_db_integration_tests.sh

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

smoke-test:
	bash scripts/e2e_smoke_test.sh
