import argparse
import asyncio
import json
import os
import sys
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request, urlopen

import aac_backend.models.all_models  # noqa: F401
from aac_backend.repositories.unit_of_work import unit_of_work
from aac_backend.schemas.auth import UserCreate
from aac_backend.services.user_service import create_user


async def _create_admin(args: argparse.Namespace) -> None:
    async with unit_of_work() as session:
        user = await create_user(
            session,
            UserCreate(
                username=args.username,
                display_name=args.display_name,
                email=args.email,
                password=args.password,
                roles=["admin"],
            ),
            actor_user_id=None,
        )
        print(f"created admin user {user.username} ({user.user_id})")


def _api_request(args: argparse.Namespace, method: str, path: str, body: dict | None = None) -> dict:
    base_url = args.base_url.rstrip("/")
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    token = getattr(args, "token", None) or os.getenv("AAC_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    request = Request(f"{base_url}{path}", data=data, headers=headers, method=method)
    try:
        with urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        message = exc.read().decode("utf-8")
        raise SystemExit(f"API request failed: HTTP {exc.code}: {message}") from exc


def _print_json(data: dict) -> None:
    print(json.dumps(data, indent=2, sort_keys=True, default=str))


def _resource_id(value: str) -> str:
    return quote(value, safe="")


def _json_payload(args: argparse.Namespace) -> dict:
    if getattr(args, "json", None):
        payload = json.loads(args.json)
    elif getattr(args, "file", None):
        with open(args.file, encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = {}
    if not isinstance(payload, dict):
        raise SystemExit("payload must be a JSON object")
    return payload


def _project_request(
    args: argparse.Namespace,
    method: str,
    suffix: str,
    body: dict | None = None,
) -> None:
    _print_json(
        _api_request(
            args,
            method,
            f"/api/v1/projects/{_resource_id(args.project_id)}{suffix}",
            body,
        )
    )


def _login(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            "/api/v1/auth/login",
            {"username": args.username, "password": args.password},
        )
    )


def _list_projects(args: argparse.Namespace) -> None:
    _print_json(_api_request(args, "GET", "/api/v1/projects"))


def _import_sphinx(args: argparse.Namespace) -> None:
    with open(args.file, encoding="utf-8") as handle:
        needs = json.load(handle)
    if isinstance(needs, dict):
        needs = needs.get("sphinx_needs") or needs.get("needs") or list(needs.values())
    body = {
        "source_root": args.source_root,
        "sphinx_needs": needs,
    }
    if args.version_update_mode:
        body["version_update_mode"] = args.version_update_mode
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/projects/{args.project_id}/imports/sphinx",
            body,
        )
    )


def _validation_run(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/projects/{args.project_id}/validation/run",
            {"type": "project", "mode": args.mode},
        )
    )


def _trace(args: argparse.Namespace) -> None:
    _print_json(_api_request(args, "GET", f"/api/v1/projects/{args.project_id}/trace/{args.artefact_id}"))


def _baseline_create(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/projects/{args.project_id}/baselines",
            {"name": args.name, "description": args.description},
        )
    )


def _impact(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/projects/{args.project_id}/impact",
            {"artefact_id": args.artefact_id},
        )
    )


def _report(args: argparse.Namespace) -> None:
    body = {"report_type": args.report_type, "format": "json"}
    if args.report_type == "baseline_comparison":
        if not args.left_baseline_id or not args.right_baseline_id:
            raise SystemExit(
                "baseline_comparison requires --left-baseline-id and --right-baseline-id"
            )
        if args.left_baseline_id == args.right_baseline_id:
            raise SystemExit("comparison baselines must be different")
        body["left_baseline_id"] = args.left_baseline_id
        body["right_baseline_id"] = args.right_baseline_id
    elif args.baseline_id:
        body["baseline_id"] = args.baseline_id
    _print_json(_api_request(args, "POST", f"/api/v1/projects/{args.project_id}/reports", body))


