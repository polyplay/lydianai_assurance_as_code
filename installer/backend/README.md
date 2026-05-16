# Backend Installer

This folder contains a production-oriented Docker Compose installer for the LydianAI Assurance-as-Code backend.

## Install

From the repository root:

```bash
sudo installer/backend/install.sh \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password 'change-me'
```

The default installation directory is `/opt/lydianai-aac`. The installer copies the application, creates `/opt/lydianai-aac/.env` with generated secrets, starts PostgreSQL, Redis, API, worker, and nginx, and installs a `lydianai-aac.service` systemd unit.

## Manage

```bash
sudo systemctl status lydianai-aac
sudo systemctl restart lydianai-aac
sudo systemctl stop lydianai-aac
```

Or with Compose:

```bash
cd /opt/lydianai-aac
docker compose --env-file .env -f installer/backend/docker-compose.backend.yml ps
docker compose --env-file .env -f installer/backend/docker-compose.backend.yml logs -f api
```

## Backup

```bash
sudo /opt/lydianai-aac/installer/backend/backup.sh
```

## Restore

```bash
sudo /opt/lydianai-aac/installer/backend/restore.sh \
  --backup-file /opt/lydianai-aac/backups/aac-postgres-YYYYMMDDTHHMMSSZ.dump
```

## Uninstall

Stop services but keep data:

```bash
sudo /opt/lydianai-aac/installer/backend/uninstall.sh
```

Remove services, volumes, and installed files:

```bash
sudo /opt/lydianai-aac/installer/backend/uninstall.sh --remove-data
```
