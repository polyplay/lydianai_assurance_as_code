# Valkey Broker Migration

The default broker is `valkey/valkey:8.1.10-alpine`. The application remains
[Apache-2.0](../LICENSE); Valkey has its own
[BSD-3-Clause server license](../LICENSES/Valkey-8.1.10.txt), with upstream
attributions retained in [Third-Party License Notices](../THIRD_PARTY_NOTICES.md).
Existing ARQ clients
continue using `AAC_REDIS_URL`, `redis://` URLs, port 6379, and Compose service
name `redis`. No application database migration or Python dependency changes
are introduced by this replacement.

## New Installations

Use the usual Compose or installer instructions. The `redis` service now starts
Valkey, and its health check uses `valkey-cli ping`. Production persistence is
stored in `valkey_data`; the PostgreSQL and upload volumes are unchanged.

## Existing Redis Installations

Perform an operator-controlled upgrade before running the new installer or
bringing up the updated production Compose file. PostgreSQL retains application
job records, but queued payloads and in-flight coordination live in the broker;
changing servers does not automatically replay those records.

Redis 7.4 and later RDB/AOF files are incompatible with Valkey. Do not rename,
copy, restore, or mount the old `redis_data` volume as `valkey_data`. The new
Compose definition creates separate storage and leaves the original volume
intact. Do not run `docker compose down -v` or volume-pruning commands during
this procedure.

1. Retain the original full deployment configuration/source revision, exact
   Redis image identity, and securely stored environment file. Record the
   existing Compose project name and old Redis volume identity. Keep the project
   name unchanged throughout the upgrade so PostgreSQL/upload volumes continue
   to resolve to their existing data.
2. Prevent new user/API submissions while keeping controlled operator access
   for draining existing work. Complete, explicitly cancel, or resolve every
   queued/running/waiting job through supported workflows. Verify the Jobs view
   and the original broker's `redis-cli ZCARD arq:queue`; do not proceed while
   application work remains. Drain pending event dispatch as well. If work
   cannot be drained, retain the old deployment and plan an explicit migration.
3. Stop API and workers after draining so they cannot enqueue more work. Create
   a PostgreSQL backup with the existing backup script. Save and back up the
   original Redis persistence using the original Redis server, then stop it.
   Keep both the old volume and its backup for rollback; these files are not
   inputs to Valkey.
4. Install the updated deployment files using the same installation directory,
   Compose project name, and environment. Start only the `redis` service first.
   It uses the new Valkey image and a fresh `valkey_data` volume. Do not run a
   second copy of the original stack against the same PostgreSQL database.
5. Verify `docker compose --env-file .env -f
   installer/backend/docker-compose.backend.yml exec redis valkey-cli ping`
   returns `PONG`. Inspect `valkey-cli INFO server` for `valkey_version`, and
   confirm the container mounts the new volume rather than old Redis data.
6. Start API and workers, check migrations/startup and health, and run a
   controlled queued validation job to completion. Confirm the resulting job
   record in PostgreSQL and inspect API/worker logs before reopening client
   access. API and job contracts remain unchanged.
7. Retain the original Redis artifacts until this verification and the agreed
   rollback window are complete. Remove them only by a separate deliberate
   operator action.

## Rollback

Before accepting new work, stop the new API/worker/Valkey services, restore the
original deployment configuration and exact Redis image, and start the original
broker against its original volume. Keep the existing PostgreSQL/upload volumes
and environment. Check health and queued work before reopening access.

After new work has been accepted on Valkey, first drain that work and preserve
its data and PostgreSQL state. Restoring the old Redis volume alone would not
recover the new queue. There is no automatic cross-server persistence conversion
or queue replay in this change.

## Verification

`bash scripts/run_web_integration_tests.sh` starts disposable PostgreSQL and
Valkey containers, exercises ARQ transport, then runs the real API/worker browser
workflow. It requires Docker daemon access and installed browser dependencies.
The standalone broker test can target an explicitly disposable Valkey service:

```bash
AAC_TEST_VALKEY_URL=redis://127.0.0.1:6379/0 \
  .venv/bin/pytest -q tests/integration/test_valkey_queue.py
```

The test uses isolated queue/job keys and does not flush the database. Upstream
protocol and persistence guidance is available in the
[Valkey migration guide](https://valkey.io/topics/migration/).
