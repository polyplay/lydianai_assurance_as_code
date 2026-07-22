#!/usr/bin/env bash
set -euo pipefail

container_name="aac-backup-restore-postgres-$$"
backup_file="$(mktemp --suffix=.dump)"

cleanup() {
    docker stop "${container_name}" >/dev/null 2>&1 || true
    rm -f "${backup_file}"
}
trap cleanup EXIT

docker run \
    --detach \
    --rm \
    --name "${container_name}" \
    --env POSTGRES_DB=aac_restore \
    --env POSTGRES_USER=aac \
    --env POSTGRES_PASSWORD=aac \
    --publish 127.0.0.1::5432 \
    postgres:16-alpine >/dev/null

for _ in $(seq 1 60); do
    if docker exec "${container_name}" \
        psql -U aac -d aac_restore -c 'SELECT 1' >/dev/null 2>&1; then
        break
    fi
    sleep 0.25
done

port="$(
    docker inspect \
        --format '{{(index (index .NetworkSettings.Ports "5432/tcp") 0).HostPort}}' \
        "${container_name}"
)"
async_url="postgresql+asyncpg://aac:aac@127.0.0.1:${port}/aac_restore"
sync_url="postgresql://aac:aac@127.0.0.1:${port}/aac_restore"

AAC_DATABASE_URL="${async_url}" .venv/bin/alembic upgrade head
PGPASSWORD=aac psql "${sync_url}" -v ON_ERROR_STOP=1 <<'SQL'
INSERT INTO projects (
    project_id, project_key, name, description, status, created_at, updated_at
) VALUES (
    'PROJ_BACKUP', 'BACKUP', 'Backup restore evidence', '', 'active', now(), now()
);
SQL

PGPASSWORD=aac pg_dump "${sync_url}" --format=custom --file="${backup_file}"

docker exec "${container_name}" dropdb -U aac aac_restore
docker exec "${container_name}" createdb -U aac aac_restore
PGPASSWORD=aac pg_restore \
    --dbname="${sync_url}" \
    --no-owner \
    --exit-on-error \
    "${backup_file}"

restored="$(
    PGPASSWORD=aac psql "${sync_url}" -Atc \
        "SELECT count(*) FROM projects WHERE project_id = 'PROJ_BACKUP'"
)"
if [[ "${restored}" != "1" ]]; then
    echo "restored project marker was not found" >&2
    exit 1
fi

echo "Backup/restore test passed."
