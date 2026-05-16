import asyncio
import hashlib
import hmac
from types import SimpleNamespace

import pytest

from aac_backend.api.repositories import delete_repository_connector
from aac_backend.models.artefacts import Artefact
from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.models.repository_integrations import ConnectorSecret, RepositoryConnector, RepositoryRevision, RepositoryScanRun
from aac_backend.models.validation import ValidationRun
import aac_backend.services.repository_integration_service as repo_service
from aac_backend.services.repository_integration_service import (
    record_github_webhook_delivery,
    parse_repository_mapping,
    publish_release_approval_for_baseline,
    publish_repository_check_run,
    repository_connector_data,
    repository_status_data,
    run_repository_scan,
    verify_github_signature,
)
from aac_backend.services.secret_service import decrypt_secret_payload, encrypt_secret_payload
from aac_backend.services.validation_service import ValidationContext, _rule_041, _rule_042


def test_connector_secret_payload_is_encrypted_and_round_trips() -> None:
    encrypted = encrypt_secret_payload({"webhook_secret": "super-secret"})

    assert "super-secret" not in encrypted
    assert decrypt_secret_payload(encrypted) == {"webhook_secret": "super-secret"}


def test_github_signature_verification_uses_sha256_hmac() -> None:
    body = b'{"zen":"keep it logically traceable"}'
    digest = hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()

    assert verify_github_signature("hook-secret", body, f"sha256={digest}") is True
    assert verify_github_signature("hook-secret", body, "sha256=bad") is False


def test_invalid_webhook_signature_is_recorded_before_json_parse() -> None:
    connector = _connector(webhook_secret_id=None)
    session = _FakeSession()

    delivery, scan_payload = asyncio.run(
        record_github_webhook_delivery(
            session,
            connector=connector,
            event_type="push",
            delivery_id="DELIVERY_1",
            signature_header="sha256=bad",
            body=b"{not json",
        )
    )

    assert delivery.signature_valid is False
    assert delivery.state == "rejected"
    assert scan_payload is None
    assert any(getattr(item, "event_type", "") == "repository_webhook.received" for item in session.added)


def test_valid_webhook_with_invalid_json_records_failed_delivery() -> None:
    encrypted = encrypt_secret_payload({"webhook_secret": "hook-secret"})
    secret = ConnectorSecret(
        connector_secret_id="CSEC_WEBHOOK",
        project_id="PROJ_1",
        secret_type="github_webhook_secret",
        encrypted_payload=encrypted,
        status="active",
    )
    connector = _connector(webhook_secret_id="CSEC_WEBHOOK")
    body = b"{not json"
    digest = hmac.new(b"hook-secret", body, hashlib.sha256).hexdigest()
    session = _FakeSession(get_by_class={ConnectorSecret: secret})

    with pytest.raises(ValueError):
        asyncio.run(
            record_github_webhook_delivery(
                session,
                connector=connector,
                event_type="push",
                delivery_id="DELIVERY_1",
                signature_header=f"sha256={digest}",
                body=body,
            )
        )

    delivery = next(item for item in session.added if isinstance(item, repo_service.RepositoryWebhookDelivery))
    assert delivery.state == "failed"
    assert delivery.diagnostics_json["error"] == "invalid_json"


def test_webhook_scan_payload_uses_exact_push_and_pull_request_sha() -> None:
    connector = _connector()

    push_payload = repo_service._scan_payload_from_webhook(
        connector,
        "push",
        {"ref": "refs/heads/release", "after": "push-sha"},
    )
    pull_request_payload = repo_service._scan_payload_from_webhook(
        connector,
        "pull_request",
        {"number": 42, "pull_request": {"head": {"sha": "pr-sha", "ref": "feature"}}},
    )
    unsupported_payload = repo_service._scan_payload_from_webhook(
        connector,
        "issues",
        {"action": "opened"},
    )

    assert push_payload == {"trigger": "github_push", "commit_sha": "push-sha", "branch": "release"}
    assert pull_request_payload == {
        "trigger": "github_pull_request",
        "commit_sha": "pr-sha",
        "branch": "feature",
        "pull_request_id": 42,
    }
    assert unsupported_payload is None


