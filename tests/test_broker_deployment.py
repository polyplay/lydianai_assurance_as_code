from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "compose_path",
    ["docker-compose.yml", "installer/backend/docker-compose.backend.yml"],
)
def test_acc_lic_013_valkey_preserves_broker_connection_contract(compose_path: str) -> None:
    compose = yaml.safe_load((ROOT / compose_path).read_text(encoding="utf-8"))
    services = compose["services"]

    assert services["redis"]["image"] == "valkey/valkey:8.1.10-alpine"
    assert services["redis"]["healthcheck"]["test"] == ["CMD", "valkey-cli", "ping"]
    for service_name in ("api", "worker"):
        assert services[service_name]["environment"]["AAC_REDIS_URL"] == "redis://redis:6379/0"
        assert services[service_name]["depends_on"]["redis"] == {"condition": "service_healthy"}

    if compose_path == "docker-compose.yml":
        assert services["redis"]["ports"] == ["${AAC_REDIS_PORT:-6379}:6379"]
    else:
        assert "ports" not in services["redis"]
        assert services["redis"]["expose"] == ["6379"]


def test_acc_lic_014_valkey_does_not_reuse_original_redis_persistence() -> None:
    compose = yaml.safe_load(
        (ROOT / "installer/backend/docker-compose.backend.yml").read_text(encoding="utf-8")
    )

    assert compose["services"]["redis"]["volumes"] == ["valkey_data:/data"]
    assert "valkey_data" in compose["volumes"]
    assert all(
        not mount.startswith("redis_data:")
        for service in compose["services"].values()
        for mount in service.get("volumes", [])
    )
