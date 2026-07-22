#!/usr/bin/env python3
"""Run deterministic database-path benchmarks against the seeded dataset."""

from __future__ import annotations

import argparse
import asyncio
from math import ceil
import json
from pathlib import Path
import sys
from time import perf_counter

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.baselines import (
    BaselineArtefactRevision,
    BaselineRelationshipRevision,
)


TARGETS_MS = {
    "get_single_artefact": 100,
    "update_artefact": 200,
    "direct_trace": 500,
    "traceability_matrix": 5_000,
    "baseline_comparison": 5_000,
}


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--project-id", default="PROJ_PERFORMANCE")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/generated/performance-results.json"),
    )
    args = parser.parse_args()
    results = await benchmark(args.database_url, args.project_id)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(results, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(results, indent=2))
    if any(item["blocking"] for item in results["benchmarks"].values()):
        raise SystemExit(1)


async def benchmark(database_url: str, project_id: str) -> dict:
    engine = create_async_engine(database_url, pool_pre_ping=True)
    artefact_id = "ART_PERF_000001"
    try:
        benchmarks = {
            "get_single_artefact": await _measure(
                100,
                lambda: _get_artefact(engine, project_id, artefact_id),
            ),
            "update_artefact": await _measure(
                30,
                lambda: _update_artefact(engine, project_id, artefact_id),
            ),
            "direct_trace": await _measure(
                50,
                lambda: _direct_trace(engine, project_id, artefact_id),
            ),
            "traceability_matrix": await _measure(
                10,
                lambda: _traceability_matrix(engine, project_id),
            ),
            "baseline_comparison": await _measure(
                10,
                lambda: _baseline_comparison(engine),
            ),
        }
        for name, result in benchmarks.items():
            target = TARGETS_MS[name]
            result["target_ms"] = target
            result["status"] = "pass" if result["p95_ms"] <= target else "fail"
            result["blocking"] = result["p95_ms"] > target * 2
        return {
            "version": 1,
            "project_id": project_id,
            "path": "database",
            "benchmarks": benchmarks,
        }
    finally:
        await engine.dispose()


async def _measure(iterations: int, operation) -> dict:
    samples = []
    for _ in range(iterations):
        started = perf_counter()
        await operation()
        samples.append((perf_counter() - started) * 1000)
    ordered = sorted(samples)
    return {
        "iterations": iterations,
        "p50_ms": round(ordered[ceil(iterations * 0.50) - 1], 3),
        "p95_ms": round(ordered[ceil(iterations * 0.95) - 1], 3),
        "max_ms": round(max(samples), 3),
    }


async def _get_artefact(engine, project_id: str, artefact_id: str) -> None:
    async with engine.connect() as connection:
        await connection.execute(
            select(Artefact).where(
                Artefact.project_id == project_id,
                Artefact.artefact_id == artefact_id,
            )
        )


async def _update_artefact(engine, project_id: str, artefact_id: str) -> None:
    async with engine.begin() as connection:
        await connection.execute(
            update(Artefact)
            .where(
                Artefact.project_id == project_id,
                Artefact.artefact_id == artefact_id,
            )
            .values(description="performance benchmark update")
        )


async def _direct_trace(engine, project_id: str, artefact_id: str) -> None:
    async with engine.connect() as connection:
        await connection.execute(
            select(Relationship).where(
                Relationship.project_id == project_id,
                (
                    (Relationship.source_artefact_id == artefact_id)
                    | (Relationship.target_artefact_id == artefact_id)
                ),
                Relationship.deleted_at.is_(None),
            )
        )


async def _traceability_matrix(engine, project_id: str) -> None:
    async with engine.connect() as connection:
        result = await connection.execute(
            select(
                Relationship.source_artefact_id,
                Relationship.relationship_type,
                Relationship.target_artefact_id,
            ).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
        result.all()


async def _baseline_comparison(engine) -> None:
    async with engine.connect() as connection:
        for table, id_column, revision_column in (
            (
                BaselineArtefactRevision,
                BaselineArtefactRevision.artefact_id,
                BaselineArtefactRevision.artefact_revision_id,
            ),
            (
                BaselineRelationshipRevision,
                BaselineRelationshipRevision.relationship_id,
                BaselineRelationshipRevision.relationship_revision_id,
            ),
        ):
            _ = table
            left = await connection.execute(
                select(id_column, revision_column).where(
                    id_column.class_.baseline_id == "BASE_PERF_01"
                )
            )
            right = await connection.execute(
                select(id_column, revision_column).where(
                    id_column.class_.baseline_id == "BASE_PERF_02"
                )
            )
            dict(left.all())
            dict(right.all())


if __name__ == "__main__":
    asyncio.run(main())
