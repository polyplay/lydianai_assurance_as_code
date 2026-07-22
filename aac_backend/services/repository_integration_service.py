from __future__ import annotations

import hashlib
import hmac
import json
import re
from datetime import UTC, datetime
from typing import Any

import httpx
import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import Baseline, ReleaseGateResult
from aac_backend.models.jobs import Job
from aac_backend.models.repository_integrations import (
    BaselineRepositoryRevision,
    ConnectorSecret,
    RepositoryCheckRun,
    RepositoryConnector,
    RepositoryRevision,
    RepositoryScanRun,
    RepositoryWebhookDelivery,
)
from aac_backend.schemas.domain import ArtefactCreate, ArtefactSource, ArtefactUpdate, RelationshipCreate
from aac_backend.services.artefact_service import create_artefact, create_relationship, fingerprint, update_artefact
from aac_backend.services.event_service import record_event
from aac_backend.services.github_client import GitHubClient
from aac_backend.services.secret_service import decrypt_secret_payload, encrypt_secret_payload

DEFAULT_MAPPING_FILE = ".aac/repo.yml"


def verify_github_signature(secret: str, body: bytes, signature_header: str | None) -> bool:
    if not secret or not signature_header or not signature_header.startswith("sha256="):
        return False
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature_header)


def parse_repository_mapping(text: str) -> dict[str, Any]:
    try:
        payload = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"repository mapping is not valid YAML: {exc}") from exc
    if not isinstance(payload, dict):
        raise ValueError("repository mapping root must be an object")
    if int(payload.get("version", 1)) != 1:
        raise ValueError("unsupported repository mapping version")
    return {
        "version": 1,
        "implementation_items": _list_of_objects(payload, "implementation_items"),
        "source_references": _list_of_objects(payload, "source_references"),
        "build_configurations": _list_of_objects(payload, "build_configurations"),
    }


async def create_repository_connector(
    session: AsyncSession,
    *,
    project_id: str,
    payload: dict[str, Any],
    actor_user_id: str,
) -> RepositoryConnector:
    if payload.get("provider", "github") != "github":
        raise ValueError("only provider 'github' is supported")
    auth_mode = payload.get("auth_mode") or "github_app"
    if auth_mode not in {"github_app", "access_token"}:
        raise ValueError("auth_mode must be github_app or access_token")

    app_id = ""
    installation_id = ""
    access_token_secret_id: str | None = None
    private_key_secret_id: str | None = None
    webhook_secret_id: str | None = None

    if auth_mode == "github_app":
        github_app = dict(payload.get("github_app") or {})
        private_key = github_app.get("private_key_pem")
        webhook_secret = github_app.get("webhook_secret")
        if not private_key or not webhook_secret:
            raise ValueError("github_app.private_key_pem and github_app.webhook_secret are required")
        if not github_app.get("app_id") or not github_app.get("installation_id"):
            raise ValueError("github_app.app_id and github_app.installation_id are required")
        app_id = str(github_app["app_id"])
        installation_id = str(github_app["installation_id"])
        private_key_secret = _secret(
            project_id,
            "github_private_key",
            {"private_key_pem": private_key},
            actor_user_id,
        )
        webhook_secret_row = _secret(
            project_id,
            "github_webhook_secret",
            {"webhook_secret": webhook_secret},
            actor_user_id,
        )
        session.add_all([private_key_secret, webhook_secret_row])
        await session.flush()
        private_key_secret_id = private_key_secret.connector_secret_id
        webhook_secret_id = webhook_secret_row.connector_secret_id
    else:
        access_token_config = dict(payload.get("access_token") or {})
        access_token = access_token_config.get("access_token")
        if not access_token:
            raise ValueError("access_token.access_token is required")
        token_secret = _secret(
            project_id,
            "github_access_token",
            {"access_token": access_token},
            actor_user_id,
        )
        secrets = [token_secret]
        webhook_secret_row = None
        if access_token_config.get("webhook_secret"):
            webhook_secret_row = _secret(
                project_id,
                "github_webhook_secret",
                {"webhook_secret": access_token_config["webhook_secret"]},
                actor_user_id,
            )
            secrets.append(webhook_secret_row)
        session.add_all(secrets)
        await session.flush()
        access_token_secret_id = token_secret.connector_secret_id
        webhook_secret_id = webhook_secret_row.connector_secret_id if webhook_secret_row else None

    owner = str(payload["owner"])
    repository = str(payload["repository"])
    connector = RepositoryConnector(
        project_id=project_id,
        provider="github",
        name=payload.get("name") or f"{owner}/{repository}",
        owner=owner,
        repository=repository,
        repository_url=payload.get("repository_url") or f"https://github.com/{owner}/{repository}",
        default_branch=payload.get("default_branch") or "main",
        auth_mode=auth_mode,
        app_id=app_id,
        installation_id=installation_id,
        access_token_secret_id=access_token_secret_id,
        private_key_secret_id=private_key_secret_id,
        webhook_secret_id=webhook_secret_id,
        scan_policy_json={
            "auto_scan_on_push": True,
            "auto_scan_on_pull_request": True,
            **dict(payload.get("scan_policy") or {}),
        },
        mapping_policy_json={
            "mapping_file_path": DEFAULT_MAPPING_FILE,
            **dict(payload.get("mapping_policy") or {}),
        },
        created_by=actor_user_id,
    )
    session.add(connector)
    await session.flush()
    await record_event(
        session,
        event_type="repository_connector.created",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload={"repository_connector_id": connector.repository_connector_id},
    )
    return connector


