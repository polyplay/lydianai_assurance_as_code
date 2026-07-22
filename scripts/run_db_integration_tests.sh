#!/usr/bin/env bash
set -euo pipefail

if [[ -n "${AAC_TEST_DATABASE_URL:-}" ]]; then
    exec .venv/bin/pytest -q -m integration "$@"
fi

container_name="aac-integration-postgres-$$"

cleanup() {
    docker stop "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run \
    --detach \
    --rm \
    --name "${container_name}" \
    --env POSTGRES_DB=postgres \
    --env POSTGRES_USER=aac \
    --env POSTGRES_PASSWORD=aac \
    --publish 127.0.0.1::5432 \
    postgres:16-alpine >/dev/null

for _ in $(seq 1 60); do
    if docker exec "${container_name}" pg_isready -U aac -d postgres >/dev/null 2>&1; then
        break
    fi
    sleep 0.25
done

if ! docker exec "${container_name}" pg_isready -U aac -d postgres >/dev/null; then
    docker logs "${container_name}"
    exit 1
fi
port="$(
    docker inspect \
        --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' \
        "${container_name}"
)"

export AAC_TEST_DATABASE_URL="postgresql+asyncpg://aac:aac@127.0.0.1:${port}/postgres"
.venv/bin/pytest -q -m integration "$@"