def test_repository_connector_data_redacts_access_token_secret() -> None:
    connector = RepositoryConnector(
        repository_connector_id="RCON_1",
        project_id="PROJ_1",
        provider="github",
        auth_mode="access_token",
        name="org/repo",
        owner="org",
        repository="repo",
        repository_url="https://github.com/org/repo",
        default_branch="main",
        app_id="",
        installation_id="",
        access_token_secret_id="CSEC_TOKEN",
        status="active",
    )

    payload = repository_connector_data(connector)

    assert payload["auth_mode"] == "access_token"
    assert payload["has_access_token"] is True
    assert "access_token_secret_id" not in payload
    assert "access_token" not in payload


def test_soft_delete_connector_records_audit_event() -> None:
    connector = _connector()
    session = _FakeSession(get_by_class={RepositoryConnector: connector})
    current = SimpleNamespace(user=SimpleNamespace(user_id="USER_1"))

    response = asyncio.run(
        delete_repository_connector(
            project_id="PROJ_1",
            connector_id="RCON_1",
            current=current,
            session=session,
        )
    )

    assert response.data["status"] == "deleted"
    assert connector.status == "deleted"
    assert session.committed is True
    assert any(getattr(item, "event_type", "") == "repository_connector.deleted" for item in session.added)


def test_repository_status_reads_branch_head_not_last_scanned_revision() -> None:
    connector = _connector(last_revision_id="RREV_LAST")
    revision = RepositoryRevision(
        repository_revision_id="RREV_LAST",
        repository_connector_id=connector.repository_connector_id,
        project_id=connector.project_id,
        commit_sha="old-scan-sha",
        branch="main",
    )
    session = _FakeSession(get_by_class={RepositoryRevision: revision})
    client = _StatusClient()

    payload = asyncio.run(repository_status_data(session, connector, client=client))

    assert client.commit_refs[0] == "main"
    assert payload["current_ref"] == "main"
    assert payload["latest_revision"]["commit_sha"] == "old-scan-sha"
    assert payload["current_commit"]["commit_sha"] == "branch-head-sha"


def test_access_token_approval_falls_back_to_commit_status() -> None:
    connector = RepositoryConnector(
        repository_connector_id="RCON_1",
        project_id="PROJ_1",
        provider="github",
        auth_mode="access_token",
        name="org/repo",
        owner="org",
        repository="repo",
        repository_url="https://github.com/org/repo",
        default_branch="main",
        app_id="",
        installation_id="",
        access_token_secret_id="CSEC_TOKEN",
        status="active",
    )
    client = _TokenFallbackClient()
    session = _FakeSession()

    check = asyncio.run(
        publish_repository_check_run(
            session,
            connector=connector,
            commit_sha="abc123",
            name="AAC Release Approval",
            status="completed",
            conclusion="success",
            summary="Approved in AAC",
            actor_user_id="USER_1",
            client=client,
        )
    )

    assert check.check_type == "github_commit_status"
    assert check.status == "completed"
    assert check.conclusion == "success"
    assert client.status_payload["context"] == "AAC Release Approval"
    assert client.status_payload["state"] == "success"


def test_release_approval_requires_repository_revision_snapshot() -> None:
    baseline = Baseline(
        baseline_id="BASE_1",
        project_id="PROJ_1",
        name="Baseline 1",
        state="approved",
        created_by="USER_1",
    )
    gate = ReleaseGateResult(
        release_gate_result_id="RGATE_1",
        project_id="PROJ_1",
        baseline_id="BASE_1",
        evaluation_number=1,
        triggered_by="USER_1",
        status="passed",
        result="pass",
    )
    session = _FakeSession(scalar_result=gate, scalars_result=[])

    with pytest.raises(ValueError, match="repository revision snapshot"):
        asyncio.run(
            publish_release_approval_for_baseline(
                session,
                baseline=baseline,
                actor_user_id="USER_1",
            )
        )


def test_repository_mapping_parser_accepts_mvp_shape() -> None:
    mapping = parse_repository_mapping(
        """
version: 1
implementation_items:
  - id: brake_monitor
    path: src/brake/monitor.py
    language: python
    satisfies: [SSR-001]
source_references:
  - path: src/brake/monitor.py
    lines: 10-80
    implements: [brake_monitor]
build_configurations:
  - id: ci-main
    workflow: github-actions
"""
    )

    assert mapping["implementation_items"][0]["id"] == "brake_monitor"
    assert mapping["source_references"][0]["path"] == "src/brake/monitor.py"
    assert mapping["build_configurations"][0]["id"] == "ci-main"


def test_repository_mapping_parser_rejects_entries_without_path() -> None:
    with pytest.raises(ValueError, match="require path"):
        parse_repository_mapping(
            """
version: 1
implementation_items:
  - id: missing_path
"""
        )


