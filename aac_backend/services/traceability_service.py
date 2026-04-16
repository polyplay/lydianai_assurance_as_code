from collections import defaultdict, deque

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Relationship

MAX_TRACE_DEPTH = 10


async def trace_artefact(session: AsyncSession, project_id: str, artefact_id: str) -> dict:
    relationships = list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
    )
    return {
        "artefact_id": artefact_id,
        "forward": _trace_direction(relationships, artefact_id, "forward"),
        "backward": _trace_direction(relationships, artefact_id, "backward"),
    }


def _trace_direction(relationships: list[Relationship], artefact_id: str, direction: str) -> list[dict]:
    forward_index: defaultdict[str, list[Relationship]] = defaultdict(list)
    backward_index: defaultdict[str, list[Relationship]] = defaultdict(list)
    for relationship in relationships:
        forward_index[relationship.source_artefact_id].append(relationship)
        backward_index[relationship.target_artefact_id].append(relationship)
    index = forward_index if direction == "forward" else backward_index
    visited = {artefact_id}
    queue = deque([(artefact_id, [], 0)])
    traced = []
    while queue:
        current_id, path, depth = queue.popleft()
        if depth >= MAX_TRACE_DEPTH:
            continue
        for relationship in index.get(current_id, []):
            next_id = (
                relationship.target_artefact_id
                if direction == "forward"
                else relationship.source_artefact_id
            )
            edge = _relationship_summary(relationship)
            next_path = [*path, edge]
            traced.append({**edge, "depth": depth + 1, "path": next_path})
            if next_id in visited:
                continue
            visited.add(next_id)
            queue.append((next_id, next_path, depth + 1))
    return traced


async def direct_trace_artefact(session: AsyncSession, project_id: str, artefact_id: str) -> dict:
    forward = await session.scalars(
        select(Relationship).where(
            Relationship.project_id == project_id,
            Relationship.source_artefact_id == artefact_id,
            Relationship.deleted_at.is_(None),
        )
    )
    backward = await session.scalars(
        select(Relationship).where(
            Relationship.project_id == project_id,
            Relationship.target_artefact_id == artefact_id,
            Relationship.deleted_at.is_(None),
        )
    )
    return {
        "artefact_id": artefact_id,
        "forward": [_relationship_summary(item) for item in forward],
        "backward": [_relationship_summary(item) for item in backward],
    }


def _relationship_summary(relationship: Relationship) -> dict:
    return {
        "relationship_id": relationship.relationship_id,
        "relationship_type": relationship.relationship_type,
        "source_artefact_id": relationship.source_artefact_id,
        "target_artefact_id": relationship.target_artefact_id,
    }
