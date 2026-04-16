import argparse
import asyncio
import json
import os
import sys
from urllib.error import HTTPError
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
    if args.baseline_id:
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


def _add_api_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--base-url", default=os.getenv("AAC_API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--token", default=os.getenv("AAC_TOKEN"))


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

    release_gate = subcommands.add_parser("release-gate")
    _add_api_options(release_gate)
    release_gate.add_argument("--project-id", required=True)
    release_gate.add_argument("--baseline-id", required=True)

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
    }
    if args.command in commands:
        commands[args.command](args)
        return
    print(f"unknown command: {args.command}", file=sys.stderr)
    raise SystemExit(2)


if __name__ == "__main__":
    main()