def test_repository_scan_failure_persists_failed_scan_diagnostics() -> None:
    connector = _connector()
    session = _FakeSession(get_by_class={RepositoryConnector: connector})

    with pytest.raises(RuntimeError, match="repository unavailable"):
        asyncio.run(
            run_repository_scan(
                session,
                project_id="PROJ_1",
                connector_id="RCON_1",
                actor_user_id="USER_1",
                client=_FailingScanClient(),
            )
        )

    scan_run = next(item for item in session.added if isinstance(item, RepositoryScanRun))
    assert scan_run.state == "failed"
    assert scan_run.diagnostics_json["message"] == "repository unavailable"
    assert any(getattr(item, "event_type", "") == "repository_scan.failed" for item in session.added)


def test_repository_scan_missing_path_fails_before_import() -> None:
    connector = _connector()
    session = _FakeSession(get_by_class={RepositoryConnector: connector})

    with pytest.raises(ValueError, match="missing paths"):
        asyncio.run(
            run_repository_scan(
                session,
                project_id="PROJ_1",
                connector_id="RCON_1",
                actor_user_id="USER_1",
                client=_MissingPathScanClient(),
            )
        )

    scan_run = next(item for item in session.added if isinstance(item, RepositoryScanRun))
    assert scan_run.state == "failed"
    assert "src/missing.py" in scan_run.diagnostics_json["message"]


def test_repository_scan_rejects_disabled_connector() -> None:
    connector = _connector(status="disabled")
    session = _FakeSession(get_by_class={RepositoryConnector: connector})

    with pytest.raises(ValueError, match="must be active"):
        asyncio.run(
            run_repository_scan(
                session,
                project_id="PROJ_1",
                connector_id="RCON_1",
                actor_user_id="USER_1",
                client=_FailingScanClient(),
            )
        )


def test_mapping_import_reports_unresolved_relationship_diagnostics(monkeypatch) -> None:
    connector = _connector()
    session = _FakeSession()
    captured_payloads = {}

    async def fake_upsert_artefact(*args, **kwargs):
        artefact = Artefact(
            artefact_id=f"ART_{len(captured_payloads) + 1}",
            project_id=kwargs["project_id"],
            artefact_type=kwargs["artefact_type"],
            title=kwargs["title"],
            source_kind="repository",
            source_tool="github",
            source_object_id=kwargs["source_object_id"],
            source_document=kwargs["source_document"],
            payload_json=kwargs["payload"],
        )
        captured_payloads[kwargs["source_object_id"]] = kwargs["payload"]
        return artefact

    async def fake_artefact_by_ref(*args, **kwargs):
        return None

    monkeypatch.setattr(repo_service, "_upsert_artefact", fake_upsert_artefact)
    monkeypatch.setattr(repo_service, "_artefact_by_ref", fake_artefact_by_ref)

    result = asyncio.run(
        repo_service._upsert_mapping_artefacts(
            session,
            connector=connector,
            commit_sha="abc123",
            branch="main",
            mapping_path=".aac/repo.yml",
            mapping={
                "implementation_items": [
                    {"id": "impl", "path": "src/module.py", "satisfies": ["SSR_MISSING"]}
                ],
                "source_references": [
                    {"id": "src", "path": "src/module.py", "implements": ["impl_missing"]}
                ],
                "build_configurations": [{"id": "build", "workflow": "github-actions"}],
            },
            actor_user_id="USER_1",
        )
    )

    assert result["artefact_count"] == 3
    assert result["relationship_count"] == 0
    assert len(result["diagnostics"]) == 2
    assert captured_payloads["build"]["repo_url"] == connector.repository_url
    assert captured_payloads["build"]["repo_path"] == ".aac/repo.yml"


def test_rule_041_requires_repo_identity_when_connector_is_active() -> None:
    connector = RepositoryConnector(
        repository_connector_id="RCON_1",
        project_id="PROJ_1",
        provider="github",
        name="org/repo",
        owner="org",
        repository="repo",
        repository_url="https://github.com/org/repo",
        default_branch="main",
        app_id="1",
        installation_id="2",
        status="active",
    )
    implementation = Artefact(
        artefact_id="ART_1",
        project_id="PROJ_1",
        artefact_type="ImplementationItem",
        title="Implementation",
        source_kind="repository",
        source_object_id="impl",
        source_document="repo:RCON_1",
        payload_json={
            "repo_path": "src/module.py",
            "language": "Python",
            "source_references": [{"reference_type": "source_file", "location": "src/module.py"}],
        },
    )
    context = ValidationContext(
        project_id="PROJ_1",
        mode="baseline",
        artefacts=[implementation],
        relationships=[],
        tailoring_decisions=[],
        open_suspects=[],
        validation_policy={},
        profile_payload={},
        repository_connectors=[connector],
    )

    issues = _rule_041(ValidationRun(validation_run_id="VRUN_1", project_id="PROJ_1"), context)

    assert len(issues) == 1
    assert "configured repository connector" in issues[0].message


