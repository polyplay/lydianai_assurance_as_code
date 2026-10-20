# Backend Installer Guide

## Purpose

This guide explains how to install and operate the backend stack for LydianAI Assurance-as-Code. The backend stack includes:

- PostgreSQL database
- Valkey queue (Redis-compatible protocol)
- FastAPI backend
- ARQ worker
- nginx reverse proxy
- lightweight web console served by the backend

## Prerequisites

Install these on the target Linux host:

- Docker Engine
- Docker Compose plugin
- `bash`
- `python3`
- `openssl` for stronger generated secrets
- `systemd` if you want the installer to register the backend as a service

The installer assumes outbound network access is available while building container images.

## Production Install

Run from the repository root:

```bash
sudo installer/backend/install.sh \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password 'replace-this-password'
```

Default installation path:

```text
/opt/lydianai-aac
```

The installer:

- copies the application into the installation directory
- creates `/opt/lydianai-aac/.env` with generated database, JWT, and secret-encryption values
- starts PostgreSQL, Valkey, API, worker, and nginx with Docker Compose
- installs and enables `lydianai-aac.service`
- optionally creates the first admin user

## Custom Install Directory

Existing Redis installations must complete the
[Valkey migration procedure](valkey_migration.md) before running an upgrade.
The Compose service name `redis` and `AAC_REDIS_URL` remain compatible;
production Valkey uses a new `valkey_data` volume and does not read old Redis
persistence.

```bash
sudo installer/backend/install.sh \
  --install-dir /srv/lydianai-aac \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password 'replace-this-password'
```

## Install Without systemd

```bash
installer/backend/install.sh \
  --install-dir "$HOME/lydianai-aac" \
  --no-systemd
```

## Important Files

```text
/opt/lydianai-aac/.env
/opt/lydianai-aac/installer/backend/docker-compose.backend.yml
/etc/systemd/system/lydianai-aac.service
```

Treat `.env` as a secret file. It contains database credentials, JWT signing material, and the connector-secret encryption key.

## Access URLs

The default production installer ports are:

```text
Web console: http://127.0.0.1:18000/app
API docs:    http://127.0.0.1:18000/api/v1/docs
Health:      http://127.0.0.1:18000/api/v1/health
nginx:       http://127.0.0.1:18080
```

Change ports in `/opt/lydianai-aac/.env`, then restart:

```bash
sudo systemctl restart lydianai-aac
```

## Service Management

With systemd:

```bash
sudo systemctl status lydianai-aac
sudo systemctl restart lydianai-aac
sudo systemctl stop lydianai-aac
```

With Docker Compose:

```bash
cd /opt/lydianai-aac
sudo docker compose --env-file .env -f installer/backend/docker-compose.backend.yml ps
sudo docker compose --env-file .env -f installer/backend/docker-compose.backend.yml logs -f api
sudo docker compose --env-file .env -f installer/backend/docker-compose.backend.yml logs -f worker
```

## Create Additional Admins

```bash
cd /opt/lydianai-aac
sudo docker compose --env-file .env -f installer/backend/docker-compose.backend.yml exec -T api \
  python -m aac_backend.cli create-admin \
  --username second-admin \
  --display-name "Second Admin" \
  --email second-admin@example.com \
  --password 'replace-this-password'
```

## Backup

Create a PostgreSQL backup:

```bash
sudo /opt/lydianai-aac/installer/backend/backup.sh
```

Default backup directory:

```text
/opt/lydianai-aac/backups
```

Copy backups to secure external storage. The backup may contain regulated project evidence metadata.

## Restore

Restoring replaces database contents. Stop user traffic before restoring.

```bash
sudo /opt/lydianai-aac/installer/backend/restore.sh \
  --backup-file /opt/lydianai-aac/backups/aac-postgres-YYYYMMDDTHHMMSSZ.dump
```

After restore, confirm health:

```bash
curl http://127.0.0.1:18000/api/v1/health
```

## Upgrade

For a new application version:

1. Back up the database.
2. Stop the service.
3. Run the installer again from the new repository checkout, using the same `--install-dir`.
4. Start the service.
5. Confirm health and login.

Example:

```bash
sudo /opt/lydianai-aac/installer/backend/backup.sh
sudo systemctl stop lydianai-aac
sudo installer/backend/install.sh --install-dir /opt/lydianai-aac
sudo systemctl start lydianai-aac
curl http://127.0.0.1:18000/api/v1/health
```

Existing `.env` is preserved by the installer.

## Uninstall

Stop services but keep installed files and data volumes:

```bash
sudo /opt/lydianai-aac/installer/backend/uninstall.sh
```

Remove services, installed files, and Docker volumes:

```bash
sudo /opt/lydianai-aac/installer/backend/uninstall.sh --remove-data
```

Use `--remove-data` only after confirming backups.

## Production Hardening Checklist

- Replace default admin passwords immediately.
- Restrict host firewall access to API/nginx ports.
- Put TLS termination in front of nginx for remote access.
- Set a stable `AAC_SECRET_ENCRYPTION_KEY` before creating repository connectors.
- Keep `/opt/lydianai-aac/.env` readable only by administrators.
- Schedule database backups and periodically test restore.
- Monitor API and worker logs.
- Use GitHub App credentials with least-privilege repository permissions.
