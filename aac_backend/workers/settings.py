from arq.cron import cron

from aac_backend.services.startup_service import initialize_application_state
from aac_backend.workers.tasks import (
    baseline_job,
    outbox_dispatch_job,
    impact_job,
    IMPORT_MAX_TRIES,
    import_sphinx_job,
    release_gate_job,
    repository_scan_job,
    validation_job,
)
from aac_backend.workers.settings_support import redis_settings


async def on_startup(ctx) -> None:
    await initialize_application_state()


class WorkerSettings:
    functions = [
        import_sphinx_job,
        validation_job,
        baseline_job,
        impact_job,
        release_gate_job,
        repository_scan_job,
    ]
    cron_jobs = [cron(outbox_dispatch_job, second={0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55})]
    max_tries = IMPORT_MAX_TRIES
    on_startup = on_startup
    redis_settings = redis_settings()
