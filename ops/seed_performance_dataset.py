#!/usr/bin/env python3
"""Seed the deterministic MVP-scale performance dataset."""

from __future__ import annotations

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path
import random
import sys

from sqlalchemy import insert, select, text
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from aac_backend.models.access import User
from aac_backend.models.artefacts import (
    Artefact,
    ArtefactRevision,
    Relationship,
    RelationshipRevision,
)
from aac_backend.models.audit import AuditEvent
from aac_backend.models.baselines import (
    Baseline,
    BaselineArtefactRevision,
    BaselineRelationshipRevision,
)
from aac_backend.models.projects import Project


ARTEFACT_COUNTS = {
    "SoftwareSafetyRequirement": 100,
    "SoftwareRequirement": 400,
    "SoftwareComponent": 100,
    "SoftwareUnit": 200,
    "InterfaceContract": 150,
    "TestSpecification": 50,
    "TestCase": 500,
    "TestResult": 5000,
}
RELATIONSHIP_COUNT = 10_000
BASELINE_COUNT = 5
AUDIT_EVENT_COUNT = 50_000
BATCH_SIZE = 2_000


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    parser.add_argument("--seed", type=int, default=20260613)
    parser.add_argument("--project-id", default="PROJ_PERFORMANCE")
    args = parser.parse_args()
    await seed(args.database_url, args.project_id, args.seed)


