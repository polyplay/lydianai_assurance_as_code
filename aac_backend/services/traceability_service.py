from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Relationship


async def trace_artefact(session: AsyncSession, project_id: str, artefact_id: str) -> dict:
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
