#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/lydianai-aac"
BACKUP_FILE=""

usage() {
  cat <<'USAGE'
Usage: installer/backend/restore.sh --backup-file PATH [options]

Restores a PostgreSQL custom-format dump into the installed backend stack.
This replaces database contents. Stop application traffic before restoring.

Options:
  --install-dir PATH  Installation directory. Default: /opt/lydianai-aac
  --backup-file PATH  Backup file produced by backup.sh.
  -h, --help          Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --backup-file)
      BACKUP_FILE="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "unknown option: $1" >&2
      usage
      exit 2
      ;;
  esac
done

if [[ -z "$BACKUP_FILE" || ! -f "$BACKUP_FILE" ]]; then
  echo "--backup-file is required and must point to an existing file" >&2
  exit 1
fi

ENV_FILE="$INSTALL_DIR/.env"
COMPOSE_FILE="$INSTALL_DIR/installer/backend/docker-compose.backend.yml"

if [[ ! -f "$ENV_FILE" || ! -f "$COMPOSE_FILE" ]]; then
  echo "installer files not found under $INSTALL_DIR" >&2
  exit 1
fi

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

echo "Stopping API and worker before restore"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" stop api worker

echo "Dropping and recreating database ${AAC_POSTGRES_DB:-aac}"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  dropdb -U "${AAC_POSTGRES_USER:-aac}" --if-exists "${AAC_POSTGRES_DB:-aac}"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  createdb -U "${AAC_POSTGRES_USER:-aac}" "${AAC_POSTGRES_DB:-aac}"

echo "Restoring $BACKUP_FILE"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  pg_restore -U "${AAC_POSTGRES_USER:-aac}" -d "${AAC_POSTGRES_DB:-aac}" --no-owner < "$BACKUP_FILE"

echo "Starting backend"
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

echo "Restore complete."