async def update_repository_connector(
    session: AsyncSession,
    *,
    connector: RepositoryConnector,
    payload: dict[str, Any],
    actor_user_id: str,
) -> RepositoryConnector:
    github_app = dict(payload.get("github_app") or {})
    access_token_config = dict(payload.get("access_token") or {})
    for field in ("name", "repository_url", "default_branch", "status"):
        if field in payload:
            setattr(connector, field, payload[field])
    if "auth_mode" in payload:
        auth_mode = payload["auth_mode"]
        if auth_mode not in {"github_app", "access_token"}:
            raise ValueError("auth_mode must be github_app or access_token")
        connector.auth_mode = auth_mode
    if "app_id" in github_app:
        connector.app_id = str(github_app["app_id"])
    if "installation_id" in github_app:
        connector.installation_id = str(github_app["installation_id"])
    if "scan_policy" in payload:
        connector.scan_policy_json = {**dict(connector.scan_policy_json or {}), **dict(payload["scan_policy"])}
    if "mapping_policy" in payload:
        connector.mapping_policy_json = {
            **dict(connector.mapping_policy_json or {}),
            **dict(payload["mapping_policy"]),
        }
    if github_app.get("private_key_pem"):
        secret = _secret(
            connector.project_id,
            "github_private_key",
            {"private_key_pem": github_app["private_key_pem"]},
            actor_user_id,
        )
        session.add(secret)
        await session.flush()
        connector.private_key_secret_id = secret.connector_secret_id
    if github_app.get("webhook_secret"):
        secret = _secret(
            connector.project_id,
            "github_webhook_secret",
            {"webhook_secret": github_app["webhook_secret"]},
            actor_user_id,
        )
        session.add(secret)
        await session.flush()
        connector.webhook_secret_id = secret.connector_secret_id
    if access_token_config.get("access_token"):
        secret = _secret(
            connector.project_id,
            "github_access_token",
            {"access_token": access_token_config["access_token"]},
            actor_user_id,
        )
        session.add(secret)
        await session.flush()
        connector.access_token_secret_id = secret.connector_secret_id
    if access_token_config.get("webhook_secret"):
        secret = _secret(
            connector.project_id,
            "github_webhook_secret",
            {"webhook_secret": access_token_config["webhook_secret"]},
            actor_user_id,
        )
        session.add(secret)
        await session.flush()
        connector.webhook_secret_id = secret.connector_secret_id
    if connector.auth_mode == "github_app" and (
        not connector.app_id or not connector.installation_id or not connector.private_key_secret_id
    ):
        raise ValueError("github app credentials are incomplete")
    if connector.auth_mode == "access_token" and not connector.access_token_secret_id:
        raise ValueError("github access token is not configured")
    await record_event(
        session,
        event_type="repository_connector.updated",
        project_id=connector.project_id,
        actor_user_id=actor_user_id,
        payload={"repository_connector_id": connector.repository_connector_id},
    )
    return connector


async def test_repository_connector(
    session: AsyncSession,
    connector: RepositoryConnector,
    client: Any | None = None,
) -> dict[str, Any]:
    client = client or await _github_client_for_connector(session, connector)
    repository = await client.get_repository(connector.owner, connector.repository)
    return {
        "connected": True,
        "provider": connector.provider,
        "owner": connector.owner,
        "repository": connector.repository,
        "default_branch": repository.get("default_branch") or connector.default_branch,
        "private": repository.get("private"),
    }


