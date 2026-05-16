#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/lydianai-aac"
REMOVE_DATA=0

usage() {
  cat <<'USAGE'
Usage: installer/backend/uninstall.sh [options]

Stops the backend stack and optionally removes installed data.

Options:
  --install-dir PATH  Installation directory. Default: /opt/lydianai-aac
  --remove-data       Remove Docker volumes and the installation directory.
  -h, --help          Show this help.
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --remove-data)
      REMOVE_DATA=1
      shift
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

if [[ -f "$COMPOSE_FILE" && -f "$ENV_FILE" ]]; then
  if [[ "$REMOVE_DATA" -eq 1 ]]; then
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v
  else
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down
  fi
fi

if [[ -f /etc/systemd/system/lydianai-aac.service ]]; then
  systemctl disable --now lydianai-aac.service || true
  rm -f /etc/systemd/system/lydianai-aac.service
  systemctl daemon-reload
fi

if [[ "$REMOVE_DATA" -eq 1 ]]; then
  rm -rf "$INSTALL_DIR"
fi

echo "Uninstall complete."

