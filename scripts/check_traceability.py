#!/usr/bin/env python3
"""Build and validate the complete requirements and acceptance status inventory."""

from __future__ import annotations

import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import sys

import yaml


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
TRACE_FILE = ROOT / "verification" / "requirements_traceability.yaml"
REQUIREMENT_PATTERN = re.compile(r"\bAAC-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
ACCEPTANCE_PATTERN = re.compile(r"\b(?:ACC|REPO-ACC)-[A-Z0-9]+(?:-[A-Z0-9]+)*\b")
ARCHITECTURE_PATTERN = re.compile(r"\bF-[A-Z0-9]+(?:-[A-Z0-9]+)+\b")
VALID_STATUSES = {"missing", "implemented", "verified", "waived"}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        type=Path,
        default=ROOT / "verification" / "generated" / "traceability-status.json",
    )
    args = parser.parse_args()

    trace = yaml.safe_load(TRACE_FILE.read_text(encoding="utf-8")) or {}
    entries = trace.get("requirements", {})
    requirements = _discover(REQUIREMENT_PATTERN, DOCS.glob("*.md"))
    acceptance = _discover(
        ACCEPTANCE_PATTERN,
        [
            DOCS / "mvp_acceptance_criteria.md",
            DOCS / "repository_integration_contract.md",
        ],
    )
    architecture_ids = _discover(
        ARCHITECTURE_PATTERN,
        [DOCS / "software_architecture.md"],
    )

    errors: list[str] = []
    acceptance_evidence: dict[str, set[str]] = defaultdict(set)
    requirement_rows = []
    for requirement_id in sorted(requirements):
        entry = entries.get(requirement_id)
        status = "missing"
        if entry is not None:
            status = _entry_status(
                requirement_id,
                entry,
                requirements,
                acceptance,
                architecture_ids,
                acceptance_evidence,
                errors,
            )
        requirement_rows.append(
            {
                "id": requirement_id,
                "status": status,
                "sources": sorted(requirements[requirement_id]),
                "trace_entry": requirement_id if entry is not None else None,
            }
        )

    unknown_trace_ids = sorted(set(entries) - set(requirements))
    errors.extend(f"trace entry is not present in specifications: {item}" for item in unknown_trace_ids)

    acceptance_rows = []
    for acceptance_id in sorted(acceptance):
        evidence = sorted(acceptance_evidence.get(acceptance_id, set()))
        acceptance_rows.append(
            {
                "id": acceptance_id,
                "status": "verified" if evidence else "missing",
                "sources": sorted(acceptance[acceptance_id]),
                "evidence": evidence,
            }
        )

    statuses = {
        row["status"] for row in requirement_rows + acceptance_rows
    }
    invalid_statuses = statuses - VALID_STATUSES
    if invalid_statuses:
        errors.append(f"invalid statuses generated: {sorted(invalid_statuses)}")

    report = {
        "version": 1,
        "requirements": requirement_rows,
        "acceptance_criteria": acceptance_rows,
        "summary": {
            "requirements": _status_counts(requirement_rows),
            "acceptance_criteria": _status_counts(acceptance_rows),
            "trace_entries": len(entries),
            "errors": len(errors),
        },
        "errors": errors,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    return 0


def _discover(pattern: re.Pattern[str], paths) -> dict[str, set[str]]:
    discovered: dict[str, set[str]] = defaultdict(set)
    for path in paths:
        text = path.read_text(encoding="utf-8")
        for identifier in pattern.findall(text):
            discovered[identifier].add(str(path.relative_to(ROOT)))
    return discovered


def _entry_status(
    requirement_id: str,
    entry: dict,
    requirements: dict[str, set[str]],
    acceptance: dict[str, set[str]],
    architecture_ids: dict[str, set[str]],
    acceptance_evidence: dict[str, set[str]],
    errors: list[str],
) -> str:
    _ = requirements
    code_paths = entry.get("code", [])
    test_paths = entry.get("tests", [])
    for architecture_id in entry.get("architecture", []):
        if architecture_id not in architecture_ids:
            errors.append(
                f"{requirement_id}: unknown architecture element {architecture_id}"
            )
    for acceptance_id in entry.get("acceptance", []):
        if acceptance_id not in acceptance:
            errors.append(f"{requirement_id}: unknown acceptance criterion {acceptance_id}")
        for test_path in test_paths:
            acceptance_evidence[acceptance_id].add(test_path)
    missing_code = _missing_paths(code_paths)
    missing_tests = _missing_paths(test_paths)
    errors.extend(f"{requirement_id}: missing code path {path}" for path in missing_code)
    errors.extend(f"{requirement_id}: missing test path {path}" for path in missing_tests)
    if missing_code or not code_paths:
        return "missing"
    if missing_tests or not test_paths:
        return "implemented"
    return "verified"


def _missing_paths(paths: list[str]) -> list[str]:
    return [path for path in paths if not (ROOT / path).exists()]


def _status_counts(rows: list[dict]) -> dict[str, int]:
    return {
        status: sum(row["status"] == status for row in rows)
        for status in sorted(VALID_STATUSES)
    }


if __name__ == "__main__":
    raise SystemExit(main())
