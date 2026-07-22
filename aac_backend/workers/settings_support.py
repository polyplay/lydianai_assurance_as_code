from arq.connections import RedisSettings

from aac_backend.config import get_settings


def redis_settings() -> RedisSettings:
    url = get_settings().redis_url
    if not url.startswith("redis://"):
        return RedisSettings()
    without_scheme = url.removeprefix("redis://").split("/", 1)[0]
    host, _, port = without_scheme.partition(":")
    return RedisSettings(host=host or "localhost", port=int(port or 6379))