async def repository_status_data(
    session: AsyncSession,
    connector: RepositoryConnector,
    client: Any | None = None,
) -> dict[str, Any]:
    client = client or await _github_client_for_connector(session, connector)
    repository = await client.get_repository(connector.owner, connector.repository)
    ref = connector.default_branch
    latest_revision = None
    if connector.last_revision_id:
        latest_revision = await session.get(RepositoryRevision, connector.last_revision_id)
    status: dict[str, Any] = {
        "repository_connector": repository_connector_data(connector),
        "repository": {
            "full_name": repository.get("full_name") or f"{connector.owner}/{connector.repository}",
            "default_branch": repository.get("default_branch") or connector.default_branch,
            "private": repository.get("private"),
            "html_url": repository.get("html_url") or connector.repository_url,
        },
        "repository_state": "reachable",
        "latest_revision": repository_revision_data(latest_revision) if latest_revision else None,
        "current_ref": ref,
        "current_commit": None,
        "github_checks": [],
        "github_status": None,
        "diagnostics": [],
    }
    try:
        commit = await client.get_commit(connector.owner, connector.repository, ref)
    except httpx.HTTPStatusError as exc:
        message = _github_error_message(exc)
        state = "empty" if exc.response.status_code in {404, 409} and "empty" in message.lower() else "unavailable"
        status["repository_state"] = state
        status["diagnostics"].append({"severity": "warning", "message": message})
        return status
    commit_sha = commit["sha"]
    commit_payload = commit.get("commit") or {}
    status["current_commit"] = {
        "commit_sha": commit_sha,
        "message": commit_payload.get("message"),
        "author": (commit_payload.get("author") or {}).get("name"),
        "timestamp": (commit_payload.get("author") or {}).get("date"),
        "html_url": commit.get("html_url"),
    }
    try:
        checks = await client.list_check_runs(connector.owner, connector.repository, commit_sha)
        status["github_checks"] = [_github_check_summary(check) for check in checks]
    except httpx.HTTPStatusError as exc:
        status["diagnostics"].append({"severity": "info", "message": _github_error_message(exc)})
    try:
        combined_status = await client.get_combined_status(connector.owner, connector.repository, commit_sha)
        status["github_status"] = {
            "state": combined_status.get("state"),
            "total_count": combined_status.get("total_count"),
            "statuses": [
                {
                    "context": item.get("context"),
                    "state": item.get("state"),
                    "description": item.get("description"),
                    "target_url": item.get("target_url"),
                }
                for item in combined_status.get("statuses", [])
            ],
        }
    except httpx.HTTPStatusError as exc:
        status["diagnostics"].append({"severity": "info", "message": _github_error_message(exc)})
    return status


async def record_github_webhook_delivery(
    session: AsyncSession,
    *,
    connector: RepositoryConnector,
    event_type: str,
    delivery_id: str,
    signature_header: str | None,
    body: bytes,
) -> tuple[RepositoryWebhookDelivery, dict[str, Any] | None]:
    secret_payload = await _secret_payload(session, connector.webhook_secret_id) if connector.webhook_secret_id else {}
    signature_valid = verify_github_signature(
        str(secret_payload.get("webhook_secret") or ""),
        body,
        signature_header,
    )
    payload_hash = hashlib.sha256(body).hexdigest()
    delivery = RepositoryWebhookDelivery(
        repository_connector_id=connector.repository_connector_id,
        project_id=connector.project_id,
        delivery_id=delivery_id or payload_hash,
        event_type=event_type,
        action=None,
        signature_valid=signature_valid,
        state="accepted" if signature_valid else "rejected",
        payload_hash=payload_hash,
        received_at=datetime.now(UTC),
        diagnostics_json={},
    )
    session.add(delivery)
    await session.flush()
    await record_event(
        session,
        event_type="repository_webhook.received",
        project_id=connector.project_id,
        actor_user_id=None,
        payload={
            "repository_webhook_delivery_id": delivery.repository_webhook_delivery_id,
            "repository_connector_id": connector.repository_connector_id,
            "delivery_id": delivery.delivery_id,
            "event_type": event_type,
            "signature_valid": signature_valid,
            "payload_hash": payload_hash,
        },
    )
    if not signature_valid:
        return delivery, None

    try:
        payload = json.loads(body.decode("utf-8") or "{}") if body else {}
    except json.JSONDecodeError as exc:
        delivery.state = "failed"
        delivery.processed_at = datetime.now(UTC)
        delivery.diagnostics_json = {
            "error": "invalid_json",
            "message": str(exc),
        }
        raise
    delivery.action = payload.get("action")
    scan_payload = _scan_payload_from_webhook(connector, event_type, payload)
    if scan_payload is None:
        delivery.state = "ignored"
        delivery.processed_at = datetime.now(UTC)
    return delivery, scan_payload


