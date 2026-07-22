#!/usr/bin/env bash
set -euo pipefail

postgres_container="aac-web-postgres-$$"
redis_container="aac-web-redis-$$"
api_pid=""
worker_pid=""
api_log="$(mktemp)"
worker_log="$(mktemp)"

cleanup() {
    status=$?
    if [[ -n "${worker_pid}" ]]; then
        kill "${worker_pid}" >/dev/null 2>&1 || true
        wait "${worker_pid}" >/dev/null 2>&1 || true
    fi
    if [[ -n "${api_pid}" ]]; then
        kill "${api_pid}" >/dev/null 2>&1 || true
        wait "${api_pid}" >/dev/null 2>&1 || true
    fi
    docker stop "${redis_container}" "${postgres_container}" >/dev/null 2>&1 || true
    if [[ "${status}" -ne 0 ]]; then
        printf '\nFastAPI log:\n' >&2
        cat "${api_log}" >&2
        printf '\nARQ worker log:\n' >&2
        cat "${worker_log}" >&2
    fi
    rm -f "${api_log}" "${worker_log}"
    exit "${status}"
}
trap cleanup EXIT

docker run \
    --detach \
    --rm \
    --name "${postgres_container}" \
    --env POSTGRES_DB=postgres \
    --env POSTGRES_USER=aac \
    --env POSTGRES_PASSWORD=aac \
    --publish 127.0.0.1::5432 \
    postgres:16-alpine >/dev/null

docker run \
    --detach \
    --rm \
    --name "${redis_container}" \
    --publish 127.0.0.1::6379 \
    redis:7-alpine >/dev/null

for _ in $(seq 1 60); do
    if docker exec "${postgres_container}" pg_isready -U aac -d postgres >/dev/null 2>&1 &&
        docker exec "${redis_container}" redis-cli ping 2>/dev/null | grep -q PONG; then
        break
    fi
    sleep 0.25
done

if ! docker exec "${postgres_container}" pg_isready -U aac -d postgres >/dev/null; then
    docker logs "${postgres_container}"
    exit 1
fi
if ! docker exec "${redis_container}" redis-cli ping | grep -q PONG; then
    docker logs "${redis_container}"
    exit 1
fi

postgres_port="$(
    docker inspect \
        --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' \
        "${postgres_container}"
)"
redis_port="$(
    docker inspect \
        --format '{{(index (index .NetworkSettings.Ports "6379/tcp") 0).HostPort}}' \
        "${redis_container}"
)"
web_port="$(
    python3 -c \
        'import socket; s=socket.socket(); s.bind(("127.0.0.1", 0)); print(s.getsockname()[1]); s.close()'
)"

export AAC_DATABASE_URL="postgresql+asyncpg://aac:aac@127.0.0.1:${postgres_port}/postgres"
export AAC_REDIS_URL="redis://127.0.0.1:${redis_port}/0"
export AAC_JWT_SECRET="web-integration-secret-web-integration-secret"
export AAC_ENVIRONMENT="test"
export AAC_WEB_BASE_URL="http://127.0.0.1:${web_port}/app/"

.venv/bin/alembic upgrade head
.venv/bin/python -m aac_backend.cli create-admin \
    --username webadmin \
    --display-name "Web Integration Admin" \
    --email webadmin@example.com \
    --password "WebIntegration-123!"

.venv/bin/uvicorn aac_backend.main:app \
    --host 127.0.0.1 \
    --port "${web_port}" >"${api_log}" 2>&1 &
api_pid=$!

for _ in $(seq 1 80); do
    if curl -fsS "http://127.0.0.1:${web_port}/api/v1/health" >/dev/null 2>&1; then
        break
    fi
    if ! kill -0 "${api_pid}" >/dev/null 2>&1; then
        cat "${api_log}" >&2
        exit 1
    fi
    sleep 0.25
done

if ! curl -fsS "http://127.0.0.1:${web_port}/api/v1/health" >/dev/null; then
    cat "${api_log}" >&2
    exit 1
fi

.venv/bin/arq aac_backend.workers.settings.WorkerSettings >"${worker_log}" 2>&1 &
worker_pid=$!
for _ in $(seq 1 40); do
    if grep -q "Starting worker" "${worker_log}"; then
        break
    fi
    if ! kill -0 "${worker_pid}" >/dev/null 2>&1; then
        cat "${worker_log}" >&2
        exit 1
    fi
    sleep 0.25
done

npx playwright test --config tests/web-real/playwright.config.js
