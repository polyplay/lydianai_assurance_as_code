from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.artefacts import Artefact, Relationship, RelationshipRevision
from aac_backend.repositories.domain import RelationshipRepository
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import RelationshipCreate, RelationshipRead
from aac_backend.services.artefact_service import create_relationship, ensure_project_writable
from aac_backend.services.event_service import record_event
from aac_backend.services.impact_service import propagate_suspects
from aac_backend.services.validation_service import relationship_type_allowed_for_types, run_validation

router = APIRouter(tags=["relationships"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/projects/{project_id}/relationships", response_model=ApiEnvelope)
async def list_relationships(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    relationships = await RelationshipRepository(session).list_for_project(project_id)
    return ApiEnvelope(data=[RelationshipRead.model_validate(item) for item in relationships])


@router.post("/projects/{project_id}/relationships", response_model=ApiEnvelope)
async def create_relationship_endpoint(
    project_id: str,
    payload: RelationshipCreate,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    try:
        relationship = await create_relationship(session, project_id, payload, current.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=RelationshipRead.model_validate(relationship))


@router.get("/projects/{project_id}/relationships/{relationship_id}", response_model=ApiEnvelope)
async def get_relationship(
    project_id: str,
    relationship_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    relationship = await session.get(Relationship, relationship_id)
    if not relationship or relationship.project_id != project_id:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return ApiEnvelope(data=RelationshipRead.model_validate(relationship))


@router.put("/projects/{project_id}/relationships/{relationship_id}", response_model=ApiEnvelope)
async def update_relationship(
    project_id: str,
    relationship_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    relationship = await _get_relationship_or_404(session, project_id, relationship_id)
    await ensure_project_writable(session, project_id)
    next_type = payload.get("relationship_type", relationship.relationship_type)
    if next_type != relationship.relationship_type:
        source = await session.get(Artefact, relationship.source_artefact_id)
        target = await session.get(Artefact, relationship.target_artefact_id)
        if not source or not target or not relationship_type_allowed_for_types(
            source.artefact_type,
            target.artefact_type,
            next_type,
            same_artefact=source.artefact_id == target.artefact_id,
        ):
            raise HTTPException(
                status_code=409,
                detail="relationship type is not permitted for the source and target artefact types",
            )
    relationship.relationship_type = next_type
    relationship.payload_json = payload.get("payload", relationship.payload_json)
    relationship.updated_at = datetime.now(UTC)
    repo = RelationshipRepository(session)
    revision = RelationshipRevision(
        relationship_id=relationship.relationship_id,
        project_id=project_id,
        revision_number=await repo.next_revision_number(relationship.relationship_id),
        payload_json=relationship.payload_json,
        changed_by=current.user.user_id,
        changed_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    relationship.current_revision_id = revision.relationship_revision_id
    await record_event(
        session,
        event_type="relationship.revised",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        affected_relationship_ids=[relationship.relationship_id],
    )
    await session.commit()
    return ApiEnvelope(data=RelationshipRead.model_validate(relationship))


@router.delete("/projects/{project_id}/relationships/{relationship_id}", response_model=ApiEnvelope)
async def delete_relationship(
    project_id: str,
    relationship_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    relationship = await _get_relationship_or_404(session, project_id, relationship_id)
    await ensure_project_writable(session, project_id)
    relationship.status = "obsolete"
    relationship.deleted_at = datetime.now(UTC)
    repo = RelationshipRepository(session)
    revision = RelationshipRevision(
        relationship_id=relationship.relationship_id,
        project_id=project_id,
        revision_number=await repo.next_revision_number(relationship.relationship_id),
        payload_json={**relationship.payload_json, "status": "obsolete"},
        changed_by=current.user.user_id,
        changed_at=datetime.now(UTC),
    )
    session.add(revision)
    await session.flush()
    relationship.current_revision_id = revision.relationship_revision_id
    await record_event(
        session,
        event_type="relationship.deleted",
        project_id=project_id,
        actor_user_id=current.user.user_id,
        affected_relationship_ids=[relationship.relationship_id],
    )
    await propagate_suspects(
        session,
        project_id=project_id,
        trigger_artefact_id=relationship.target_artefact_id,
        trigger_revision_id=None,
        trigger_event_type="relationship.deleted",
        actor_user_id=current.user.user_id,
    )
    await run_validation(
        session,
        project_id,
        current.user.user_id,
        scope={"type": "project", "trigger": "relationship.deleted", "relationship_id": relationship_id},
    )
    await session.commit()
    return ApiEnvelope(data=RelationshipRead.model_validate(relationship))


@router.get(
    "/projects/{project_id}/relationships/{relationship_id}/revisions",
    response_model=ApiEnvelope,
)
async def list_relationship_revisions(
    project_id: str,
    relationship_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    await _get_relationship_or_404(session, project_id, relationship_id)
    revisions = list(
        await session.scalars(
            select(RelationshipRevision)
            .where(
                RelationshipRevision.project_id == project_id,
                RelationshipRevision.relationship_id == relationship_id,
            )
            .order_by(RelationshipRevision.revision_number)
        )
    )
    return ApiEnvelope(
        data=[
            {
                "relationship_revision_id": revision.relationship_revision_id,
                "relationship_id": revision.relationship_id,
                "revision_number": revision.revision_number,
                "payload": revision.payload_json,
                "changed_at": revision.changed_at,
            }
            for revision in revisions
        ]
    )


@router.post("/projects/{project_id}/relationships/{relationship_id}/compare", response_model=ApiEnvelope)
async def compare_relationship_revisions(
    project_id: str,
    relationship_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    left = await session.get(RelationshipRevision, payload["left_revision_id"])
    right = await session.get(RelationshipRevision, payload["right_revision_id"])
    if (
        not left
        or not right
        or left.project_id != project_id
        or right.project_id != project_id
        or left.relationship_id != relationship_id
        or right.relationship_id != relationship_id
    ):
        raise HTTPException(status_code=404, detail="Relationship revision not found")
    return ApiEnvelope(
        data={
            "left_revision_id": left.relationship_revision_id,
            "right_revision_id": right.relationship_revision_id,
            "same_payload": left.payload_json == right.payload_json,
            "left_payload": left.payload_json,
            "right_payload": right.payload_json,
        }
    )


async def _get_relationship_or_404(
    session: AsyncSession,
    project_id: str,
    relationship_id: str,
) -> Relationship:
    relationship = await session.get(Relationship, relationship_id)
    if not relationship or relationship.project_id != project_id:
        raise HTTPException(status_code=404, detail="Relationship not found")
    return relationship