async def run_repository_scan(
    session: AsyncSession,
    *,
    project_id: str,
    connector_id: str,
    actor_user_id: str | None,
    payload: dict[str, Any] | None = None,
    job: Job | None = None,
    client: Any | None = None,
) -> RepositoryScanRun:
    payload = payload or {}
    connector = await session.get(RepositoryConnector, connector_id)
    if not connector or connector.project_id != project_id or connector.status == "deleted":
        raise ValueError("repository connector not found")
    if connector.status != "active":
        raise ValueError("repository connector must be active to scan")

    scan_run = RepositoryScanRun(
        repository_connector_id=connector.repository_connector_id,
        project_id=project_id,
        job_id=job.job_id if job else None,
        trigger=payload.get("trigger", "manual"),
        state="running",
        requested_by=actor_user_id,
        branch=payload.get("branch") or connector.default_branch,
        pull_request_id=str(payload["pull_request_id"]) if payload.get("pull_request_id") else None,
        started_at=datetime.now(UTC),
    )
    session.add(scan_run)
    await session.flush()

    try:
        client = client or await _github_client_for_connector(session, connector)
        ref = payload.get("commit_sha") or scan_run.branch or connector.default_branch
        commit = await client.get_commit(connector.owner, connector.repository, ref)
        commit_sha = commit["sha"]
        scan_run.commit_sha = commit_sha
        mapping_path = (connector.mapping_policy_json or {}).get("mapping_file_path") or DEFAULT_MAPPING_FILE
        mapping_text = await client.get_file_text(connector.owner, connector.repository, mapping_path, commit_sha)
        mapping = parse_repository_mapping(mapping_text)
        tree_paths = await _tree_paths(client, connector, commit_sha)
        missing_paths = _missing_mapping_paths(mapping, tree_paths) if tree_paths else []
        if missing_paths:
            raise ValueError(f"repository mapping references missing paths: {', '.join(missing_paths)}")

        revision = await _upsert_repository_revision(
            session,
            connector=connector,
            scan_run=scan_run,
            commit=commit,
            mapping_text=mapping_text,
        )
        imported = await _upsert_mapping_artefacts(
            session,
            connector=connector,
            commit_sha=commit_sha,
            branch=scan_run.branch,
            mapping_path=mapping_path,
            mapping=mapping,
            actor_user_id=actor_user_id,
        )
    except Exception as exc:
        scan_run.state = "failed"
        scan_run.completed_at = datetime.now(UTC)
        scan_run.diagnostics_json = {
            "error": type(exc).__name__,
            "message": str(exc),
        }
        await record_event(
            session,
            event_type="repository_scan.failed",
            project_id=project_id,
            actor_user_id=actor_user_id,
            payload={
                "repository_scan_run_id": scan_run.repository_scan_run_id,
                "repository_connector_id": connector.repository_connector_id,
                "diagnostics": scan_run.diagnostics_json,
            },
        )
        await session.flush()
        raise

    scan_run.state = "completed"
    scan_run.completed_at = datetime.now(UTC)
    scan_run.summary_json = {
        "repository_revision_id": revision.repository_revision_id,
        "commit_sha": commit_sha,
        "mapping_file_path": mapping_path,
        **imported,
    }
    scan_run.diagnostics_json = {"diagnostics": imported.get("diagnostics", [])}
    connector.last_scan_run_id = scan_run.repository_scan_run_id
    connector.last_revision_id = revision.repository_revision_id
    await record_event(
        session,
        event_type="repository_scan.completed",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=scan_run.summary_json,
    )
    return scan_run


async def publish_repository_check_run(
    session: AsyncSession,
    *,
    connector: RepositoryConnector,
    commit_sha: str,
    name: str,
    status: str,
    conclusion: str | None,
    summary: str,
    actor_user_id: str | None,
    validation_run_id: str | None = None,
    release_gate_result_id: str | None = None,
    baseline_id: str | None = None,
    details_url: str | None = None,
    client: Any | None = None,
) -> RepositoryCheckRun:
    check = RepositoryCheckRun(
        repository_connector_id=connector.repository_connector_id,
        project_id=connector.project_id,
        validation_run_id=validation_run_id,
        release_gate_result_id=release_gate_result_id,
        baseline_id=baseline_id,
        commit_sha=commit_sha,
        status=status,
        conclusion=conclusion,
        details_url=details_url,
        summary=summary,
        requested_by=actor_user_id,
    )
    session.add(check)
    await session.flush()
    client = client or await _github_client_for_connector(session, connector)
    try:
        result = await client.create_check_run(
            owner=connector.owner,
            repository=connector.repository,
            name=name,
            commit_sha=commit_sha,
            status=status,
            conclusion=conclusion,
            summary=summary,
            details_url=details_url,
        )
    except Exception as exc:
        if connector.auth_mode != "access_token":
            check.status = "failed"
            check.error_json = {"error": type(exc).__name__, "message": str(exc)}
            raise
        status_result = await client.create_commit_status(
            owner=connector.owner,
            repository=connector.repository,
            commit_sha=commit_sha,
            state="success" if conclusion == "success" else "failure",
            context=name,
            description=summary,
            target_url=details_url,
        )
        check.check_type = "github_commit_status"
        check.github_check_run_id = str(status_result.get("id") or "")
        check.status = "completed"
        check.conclusion = conclusion
        return check
    check.github_check_run_id = str(result.get("id") or "")
    check.check_type = "github_check_run"
    check.status = result.get("status") or status
    check.conclusion = result.get("conclusion") or conclusion
    return check


