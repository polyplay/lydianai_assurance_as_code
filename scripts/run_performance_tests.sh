#!/usr/bin/env bash
set -euo pipefail

container_name="aac-performance-postgres-$$"

cleanup() {
    docker stop "${container_name}" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker run \
    --detach \
    --rm \
    --name "${container_name}" \
    --env POSTGRES_DB=aac_performance \
    --env POSTGRES_USER=aac \
    --env POSTGRES_PASSWORD=aac \
    --publish 127.0.0.1::5432 \
    postgres:16-alpine >/dev/null

for _ in $(seq 1 60); do
    if docker exec "${container_name}" \
        psql -U aac -d aac_performance -c 'SELECT 1' >/dev/null 2>&1; then
        break
    fi
    sleep 0.25
done

if ! docker exec "${container_name}" \
    psql -U aac -d aac_performance -c 'SELECT 1' >/dev/null 2>&1; then
    docker logs "${container_name}"
    exit 1
fi

port="$(
    docker inspect \
        --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' \
        "${container_name}"
)"
database_url="postgresql+asyncpg://aac:aac@127.0.0.1:${port}/aac_performance"

AAC_DATABASE_URL="${database_url}" .venv/bin/alembic upgrade head
.venv/bin/python ops/seed_performance_dataset.py --database-url "${database_url}"
.venv/bin/python ops/run_performance_benchmarks.py \
    --database-url "${database_url}" \
    --output verification/generated/performance-results.json
