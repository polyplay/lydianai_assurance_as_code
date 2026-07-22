#!/usr/bin/env bash
set -euo pipefail

INSTALL_DIR="/opt/lydianai-aac"
ADMIN_USERNAME=""
ADMIN_EMAIL=""
ADMIN_PASSWORD=""
INSTALL_SYSTEMD=1
START_STACK=1
TLS_CERT=""
TLS_KEY=""

usage() {
  cat <<'USAGE'
Usage: installer/backend/install.sh [options]

Installs the LydianAI Assurance-as-Code backend using Docker Compose.

Options:
  --install-dir PATH       Installation directory. Default: /opt/lydianai-aac
  --admin-username NAME    Create an initial admin user.
  --admin-email EMAIL      Email for the initial admin user.
  --admin-password PASS    Password for the initial admin user.
  --tls-cert PATH          PEM certificate chain for HTTPS.
  --tls-key PATH           PEM private key for HTTPS.
  --no-systemd             Do not install the systemd unit.
  --no-start               Copy files and create .env, but do not start services.
  -h, --help               Show this help.

Examples:
  sudo installer/backend/install.sh \
    --admin-username admin \
    --admin-email admin@example.com \
    --admin-password 'change-me'

  sudo installer/backend/install.sh --install-dir /srv/aac --no-systemd
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --install-dir)
      INSTALL_DIR="$2"
      shift 2
      ;;
    --admin-username)
      ADMIN_USERNAME="$2"
      shift 2
      ;;
    --admin-email)
      ADMIN_EMAIL="$2"
      shift 2
      ;;
    --admin-password)
      ADMIN_PASSWORD="$2"
      shift 2
      ;;
    --tls-cert)
      TLS_CERT="$2"
      shift 2
      ;;
    --tls-key)
      TLS_KEY="$2"
      shift 2
      ;;
    --no-systemd)
      INSTALL_SYSTEMD=0
      shift
      ;;
    --no-start)
      START_STACK=0
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

require_command() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "required command not found: $1" >&2
    exit 1
  fi
}

random_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n'
  else
    python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48), end="")
PY
  fi
}

require_command docker
require_command python3

if ! docker compose version >/dev/null 2>&1; then
  echo "docker compose plugin is required" >&2
  exit 1
fi

SOURCE_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
COMPOSE_FILE="$INSTALL_DIR/installer/backend/docker-compose.backend.yml"
ENV_FILE="$INSTALL_DIR/.env"

mkdir -p "$INSTALL_DIR"

if [[ "$START_STACK" -eq 1 ]]; then
  if [[ -z "$TLS_CERT" || -z "$TLS_KEY" ]]; then
    echo "--tls-cert and --tls-key are required when starting the production stack" >&2
    exit 2
  fi
  if [[ ! -f "$TLS_CERT" || ! -f "$TLS_KEY" ]]; then
    echo "TLS certificate or key file does not exist" >&2
    exit 2
  fi
fi

echo "Copying application files to $INSTALL_DIR"
tar \
  --exclude='.git' \
  --exclude='.venv' \
  --exclude='.env' \
  --exclude='.env.*' \
  --exclude='.pytest_cache' \
  --exclude='.ruff_cache' \
  --exclude='__pycache__' \
  -C "$SOURCE_ROOT" \
  -cf - . | tar -C "$INSTALL_DIR" -xf -

if [[ ! -f "$ENV_FILE" ]]; then
  DB_PASSWORD="$(random_secret)"
  JWT_SECRET="$(random_secret)"
  ENCRYPTION_KEY="$(random_secret)"
  sed \
    -e "s|CHANGE_ME_DATABASE_PASSWORD|$DB_PASSWORD|g" \
    -e "s|CHANGE_ME_LONG_RANDOM_JWT_SECRET|$JWT_SECRET|g" \
    -e "s|CHANGE_ME_LONG_RANDOM_SECRET_ENCRYPTION_KEY|$ENCRYPTION_KEY|g" \
    "$INSTALL_DIR/installer/backend/production.env.example" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE"
else
  echo "Keeping existing $ENV_FILE"
fi

if [[ -n "$TLS_CERT" && -n "$TLS_KEY" ]]; then
  install -d -m 700 "$INSTALL_DIR/installer/backend/tls"
  install -m 644 "$TLS_CERT" "$INSTALL_DIR/installer/backend/tls/fullchain.pem"
  install -m 600 "$TLS_KEY" "$INSTALL_DIR/installer/backend/tls/privkey.pem"
fi

if [[ "$INSTALL_SYSTEMD" -eq 1 ]]; then
  if [[ "$(id -u)" -ne 0 ]]; then
    echo "systemd installation requires root; rerun with sudo or use --no-systemd" >&2
    exit 1
  fi
  sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" \
    "$INSTALL_DIR/installer/backend/systemd/lydianai-aac.service" \
    > /etc/systemd/system/lydianai-aac.service
  systemctl daemon-reload
  systemctl enable lydianai-aac.service
  echo "Installed and enabled systemd unit: lydianai-aac.service"
fi

if [[ "$START_STACK" -eq 1 ]]; then
  echo "Starting backend stack"
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build

  if [[ -n "$ADMIN_USERNAME" || -n "$ADMIN_EMAIL" || -n "$ADMIN_PASSWORD" ]]; then
    if [[ -z "$ADMIN_USERNAME" || -z "$ADMIN_EMAIL" || -z "$ADMIN_PASSWORD" ]]; then
      echo "admin creation requires --admin-username, --admin-email, and --admin-password" >&2
      exit 1
    fi
    echo "Creating initial admin user $ADMIN_USERNAME"
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" exec -T api \
      python -m aac_backend.cli create-admin \
      --username "$ADMIN_USERNAME" \
      --display-name "$ADMIN_USERNAME" \
      --email "$ADMIN_EMAIL" \
      --password "$ADMIN_PASSWORD" || {
        echo "admin user creation failed; it may already exist" >&2
      }
  fi
fi

HTTPS_PORT="$(grep '^AAC_HTTPS_PORT=' "$ENV_FILE" | cut -d= -f2)"

cat <<EOF

Installation complete.

Application directory: $INSTALL_DIR
Environment file:      $ENV_FILE
Compose file:          $COMPOSE_FILE

Web console:           https://127.0.0.1:${HTTPS_PORT:-443}/app
API docs:              https://127.0.0.1:${HTTPS_PORT:-443}/api/v1/docs

Manage manually:
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" ps
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" logs -f api

Manage with systemd, if installed:
  systemctl status lydianai-aac
  systemctl restart lydianai-aac
EOF