async def publish_release_approval_for_baseline(
    session: AsyncSession,
    *,
    baseline: Baseline,
    actor_user_id: str,
    details_url: str | None = None,
) -> list[RepositoryCheckRun]:
    if baseline.state != "released":
        raise ValueError("repository approval requires a released baseline")
    result = await session.scalar(
        select(ReleaseGateResult)
        .where(
            ReleaseGateResult.project_id == baseline.project_id,
            ReleaseGateResult.baseline_id == baseline.baseline_id,
        )
        .order_by(ReleaseGateResult.evaluation_number.desc())
        .limit(1)
    )
    if not result or result.status != "passed" or result.result != "pass":
        raise ValueError("release approval requires a passed release gate result")
    revisions = list(
        await session.scalars(
            select(BaselineRepositoryRevision).where(
                BaselineRepositoryRevision.baseline_id == baseline.baseline_id
            )
        )
    )
    if not revisions:
        raise ValueError("release approval requires a baseline repository revision snapshot")
    checks: list[RepositoryCheckRun] = []
    for revision in revisions:
        connector = await session.get(RepositoryConnector, revision.repository_connector_id)
        if not connector or connector.status != "active":
            continue
        check = await publish_repository_check_run(
            session,
            connector=connector,
            commit_sha=revision.commit_sha,
            name="AAC Release Approval",
            status="completed",
            conclusion="success",
            summary=(
                f"Baseline {baseline.name} ({baseline.baseline_id}) passed the release gate "
                f"and was approved in Assurance-as-Code."
            ),
            actor_user_id=actor_user_id,
            release_gate_result_id=result.release_gate_result_id,
            baseline_id=baseline.baseline_id,
            details_url=details_url,
        )
        checks.append(check)
    await record_event(
        session,
        event_type="repository_approval.published",
        project_id=baseline.project_id,
        actor_user_id=actor_user_id,
        payload={
            "baseline_id": baseline.baseline_id,
            "release_gate_result_id": result.release_gate_result_id,
            "repository_check_run_ids": [check.repository_check_run_id for check in checks],
        },
    )
    return checks


def repository_connector_data(connector: RepositoryConnector) -> dict[str, Any]:
    return {
        "repository_connector_id": connector.repository_connector_id,
        "project_id": connector.project_id,
        "provider": connector.provider,
        "auth_mode": connector.auth_mode,
        "name": connector.name,
        "owner": connector.owner,
        "repository": connector.repository,
        "repository_url": connector.repository_url,
        "default_branch": connector.default_branch,
        "app_id": connector.app_id,
        "installation_id": connector.installation_id,
        "has_access_token": bool(connector.access_token_secret_id),
        "has_private_key": bool(connector.private_key_secret_id),
        "has_webhook_secret": bool(connector.webhook_secret_id),
        "scan_policy": connector.scan_policy_json,
        "mapping_policy": connector.mapping_policy_json,
        "status": connector.status,
        "last_scan_run_id": connector.last_scan_run_id,
        "last_revision_id": connector.last_revision_id,
    }


def repository_revision_data(revision: RepositoryRevision | None) -> dict[str, Any] | None:
    if revision is None:
        return None
    return {
        "repository_revision_id": revision.repository_revision_id,
        "repository_connector_id": revision.repository_connector_id,
        "project_id": revision.project_id,
        "scan_run_id": revision.scan_run_id,
        "commit_sha": revision.commit_sha,
        "branch": revision.branch,
        "tag": revision.tag,
        "commit_timestamp": revision.commit_timestamp.isoformat() if revision.commit_timestamp else None,
        "author_name": revision.author_name,
        "author_email": revision.author_email,
        "message": revision.message,
        "tree_sha": revision.tree_sha,
        "mapping_fingerprint": revision.mapping_fingerprint,
        "status": revision.status,
        "metadata": revision.metadata_json,
    }


def repository_check_run_data(check: RepositoryCheckRun) -> dict[str, Any]:
    return {
        "repository_check_run_id": check.repository_check_run_id,
        "repository_connector_id": check.repository_connector_id,
        "project_id": check.project_id,
        "validation_run_id": check.validation_run_id,
        "release_gate_result_id": check.release_gate_result_id,
        "baseline_id": check.baseline_id,
        "commit_sha": check.commit_sha,
        "github_check_run_id": check.github_check_run_id,
        "check_type": check.check_type,
        "status": check.status,
        "conclusion": check.conclusion,
        "details_url": check.details_url,
        "summary": check.summary,
        "requested_by": check.requested_by,
        "error": check.error_json,
    }


