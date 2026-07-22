import json
from argparse import Namespace
from pathlib import Path

import pytest
import yaml
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from aac_backend import cli
from aac_backend.api.imports import _bounded_sphinx_import_payload
from aac_backend.config import Settings
from aac_backend.main import create_app


def test_http_errors_use_standard_envelope() -> None:
    app = create_app()

    @app.get("/contract-error")
    async def contract_error():
        raise HTTPException(status_code=409, detail="Stale revision")

    client = TestClient(app)
    response = client.get(
        "/contract-error",
        headers={"X-Request-ID": "REQ_contract", "X-Correlation-ID": "CORR_contract"},
    )

    assert response.status_code == 409
    assert response.json() == {
        "status": "error",
        "request_id": "REQ_contract",
        "correlation_id": "CORR_contract",
        "error": {
            "code": "conflict",
            "message": "Stale revision",
            "details": None,
        },
    }


def test_production_configuration_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="AAC_JWT_SECRET"):
        Settings(environment="production", https_required=True).validate_runtime_configuration()
    with pytest.raises(RuntimeError, match="AAC_HTTPS_REQUIRED"):
        Settings(
            environment="production",
            jwt_secret="j" * 32,
            secret_encryption_key="e" * 32,
        ).validate_runtime_configuration()


def test_production_compose_exposes_only_tls_proxy() -> None:
    root = Path(__file__).resolve().parents[1]
    compose = yaml.safe_load(
        (root / "installer/backend/docker-compose.backend.yml").read_text(
            encoding="utf-8"
        )
    )
    services = compose["services"]
    for service_name in ("postgres", "redis", "api", "worker"):
        assert "ports" not in services[service_name]
    assert services["api"]["environment"]["AAC_ENVIRONMENT"] == "production"
    assert services["api"]["environment"]["AAC_HTTPS_REQUIRED"] == "true"
    assert services["nginx"]["ports"] == [
        "${AAC_HTTP_PORT:-80}:80",
        "${AAC_HTTPS_PORT:-443}:443",
    ]


@pytest.mark.asyncio
async def test_sphinx_import_rejects_oversized_stream(monkeypatch) -> None:
    monkeypatch.setenv("AAC_MAX_IMPORT_BYTES", "8")
    from aac_backend.config import get_settings

    get_settings.cache_clear()
    chunks = iter([b'{"source', b'_root":""}'])

    async def receive():
        try:
            body = next(chunks)
            return {"type": "http.request", "body": body, "more_body": True}
        except StopIteration:
            return {"type": "http.request", "body": b"", "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/projects/P/imports/sphinx",
            "headers": [(b"content-type", b"application/json")],
        },
        receive,
    )
    with pytest.raises(HTTPException) as error:
        await _bounded_sphinx_import_payload(request)
    assert error.value.status_code == 413
    get_settings.cache_clear()


def test_cli_baseline_comparison_uses_two_baselines(monkeypatch, capsys) -> None:
    captured = {}

    def request(args, method, path, body=None):
        captured.update(method=method, path=path, body=body)
        return {"status": "accepted"}

    monkeypatch.setattr(cli, "_api_request", request)
    cli._report(
        Namespace(
            base_url="https://example.test",
            token="token",
            project_id="PROJ 1",
            report_type="baseline_comparison",
            baseline_id=None,
            left_baseline_id="BASE_1",
            right_baseline_id="BASE_2",
        )
    )

    assert captured["body"]["left_baseline_id"] == "BASE_1"
    assert captured["body"]["right_baseline_id"] == "BASE_2"
    assert "baseline_id" not in captured["body"]
    assert json.loads(capsys.readouterr().out)["status"] == "accepted"


def test_cli_delete_sends_revision_token(monkeypatch) -> None:
    captured = {}

    def request(args, method, path, body=None):
        captured.update(method=method, path=path, body=body)
        return {"status": "success"}

    monkeypatch.setattr(cli, "_api_request", request)
    cli._artefact_delete(
        Namespace(
            base_url="https://example.test",
            token="token",
            project_id="PROJ 1",
            artefact_id="ART/1",
            base_revision_id="AREV_1",
        )
    )

    assert captured == {
        "method": "DELETE",
        "path": "/api/v1/projects/PROJ%201/artefacts/ART%2F1",
        "body": {"base_revision_id": "AREV_1"},
    }
