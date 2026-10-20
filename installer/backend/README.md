# Backend Installer

This folder contains a production-oriented Docker Compose installer for the LydianAI Assurance-as-Code backend.

## Install

From the repository root:

```bash
sudo installer/backend/install.sh \
  --admin-username admin \
  --admin-email admin@example.com \
  --admin-password 'change-me' \
  --tls-cert /etc/letsencrypt/live/aac.example.com/fullchain.pem \
  --tls-key /etc/letsencrypt/live/aac.example.com/privkey.pem
```

The default installation directory is `/opt/lydianai-aac`. The installer requires a TLS certificate and key when starting services, creates generated application secrets, and exposes only nginx on ports 80 and 443. PostgreSQL, Valkey, and the API remain internal to the Compose network.

Valkey keeps the `redis` service hostname and `AAC_REDIS_URL` setting. Existing
Redis installations must follow the
[migration procedure](../../documentation/valkey_migration.md) before upgrading.
Production Valkey uses fresh `valkey_data` storage; the old Redis volume is
retained separately.

## Licenses

Application code: [Apache-2.0](../../LICENSE). Valkey server:
[BSD-3-Clause](../../LICENSES/Valkey-8.1.10.txt). See
[Third-Party License Notices](../../THIRD_PARTY_NOTICES.md) for upstream
attributions and dependency references. Other image components retain their
own licenses.

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