async def repository_approval_history(
    session: AsyncSession,
    *,
    project_id: str,
    baseline_id: str,
) -> list[RepositoryCheckRun]:
    return list(
        await session.scalars(
            select(RepositoryCheckRun)
            .where(
                RepositoryCheckRun.project_id == project_id,
                RepositoryCheckRun.baseline_id == baseline_id,
            )
            .order_by(RepositoryCheckRun.created_at.desc())
        )
    )


def repository_scan_run_data(scan_run: RepositoryScanRun) -> dict[str, Any]:
    return {
        "repository_scan_run_id": scan_run.repository_scan_run_id,
        "repository_connector_id": scan_run.repository_connector_id,
        "project_id": scan_run.project_id,
        "job_id": scan_run.job_id,
        "trigger": scan_run.trigger,
        "state": scan_run.state,
        "commit_sha": scan_run.commit_sha,
        "branch": scan_run.branch,
        "pull_request_id": scan_run.pull_request_id,
        "summary": scan_run.summary_json,
        "diagnostics": scan_run.diagnostics_json,
    }


async def _github_client_for_connector(session: AsyncSession, connector: RepositoryConnector) -> GitHubClient:
    if connector.auth_mode == "access_token":
        secret_payload = await _secret_payload(session, connector.access_token_secret_id)
        return GitHubClient(access_token=str(secret_payload["access_token"]))
    secret_payload = await _secret_payload(session, connector.private_key_secret_id)
    return GitHubClient(
        app_id=connector.app_id,
        installation_id=connector.installation_id,
        private_key_pem=str(secret_payload["private_key_pem"]),
    )


async def _secret_payload(session: AsyncSession, secret_id: str | None) -> dict[str, Any]:
    if not secret_id:
        raise ValueError("connector secret is not configured")
    secret = await session.get(ConnectorSecret, secret_id)
    if not secret or secret.status != "active":
        raise ValueError("connector secret is not active")
    secret.last_used_at = datetime.now(UTC)
    return decrypt_secret_payload(secret.encrypted_payload)


def _secret(project_id: str, secret_type: str, payload: dict[str, Any], actor_user_id: str) -> ConnectorSecret:
    return ConnectorSecret(
        project_id=project_id,
        secret_type=secret_type,
        encrypted_payload=encrypt_secret_payload(payload),
        created_by=actor_user_id,
        last_rotated_at=datetime.now(UTC),
    )


def _scan_payload_from_webhook(
    connector: RepositoryConnector,
    event_type: str,
    payload: dict[str, Any],
) -> dict[str, Any] | None:
    policy = connector.scan_policy_json or {}
    if event_type == "push" and policy.get("auto_scan_on_push", True):
        ref = str(payload.get("ref") or "")
        branch = ref.removeprefix("refs/heads/") if ref.startswith("refs/heads/") else connector.default_branch
        return {"trigger": "github_push", "commit_sha": payload.get("after"), "branch": branch}
    if event_type == "pull_request" and policy.get("auto_scan_on_pull_request", True):
        pull_request = payload.get("pull_request") or {}
        head = pull_request.get("head") or {}
        return {
            "trigger": "github_pull_request",
            "commit_sha": head.get("sha"),
            "branch": head.get("ref") or connector.default_branch,
            "pull_request_id": pull_request.get("number") or payload.get("number"),
        }
    return None


async def _upsert_repository_revision(
    session: AsyncSession,
    *,
    connector: RepositoryConnector,
    scan_run: RepositoryScanRun,
    commit: dict[str, Any],
    mapping_text: str,
) -> RepositoryRevision:
    commit_payload = commit.get("commit") or {}
    author = commit_payload.get("author") or {}
    revision = await session.scalar(
        select(RepositoryRevision).where(
            RepositoryRevision.repository_connector_id == connector.repository_connector_id,
            RepositoryRevision.commit_sha == commit["sha"],
        )
    )
    if revision is None:
        revision = RepositoryRevision(
            repository_connector_id=connector.repository_connector_id,
            project_id=connector.project_id,
            commit_sha=commit["sha"],
        )
        session.add(revision)
    revision.scan_run_id = scan_run.repository_scan_run_id
    revision.branch = scan_run.branch
    revision.commit_timestamp = _parse_datetime(author.get("date"))
    revision.author_name = author.get("name")
    revision.author_email = author.get("email")
    revision.message = commit_payload.get("message") or ""
    revision.tree_sha = (commit_payload.get("tree") or {}).get("sha")
    revision.mapping_fingerprint = hashlib.sha256(mapping_text.encode("utf-8")).hexdigest()
    revision.metadata_json = {
        "html_url": commit.get("html_url"),
        "parents": [parent.get("sha") for parent in commit.get("parents", []) if parent.get("sha")],
    }
    await session.flush()
    return revision