def test_rule_042_accepts_repository_backed_build_configuration() -> None:
    connector = _connector()
    build_config = Artefact(
        artefact_id="ART_BUILD",
        project_id="PROJ_1",
        artefact_type="BuildConfiguration",
        title="Build",
        source_kind="repository",
        source_object_id="build",
        source_document="repo:RCON_1",
        payload_json={
            "repository_connector_id": "RCON_1",
            "source_revision": "abc123",
            "compiler_toolchain": "github-actions",
        },
    )
    context = ValidationContext(
        project_id="PROJ_1",
        mode="baseline",
        artefacts=[build_config],
        relationships=[],
        tailoring_decisions=[],
        open_suspects=[],
        validation_policy={},
        profile_payload={},
        repository_connectors=[connector],
    )

    issues = _rule_042(ValidationRun(validation_run_id="VRUN_1", project_id="PROJ_1"), context)

    assert issues == []


def _connector(**overrides) -> RepositoryConnector:
    values = {
        "repository_connector_id": "RCON_1",
        "project_id": "PROJ_1",
        "provider": "github",
        "auth_mode": "github_app",
        "name": "org/repo",
        "owner": "org",
        "repository": "repo",
        "repository_url": "https://github.com/org/repo",
        "default_branch": "main",
        "app_id": "1",
        "installation_id": "2",
        "status": "active",
    }
    values.update(overrides)
    return RepositoryConnector(**values)


class _FakeSession:
    def __init__(self, *, get_by_class=None, scalar_result=None, scalars_result=None):
        self.added = []
        self.get_by_class = get_by_class or {}
        self.scalar_result = scalar_result
        self.scalars_result = scalars_result or []
        self.committed = False

    def add(self, value):
        self.added.append(value)
        self.value = value

    def add_all(self, values):
        for value in values:
            self.add(value)

    async def flush(self) -> None:
        return None

    async def commit(self) -> None:
        self.committed = True

    async def get(self, model, identity):
        value = self.get_by_class.get(model)
        if isinstance(value, dict):
            return value.get(identity)
        return value

    async def scalar(self, statement):
        return self.scalar_result

    async def scalars(self, statement):
        return self.scalars_result


class _TokenFallbackClient:
    def __init__(self) -> None:
        self.status_payload = {}

    async def create_check_run(self, **kwargs):
        raise RuntimeError("check runs require github app auth")

    async def create_commit_status(self, **kwargs):
        self.status_payload = kwargs
        return {"id": 42}


class _StatusClient:
    def __init__(self) -> None:
        self.commit_refs = []

    async def get_repository(self, owner, repository):
        return {
            "full_name": f"{owner}/{repository}",
            "default_branch": "main",
            "private": False,
            "html_url": "https://github.com/org/repo",
        }

    async def get_commit(self, owner, repository, ref):
        self.commit_refs.append(ref)
        return {
            "sha": "branch-head-sha",
            "commit": {
                "message": "branch head",
                "author": {"name": "Developer", "date": "2026-04-19T08:00:00Z"},
            },
            "html_url": "https://github.com/org/repo/commit/branch-head-sha",
        }

    async def list_check_runs(self, owner, repository, ref):
        return []

    async def get_combined_status(self, owner, repository, ref):
        return {"state": "success", "total_count": 0, "statuses": []}


class _FailingScanClient:
    async def get_commit(self, owner, repository, ref):
        raise RuntimeError("repository unavailable")


class _MissingPathScanClient:
    async def get_commit(self, owner, repository, ref):
        return {
            "sha": "abc123",
            "commit": {
                "message": "update",
                "author": {"name": "Developer", "date": "2026-04-19T08:00:00Z"},
                "tree": {"sha": "tree-sha"},
            },
            "parents": [],
        }

    async def get_file_text(self, owner, repository, path, ref):
        return """
version: 1
implementation_items:
  - id: missing
    path: src/missing.py
"""

    async def get_tree_paths(self, owner, repository, commit_sha):
        return {"src/other.py"}
