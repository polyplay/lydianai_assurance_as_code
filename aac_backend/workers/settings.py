from arq.connections import RedisSettings

from aac_backend.config import get_settings
from aac_backend.services.startup_service import initialize_application_state
from aac_backend.workers.tasks import (
    baseline_job,
    impact_job,
    import_sphinx_job,
    release_gate_job,
    repository_scan_job,
    validation_job,
)


def redis_settings() -> RedisSettings:
    url = get_settings().redis_url
    # ARQ accepts host/port settings; URL parsing is intentionally minimal for MVP local Redis.
    if not url.startswith("redis://"):
        return RedisSettings()
    without_scheme = url.removeprefix("redis://").split("/", 1)[0]
    host, _, port = without_scheme.partition(":")
    return RedisSettings(host=host or "localhost", port=int(port or 6379))


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
    on_startup = on_startup
    redis_settings = redis_settings()