async def _upsert_mapping_artefacts(
    session: AsyncSession,
    *,
    connector: RepositoryConnector,
    commit_sha: str,
    branch: str | None,
    mapping_path: str,
    mapping: dict[str, Any],
    actor_user_id: str | None,
) -> dict[str, Any]:
    source_document = f"repo:{connector.repository_connector_id}"
    imported_ids: dict[str, Artefact] = {}
    artefact_count = 0
    relationship_count = 0
    diagnostics: list[dict[str, Any]] = []

    for item in mapping["implementation_items"]:
        object_id = str(item.get("id") or _object_id("IMPL", item["path"]))
        payload = {
            "repository_connector_id": connector.repository_connector_id,
            "repo_url": connector.repository_url,
            "repo_path": item["path"],
            "commit_ref": commit_sha,
            "commit_sha": commit_sha,
            "branch": branch,
            "language": item.get("language") or _language_from_path(item["path"]),
            "file_type": item.get("file_type") or "source",
            "satisfies_requirements": item.get("satisfies", []),
            "source_references": [
                {
                    "reference_type": "source_file",
                    "location": item["path"],
                    "commit_sha": commit_sha,
                }
            ],
        }
        artefact = await _upsert_artefact(
            session,
            project_id=connector.project_id,
            artefact_type="ImplementationItem",
            title=item.get("title") or object_id,
            source_document=source_document,
            source_object_id=object_id,
            payload=payload,
            actor_user_id=actor_user_id,
        )
        imported_ids[object_id] = artefact
        artefact_count += 1

    for ref in mapping["source_references"]:
        object_id = str(ref.get("id") or _object_id("SRC", f"{ref['path']}:{ref.get('lines', '')}"))
        payload = {
            "repository_connector_id": connector.repository_connector_id,
            "repo_url": connector.repository_url,
            "repo_path": ref["path"],
            "commit_ref": commit_sha,
            "commit_sha": commit_sha,
            "branch": branch,
            "line_ref": ref.get("lines") or ref.get("line_range"),
            "line_range": ref.get("lines") or ref.get("line_range"),
            "language": ref.get("language") or _language_from_path(ref["path"]),
            "linked_implementation_items": ref.get("implements", []),
        }
        artefact = await _upsert_artefact(
            session,
            project_id=connector.project_id,
            artefact_type="SourceCodeReference",
            title=ref.get("title") or object_id,
            source_document=source_document,
            source_object_id=object_id,
            payload=payload,
            actor_user_id=actor_user_id,
        )
        imported_ids[object_id] = artefact
        artefact_count += 1

    for build in mapping["build_configurations"]:
        object_id = str(build.get("id") or _object_id("BUILD", build.get("workflow") or build.get("build_ref") or "build"))
        repo_path = build.get("build_ref") or mapping_path
        payload = {
            "repository_connector_id": connector.repository_connector_id,
            "repo_url": connector.repository_url,
            "repo_path": repo_path,
            "build_id": object_id,
            "source_revision": commit_sha,
            "commit_sha": commit_sha,
            "branch": branch,
            "workflow": build.get("workflow"),
            "build_ref": build.get("build_ref"),
            "compiler_toolchain": build.get("compiler_toolchain") or build.get("workflow") or "github-actions",
            "build_options": build.get("build_options", {}),
            "dependencies": build.get("dependencies", []),
            "artifact_refs": build.get("artifact_refs", []),
        }
        artefact = await _upsert_artefact(
            session,
            project_id=connector.project_id,
            artefact_type="BuildConfiguration",
            title=build.get("title") or object_id,
            source_document=source_document,
            source_object_id=object_id,
            payload=payload,
            actor_user_id=actor_user_id,
        )
        imported_ids[object_id] = artefact
        artefact_count += 1

    for item in mapping["implementation_items"]:
        source = imported_ids.get(str(item.get("id") or _object_id("IMPL", item["path"])))
        if not source:
            continue
        for target_ref in item.get("satisfies", []):
            target = await _artefact_by_ref(session, connector.project_id, str(target_ref))
            if target and await _ensure_relationship(session, source, target, "implements"):
                relationship_count += 1
            if not target:
                diagnostics.append(
                    {
                        "severity": "warning",
                        "code": "unresolved_mapping_reference",
                        "source_object_id": source.source_object_id,
                        "target_ref": str(target_ref),
                        "relationship_type": "implements",
                        "message": f"Requirement reference {target_ref} was not found; relationship skipped",
                    }
                )

    for ref in mapping["source_references"]:
        source = imported_ids.get(str(ref.get("id") or _object_id("SRC", f"{ref['path']}:{ref.get('lines', '')}")))
        if not source:
            continue
        for target_ref in ref.get("implements", []):
            target = imported_ids.get(str(target_ref)) or await _artefact_by_ref(
                session,
                connector.project_id,
                str(target_ref),
            )
            if target and await _ensure_relationship(session, source, target, "references"):
                relationship_count += 1
            if not target:
                diagnostics.append(
                    {
                        "severity": "warning",
                        "code": "unresolved_mapping_reference",
                        "source_object_id": source.source_object_id,
                        "target_ref": str(target_ref),
                        "relationship_type": "references",
                        "message": f"Implementation reference {target_ref} was not found; relationship skipped",
                    }
                )

    return {
        "artefact_count": artefact_count,
        "relationship_count": relationship_count,
        "diagnostics": diagnostics,
    }