def _release_gate(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/projects/{args.project_id}/release-gate/run",
            {"baseline_id": args.baseline_id},
        )
    )


def _artefacts(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/artefacts")


def _artefact_get(args: argparse.Namespace) -> None:
    _project_request(args, "GET", f"/artefacts/{_resource_id(args.artefact_id)}")


def _artefact_create(args: argparse.Namespace) -> None:
    _project_request(args, "POST", "/artefacts", _json_payload(args))


def _artefact_update(args: argparse.Namespace) -> None:
    payload = _json_payload(args)
    payload["base_revision_id"] = args.base_revision_id
    _project_request(
        args,
        "PUT",
        f"/artefacts/{_resource_id(args.artefact_id)}",
        payload,
    )


def _artefact_delete(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "DELETE",
        f"/artefacts/{_resource_id(args.artefact_id)}",
        {"base_revision_id": args.base_revision_id},
    )


def _artefact_action(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "POST",
        f"/artefacts/{_resource_id(args.artefact_id)}/{args.action}",
        {"base_revision_id": args.base_revision_id},
    )


def _relationships(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/relationships")


def _relationship_create(args: argparse.Namespace) -> None:
    _project_request(args, "POST", "/relationships", _json_payload(args))


def _relationship_update(args: argparse.Namespace) -> None:
    payload = _json_payload(args)
    payload["base_revision_id"] = args.base_revision_id
    _project_request(
        args,
        "PUT",
        f"/relationships/{_resource_id(args.relationship_id)}",
        payload,
    )


def _relationship_delete(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "DELETE",
        f"/relationships/{_resource_id(args.relationship_id)}",
        {"base_revision_id": args.base_revision_id},
    )


def _imports(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/imports")


def _import_get(args: argparse.Namespace) -> None:
    _project_request(args, "GET", f"/imports/{_resource_id(args.import_id)}")


def _import_decisions(args: argparse.Namespace) -> None:
    payload = _json_payload(args)
    decisions = payload.get("decisions", payload)
    if not isinstance(decisions, list):
        raise SystemExit("import decisions payload must be a JSON list or {\"decisions\": [...]}")
    _project_request(
        args,
        "POST",
        f"/imports/{_resource_id(args.import_id)}/decisions",
        {"decisions": decisions},
    )


def _validation_issues(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/validation/issues")


def _validation_issue_action(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "POST",
        f"/validation/issues/{_resource_id(args.issue_id)}/{args.action}",
        _json_payload(args),
    )


def _suspects(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/suspect-states")


def _suspect_clear(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "POST",
        f"/suspect-states/{_resource_id(args.suspect_id)}/clear",
        {"rationale": args.rationale},
    )


def _baselines(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/baselines")


def _baseline_action(args: argparse.Namespace) -> None:
    _project_request(
        args,
        "POST",
        f"/baselines/{_resource_id(args.baseline_id)}/{args.action}",
        {},
    )


def _reports(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/reports")


def _report_get(args: argparse.Namespace) -> None:
    _project_request(args, "GET", f"/reports/{_resource_id(args.report_id)}")


def _jobs(args: argparse.Namespace) -> None:
    _project_request(args, "GET", "/jobs")


def _job_get(args: argparse.Namespace) -> None:
    _print_json(_api_request(args, "GET", f"/api/v1/jobs/{_resource_id(args.job_id)}"))


def _job_cancel(args: argparse.Namespace) -> None:
    _print_json(
        _api_request(
            args,
            "POST",
            f"/api/v1/jobs/{_resource_id(args.job_id)}/cancel",
            {},
        )
    )


def _add_api_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.getenv("AAC_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.getenv("AAC_TOKEN"))


def _add_project_options(parser: argparse.ArgumentParser) -> None:
    _add_api_options(parser)
    parser.add_argument("--project-id", required=True)


def _add_json_options(parser: argparse.ArgumentParser, *, required: bool = False) -> None:
    payload = parser.add_mutually_exclusive_group(required=required)
    payload.add_argument("--json")
    payload.add_argument("--file")


def main() -> None:
    parser = argparse.ArgumentParser(prog="aac")
    subcommands = parser.add_subparsers(dest="command", required=True)
    admin = subcommands.add_parser("create-admin")
    admin.add_argument("--username", required=True)
    admin.add_argument("--display-name", required=True)
    admin.add_argument("--email", required=True)
    admin.add_argument("--password", required=True)

    login = subcommands.add_parser("login")
    _add_api_options(login)
    login.add_argument("--username", required=True)
    login.add_argument("--password", required=True)

    projects = subcommands.add_parser("projects")
    _add_api_options(projects)

    import_sphinx = subcommands.add_parser("import-sphinx")
    _add_api_options(import_sphinx)
    import_sphinx.add_argument("--project-id", required=True)
    import_sphinx.add_argument("--file", required=True)
    import_sphinx.add_argument("--source-root", default="")
    import_sphinx.add_argument("--version-update-mode", choices=["automatic_new_version", "ask_user"], default=None)

    validation = subcommands.add_parser("validation-run")
    _add_api_options(validation)
    validation.add_argument("--project-id", required=True)
    validation.add_argument("--mode", choices=["baseline", "release_gate", "import"], default="baseline")

    trace = subcommands.add_parser("trace")
    _add_api_options(trace)
    trace.add_argument("--project-id", required=True)
    trace.add_argument("--artefact-id", required=True)

    baseline = subcommands.add_parser("baseline-create")
    _add_api_options(baseline)
    baseline.add_argument("--project-id", required=True)
    baseline.add_argument("--name", required=True)
    baseline.add_argument("--description", default="")

    impact = subcommands.add_parser("impact")
    _add_api_options(impact)
    impact.add_argument("--project-id", required=True)
    impact.add_argument("--artefact-id", required=True)

    report = subcommands.add_parser("report")
    _add_api_options(report)
    report.add_argument("--project-id", required=True)
    report.add_argument("--report-type", required=True)
    report.add_argument("--baseline-id", default=None)
    report.add_argument("--left-baseline-id", default=None)
    report.add_argument("--right-baseline-id", default=None)

    release_gate = subcommands.add_parser("release-gate")
    _add_api_options(release_gate)
    release_gate.add_argument("--project-id", required=True)
    release_gate.add_argument("--baseline-id", required=True)

    artefacts = subcommands.add_parser("artefacts")
    _add_project_options(artefacts)

    artefact_get = subcommands.add_parser("artefact-get")
    _add_project_options(artefact_get)
    artefact_get.add_argument("--artefact-id", required=True)

    artefact_create = subcommands.add_parser("artefact-create")
    _add_project_options(artefact_create)
    _add_json_options(artefact_create, required=True)

    artefact_update = subcommands.add_parser("artefact-update")
    _add_project_options(artefact_update)
    artefact_update.add_argument("--artefact-id", required=True)
    artefact_update.add_argument("--base-revision-id", required=True)
    _add_json_options(artefact_update, required=True)

    artefact_delete = subcommands.add_parser("artefact-delete")
    _add_project_options(artefact_delete)
    artefact_delete.add_argument("--artefact-id", required=True)
    artefact_delete.add_argument("--base-revision-id", required=True)

    artefact_action = subcommands.add_parser("artefact-action")
    _add_project_options(artefact_action)
    artefact_action.add_argument("--artefact-id", required=True)
    artefact_action.add_argument("--base-revision-id", required=True)
    artefact_action.add_argument(
        "--action",
        required=True,
        choices=["submit-for-review", "mark-reviewed", "reject", "approve", "release"],
    )

    relationships = subcommands.add_parser("relationships")
    _add_project_options(relationships)

    relationship_create = subcommands.add_parser("relationship-create")
    _add_project_options(relationship_create)
    _add_json_options(relationship_create, required=True)

    relationship_update = subcommands.add_parser("relationship-update")
    _add_project_options(relationship_update)
    relationship_update.add_argument("--relationship-id", required=True)
    relationship_update.add_argument("--base-revision-id", required=True)
    _add_json_options(relationship_update, required=True)

    relationship_delete = subcommands.add_parser("relationship-delete")
    _add_project_options(relationship_delete)
    relationship_delete.add_argument("--relationship-id", required=True)
    relationship_delete.add_argument("--base-revision-id", required=True)

    imports = subcommands.add_parser("imports")
    _add_project_options(imports)

    import_get = subcommands.add_parser("import-get")
    _add_project_options(import_get)
    import_get.add_argument("--import-id", required=True)

    import_decisions = subcommands.add_parser("import-decisions")
    _add_project_options(import_decisions)
    import_decisions.add_argument("--import-id", required=True)
    _add_json_options(import_decisions, required=True)

    validation_issues = subcommands.add_parser("validation-issues")
    _add_project_options(validation_issues)

    validation_issue_action = subcommands.add_parser("validation-issue-action")
    _add_project_options(validation_issue_action)
    validation_issue_action.add_argument("--issue-id", required=True)
    validation_issue_action.add_argument("--action", choices=["suppress", "reopen"], required=True)
    _add_json_options(validation_issue_action)

    suspects = subcommands.add_parser("suspects")
    _add_project_options(suspects)

    suspect_clear = subcommands.add_parser("suspect-clear")
    _add_project_options(suspect_clear)
    suspect_clear.add_argument("--suspect-id", required=True)
    suspect_clear.add_argument("--rationale", required=True)

    baselines = subcommands.add_parser("baselines")
    _add_project_options(baselines)

    baseline_action = subcommands.add_parser("baseline-action")
    _add_project_options(baseline_action)
    baseline_action.add_argument("--baseline-id", required=True)
    baseline_action.add_argument(
        "--action",
        choices=["approve", "release", "cancel", "obsolete"],
        required=True,
    )

    reports = subcommands.add_parser("reports")
    _add_project_options(reports)

    report_get = subcommands.add_parser("report-get")
    _add_project_options(report_get)
    report_get.add_argument("--report-id", required=True)

    jobs = subcommands.add_parser("jobs")
    _add_project_options(jobs)

    job_get = subcommands.add_parser("job-get")
    _add_api_options(job_get)
    job_get.add_argument("--job-id", required=True)

    job_cancel = subcommands.add_parser("job-cancel")
    _add_api_options(job_cancel)
    job_cancel.add_argument("--job-id", required=True)

    args = parser.parse_args()
    if args.command == "create-admin":
        asyncio.run(_create_admin(args))
        return
    commands = {
        "login": _login,
        "projects": _list_projects,
        "import-sphinx": _import_sphinx,
        "validation-run": _validation_run,
        "trace": _trace,
        "baseline-create": _baseline_create,
        "impact": _impact,
        "report": _report,
        "release-gate": _release_gate,
        "artefacts": _artefacts,
        "artefact-get": _artefact_get,
        "artefact-create": _artefact_create,
        "artefact-update": _artefact_update,
        "artefact-delete": _artefact_delete,
        "artefact-action": _artefact_action,
        "relationships": _relationships,
        "relationship-create": _relationship_create,
        "relationship-update": _relationship_update,
        "relationship-delete": _relationship_delete,
        "imports": _imports,
        "import-get": _import_get,
        "import-decisions": _import_decisions,
        "validation-issues": _validation_issues,
        "validation-issue-action": _validation_issue_action,
        "suspects": _suspects,
        "suspect-clear": _suspect_clear,
        "baselines": _baselines,
        "baseline-action": _baseline_action,
        "reports": _reports,
        "report-get": _report_get,
        "jobs": _jobs,
        "job-get": _job_get,
        "job-cancel": _job_cancel,
    }
    if args.command in commands:
        commands[args.command](args)
        return
    print(f"unknown command: {args.command}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
