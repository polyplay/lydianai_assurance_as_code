#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/lydianai-aac"
BACKUP_DIR=""

usage() {
  cat <<'USAGE'
Usage: installer/backend/backup.sh [options]

Creates a PostgreSQL dump from the installed backend stack.

Options:
  --install-dir PATH  Installation directory. Default: /opt/lydianai-aac
  --backup-dir PATH   Backup directory. Default: <install-dir>/backups
  -h, --help          Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --backup-dir)
      BACKUP_DIR="$2"
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

ENV_FILE="$INSTALL_DIR/.env"
COMPOSE_FILE="$INSTALL_DIR/installer/backend/docker-compose.backend.yml"
BACKUP_DIR="${BACKUP_DIR:-$INSTALL_DIR/backups}"

if [[ ! -f "$ENV_FILE" || ! -f "$COMPOSE_FILE" ]]; then
  echo "installer files not found under $INSTALL_DIR" >&2
  exit 1
fi

mkdir -p "$BACKUP_DIR"
STAMP="$(date -u +%Y%m%dT%H%M%SZ)"
OUT="$BACKUP_DIR/aac-postgres-$STAMP.dump"

set -a
# shellcheck disable=SC1090
. "$ENV_FILE"
set +a

docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T postgres \
  pg_dump -U "${AAC_POSTGRES_USER:-aac}" -d "${AAC_POSTGRES_DB:-aac}" -Fc > "$OUT"

chmod 600 "$OUT"
echo "Created backup: $OUT"