async def _upsert_artefact(
    session: AsyncSession,
    *,
    project_id: str,
    artefact_type: str,
    title: str,
    source_document: str,
    source_object_id: str,
    payload: dict[str, Any],
    actor_user_id: str | None,
) -> Artefact:
    existing = await session.scalar(
        select(Artefact).where(
            Artefact.project_id == project_id,
            Artefact.source_document == source_document,
            Artefact.source_object_id == source_object_id,
            Artefact.deleted_at.is_(None),
        )
    )
    if existing is None:
        return await create_artefact(
            session,
            project_id,
            ArtefactCreate(
                artefact_type=artefact_type,
                title=title,
                source=ArtefactSource(
                    source_kind="repository",
                    source_tool="github",
                    source_object_id=source_object_id,
                    source_document=source_document,
                    external_uri=payload.get("repo_url"),
                ),
                payload=payload,
            ),
            actor_user_id,
        )
    if existing.current_fingerprint == fingerprint(payload):
        return existing
    return await update_artefact(
        session,
        existing,
        ArtefactUpdate(
            title=title,
            payload=payload,
            base_revision_id=existing.current_revision_id,
            change_reason="repository scan update",
        ),
        actor_user_id,
    )


async def _ensure_relationship(
    session: AsyncSession,
    source: Artefact,
    target: Artefact,
    relationship_type: str,
) -> bool:
    existing = await session.scalar(
        select(Relationship).where(
            Relationship.project_id == source.project_id,
            Relationship.source_artefact_id == source.artefact_id,
            Relationship.target_artefact_id == target.artefact_id,
            Relationship.relationship_type == relationship_type,
            Relationship.deleted_at.is_(None),
        )
    )
    if existing:
        return False
    await create_relationship(
        session,
        source.project_id,
        RelationshipCreate(
            relationship_type=relationship_type,
            source_artefact_id=source.artefact_id,
            target_artefact_id=target.artefact_id,
            payload={"created_from": "repository_scan"},
        ),
        source.owner_user_id,
    )
    return True


async def _artefact_by_ref(session: AsyncSession, project_id: str, ref: str) -> Artefact | None:
    return await session.scalar(
        select(Artefact).where(
            Artefact.project_id == project_id,
            Artefact.deleted_at.is_(None),
            (Artefact.artefact_id == ref) | (Artefact.source_object_id == ref),
        )
    )


async def _tree_paths(client: Any, connector: RepositoryConnector, commit_sha: str) -> set[str]:
    try:
        return await client.get_tree_paths(connector.owner, connector.repository, commit_sha)
    except AttributeError:
        return set()


def _missing_mapping_paths(mapping: dict[str, Any], tree_paths: set[str]) -> list[str]:
    expected = {
        item["path"]
        for item in mapping["implementation_items"] + mapping["source_references"]
        if item.get("path")
    }
    return sorted(expected - tree_paths)


def _github_check_summary(check: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": check.get("id"),
        "name": check.get("name"),
        "status": check.get("status"),
        "conclusion": check.get("conclusion"),
        "started_at": check.get("started_at"),
        "completed_at": check.get("completed_at"),
        "html_url": check.get("html_url"),
    }


def _github_error_message(exc: httpx.HTTPStatusError) -> str:
    try:
        payload = exc.response.json()
        if isinstance(payload, dict) and payload.get("message"):
            return str(payload["message"])
    except ValueError:
        pass
    return str(exc)


def _list_of_objects(payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
    value = payload.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"{key} must be a list of objects")
    for item in value:
        if key in {"implementation_items", "source_references"} and not item.get("path"):
            raise ValueError(f"{key} entries require path")
    return value


def _object_id(prefix: str, value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", value).strip("_").upper()
    return f"{prefix}_{cleaned[:48] or hashlib.sha1(value.encode('utf-8')).hexdigest()[:12]}"


def _language_from_path(path: str) -> str:
    suffix = path.rsplit(".", 1)[-1].lower() if "." in path else ""
    return {
        "c": "C",
        "cc": "C++",
        "cpp": "C++",
        "h": "C/C++",
        "hpp": "C++",
        "py": "Python",
        "rs": "Rust",
        "java": "Java",
        "js": "JavaScript",
        "ts": "TypeScript",
    }.get(suffix, "unknown")


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