async def seed(database_url: str, project_id: str, seed_value: int) -> None:
    engine = create_async_engine(database_url)
    rng = random.Random(seed_value)
    now = datetime.now(UTC)
    user_id = "USER_PERFORMANCE"
    try:
        async with engine.begin() as connection:
            existing = await connection.scalar(
                select(Project.project_id).where(Project.project_id == project_id)
            )
            if existing:
                raise RuntimeError(
                    f"project {project_id} already exists; use a fresh benchmark database"
                )
            await connection.execute(
                insert(User),
                [
                    {
                        "user_id": user_id,
                        "username": "performance-runner",
                        "display_name": "Performance Runner",
                        "email": "performance@example.test",
                        "status": "active",
                        "global_roles_json": ["admin"],
                        "password_hash": "",
                        "password_updated_at": now,
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
            )
            await connection.execute(
                insert(Project),
                [
                    {
                        "project_id": project_id,
                        "project_key": "PERFORMANCE",
                        "name": "Deterministic performance dataset",
                        "description": f"Fixed random seed {seed_value}",
                        "status": "active",
                        "created_at": now,
                        "updated_at": now,
                    }
                ],
            )

            artefacts = _artefact_rows(project_id, now)
            revisions = _artefact_revision_rows(artefacts, project_id, now)
            await _insert_batches(connection, Artefact.__table__, artefacts)
            await _insert_batches(connection, ArtefactRevision.__table__, revisions)
            await connection.execute(
                text(
                    """
                    UPDATE artefacts
                    SET current_revision_id = replace(artefact_id, 'ART_', 'AREV_')
                    WHERE project_id = :project_id
                    """
                ),
                {"project_id": project_id},
            )

            relationships = _relationship_rows(project_id, artefacts, rng, now)
            relationship_revisions = _relationship_revision_rows(
                relationships, project_id, now
            )
            await _insert_batches(connection, Relationship.__table__, relationships)
            await _insert_batches(
                connection,
                RelationshipRevision.__table__,
                relationship_revisions,
            )
            await connection.execute(
                text(
                    """
                    UPDATE relationships
                    SET current_revision_id = replace(relationship_id, 'REL_', 'RREV_')
                    WHERE project_id = :project_id
                    """
                ),
                {"project_id": project_id},
            )

            baselines = [
                {
                    "baseline_id": f"BASE_PERF_{index:02d}",
                    "project_id": project_id,
                    "name": f"Performance baseline {index}",
                    "description": "",
                    "state": "created",
                    "created_by": user_id,
                    "created_at": now,
                    "release_gate_status": "not_evaluated",
                    "eligibility_result_json": {},
                    "summary_json": {},
                }
                for index in range(1, BASELINE_COUNT + 1)
            ]
            await connection.execute(insert(Baseline), baselines)
            await _seed_baseline_snapshots(connection, artefacts, relationships)

            audit_rows = [
                {
                    "audit_event_id": f"AUDIT_PERF_{index:06d}",
                    "project_id": project_id,
                    "event_type": "performance.seeded",
                    "actor_user_id": user_id,
                    "actor_type": "system",
                    "role_at_time_of_action": "admin",
                    "operation": "seed_performance_dataset",
                    "request_id": f"REQ_PERF_{index:06d}",
                    "correlation_id": "CORR_PERFORMANCE",
                    "affected_artefact_ids_json": [],
                    "affected_relationship_ids_json": [],
                    "payload_json": {"sequence": index, "seed": seed_value},
                    "created_at": now,
                }
                for index in range(1, AUDIT_EVENT_COUNT + 1)
            ]
            await _insert_batches(connection, AuditEvent.__table__, audit_rows)
        print(
            {
                "project_id": project_id,
                "seed": seed_value,
                "artefacts": len(artefacts),
                "relationships": len(relationships),
                "baselines": len(baselines),
                "audit_events": len(audit_rows),
            }
        )
    finally:
        await engine.dispose()


def _artefact_rows(project_id: str, now: datetime) -> list[dict]:
    rows = []
    index = 0
    for artefact_type, count in ARTEFACT_COUNTS.items():
        for type_index in range(1, count + 1):
            index += 1
            artefact_id = f"ART_PERF_{index:06d}"
            payload = {"sequence": type_index, "dataset": "performance"}
            rows.append(
                {
                    "artefact_id": artefact_id,
                    "project_id": project_id,
                    "artefact_type": artefact_type,
                    "title": f"{artefact_type} {type_index}",
                    "description": "",
                    "status": "draft",
                    "source_kind": "performance_seed",
                    "source_object_id": f"{artefact_type}_{type_index:06d}",
                    "source_document": "performance-dataset",
                    "standards_refs_json": [],
                    "review_expectation": "none",
                    "independence_expectation": "none",
                    "payload_json": payload,
                    "created_at": now,
                    "updated_at": now,
                }
            )
    return rows


def _artefact_revision_rows(
    artefacts: list[dict],
    project_id: str,
    now: datetime,
) -> list[dict]:
    return [
        {
            "artefact_revision_id": row["artefact_id"].replace("ART_", "AREV_", 1),
            "artefact_id": row["artefact_id"],
            "project_id": project_id,
            "revision_number": 1,
            "schema_version": "1.0",
            "payload_json": row["payload_json"],
            "metadata_json": {"title": row["title"], "status": row["status"]},
            "change_reason": "performance seed",
            "changed_at": now,
        }
        for row in artefacts
    ]


def _relationship_rows(
    project_id: str,
    artefacts: list[dict],
    rng: random.Random,
    now: datetime,
) -> list[dict]:
    artefact_ids = [row["artefact_id"] for row in artefacts]
    types = ("depends_on", "verifies", "satisfies", "allocates_to")
    rows = []
    for index in range(1, RELATIONSHIP_COUNT + 1):
        source = rng.choice(artefact_ids)
        target = rng.choice(artefact_ids)
        if target == source:
            target = artefact_ids[(artefact_ids.index(source) + 1) % len(artefact_ids)]
        rows.append(
            {
                "relationship_id": f"REL_PERF_{index:06d}",
                "project_id": project_id,
                "relationship_type": types[index % len(types)],
                "source_artefact_id": source,
                "target_artefact_id": target,
                "status": "active",
                "payload_json": {"sequence": index},
                "created_at": now,
                "updated_at": now,
            }
        )
    return rows


def _relationship_revision_rows(
    relationships: list[dict],
    project_id: str,
    now: datetime,
) -> list[dict]:
    return [
        {
            "relationship_revision_id": row["relationship_id"].replace(
                "REL_", "RREV_", 1
            ),
            "relationship_id": row["relationship_id"],
            "project_id": project_id,
            "revision_number": 1,
            "payload_json": row["payload_json"],
            "changed_at": now,
        }
        for row in relationships
    ]


async def _seed_baseline_snapshots(connection, artefacts, relationships) -> None:
    for baseline_id in ("BASE_PERF_01", "BASE_PERF_02"):
        await _insert_batches(
            connection,
            BaselineArtefactRevision.__table__,
            [
                {
                    "baseline_id": baseline_id,
                    "artefact_id": row["artefact_id"],
                    "artefact_revision_id": row["artefact_id"].replace(
                        "ART_", "AREV_", 1
                    ),
                    "artefact_type": row["artefact_type"],
                }
                for row in artefacts
            ],
        )
        await _insert_batches(
            connection,
            BaselineRelationshipRevision.__table__,
            [
                {
                    "baseline_id": baseline_id,
                    "relationship_id": row["relationship_id"],
                    "relationship_revision_id": row["relationship_id"].replace(
                        "REL_", "RREV_", 1
                    ),
                    "relationship_type": row["relationship_type"],
                }
                for row in relationships
            ],
        )


async def _insert_batches(connection, table, rows: list[dict]) -> None:
    for start in range(0, len(rows), BATCH_SIZE):
        await connection.execute(insert(table), rows[start : start + BATCH_SIZE])


if __name__ == "__main__":
    asyncio.run(main())
