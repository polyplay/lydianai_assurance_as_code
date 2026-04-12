from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, get_current_user, project_role_dependency
from aac_backend.database import get_session
from aac_backend.models.artefacts import Artefact, ArtefactRevision
from aac_backend.repositories.domain import ArtefactRepository
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import ArtefactCreate, ArtefactRead, ArtefactUpdate
from aac_backend.services.artefact_service import (
    change_artefact_status,
    create_artefact,
    obsolete_artefact,
    update_artefact,
)

router = APIRouter(tags=["artefacts"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/projects/{project_id}/artefacts", response_model=ApiEnvelope)
async def list_artefacts(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefacts = await ArtefactRepository(session).list_for_project(project_id)
    return ApiEnvelope(data=[ArtefactRead.model_validate(artefact) for artefact in artefacts])


@router.post("/projects/{project_id}/artefacts", response_model=ApiEnvelope)
async def create_artefact_endpoint(
    project_id: str,
    payload: ArtefactCreate,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    try:
        artefact = await create_artefact(session, project_id, payload, current.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.delete("/projects/{project_id}/artefacts/{artefact_id}", response_model=ApiEnvelope)
async def delete_artefact(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    await obsolete_artefact(session, artefact, current.user.user_id)
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post(
    "/projects/{project_id}/artefacts/{artefact_id}/submit-for-review",
    response_model=ApiEnvelope,
)
async def submit_for_review(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    if artefact.owner_user_id != current.user.user_id:
        await project_role_dependency("admin", "quality_engineer")(project_id, current, session)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status="under_review",
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/mark-reviewed", response_model=ApiEnvelope)
async def mark_reviewed(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status="reviewed",
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/reject", response_model=ApiEnvelope)
async def reject_review(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status="draft",
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/approve", response_model=ApiEnvelope)
async def approve_artefact(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status="approved",
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/release", response_model=ApiEnvelope)
async def release_artefact(
    project_id: str,
    artefact_id: str,
    current: CurrentUser = Depends(project_role_dependency("admin", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status="released",
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/status", response_model=ApiEnvelope)
async def status_transition(
    project_id: str,
    artefact_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    artefact = await change_artefact_status(
        session,
        artefact,
        new_status=payload["status"],
        actor_user_id=current.user.user_id,
    )
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.get("/projects/{project_id}/artefacts/{artefact_id}/status", response_model=ApiEnvelope)
async def get_artefact_status(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await _get_artefact_or_404(session, project_id, artefact_id)
    return ApiEnvelope(
        data={
            "artefact_id": artefact.artefact_id,
            "status": artefact.status,
            "current_revision_id": artefact.current_revision_id,
            "current_fingerprint": artefact.current_fingerprint,
        }
    )


@router.get("/projects/{project_id}/artefacts/{artefact_id}/revisions", response_model=ApiEnvelope)
async def list_revisions(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    await _get_artefact_or_404(session, project_id, artefact_id)
    revisions = list(
        await session.scalars(
            select(ArtefactRevision)
            .where(ArtefactRevision.project_id == project_id, ArtefactRevision.artefact_id == artefact_id)
            .order_by(ArtefactRevision.revision_number)
        )
    )
    return ApiEnvelope(data=[_revision_data(revision) for revision in revisions])


@router.get(
    "/projects/{project_id}/artefacts/{artefact_id}/revisions/{revision_id}",
    response_model=ApiEnvelope,
)
async def get_revision(
    project_id: str,
    artefact_id: str,
    revision_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    revision = await session.get(ArtefactRevision, revision_id)
    if not revision or revision.project_id != project_id or revision.artefact_id != artefact_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    return ApiEnvelope(data=_revision_data(revision))


@router.post("/projects/{project_id}/artefacts/{artefact_id}/compare", response_model=ApiEnvelope)
async def compare_revisions(
    project_id: str,
    artefact_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    left = await session.get(ArtefactRevision, payload["left_revision_id"])
    right = await session.get(ArtefactRevision, payload["right_revision_id"])
    if not left or not right or left.artefact_id != artefact_id or right.artefact_id != artefact_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    if left.project_id != project_id or right.project_id != project_id:
        raise HTTPException(status_code=404, detail="Revision not found")
    return ApiEnvelope(
        data={
            "left_revision_id": left.artefact_revision_id,
            "right_revision_id": right.artefact_revision_id,
            "same_fingerprint": left.content_fingerprint == right.content_fingerprint,
            "left_payload": left.payload_json,
            "right_payload": right.payload_json,
        }
    )


async def _get_artefact_or_404(session: AsyncSession, project_id: str, artefact_id: str) -> Artefact:
    artefact = await session.get(Artefact, artefact_id)
    if not artefact or artefact.project_id != project_id:
        raise HTTPException(status_code=404, detail="Artefact not found")
    return artefact


def _revision_data(revision: ArtefactRevision) -> dict:
    return {
        "artefact_revision_id": revision.artefact_revision_id,
        "artefact_id": revision.artefact_id,
        "revision_number": revision.revision_number,
        "payload": revision.payload_json,
        "metadata": revision.metadata_json,
        "content_fingerprint": revision.content_fingerprint,
        "changed_at": revision.changed_at,
    }


@router.get("/projects/{project_id}/artefacts/{artefact_id}", response_model=ApiEnvelope)
async def get_artefact(
    project_id: str,
    artefact_id: str,
    _: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await session.get(Artefact, artefact_id)
    if not artefact or artefact.project_id != project_id:
        raise HTTPException(status_code=404, detail="Artefact not found")
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))


@router.put("/projects/{project_id}/artefacts/{artefact_id}", response_model=ApiEnvelope)
async def update_artefact_endpoint(
    project_id: str,
    artefact_id: str,
    payload: ArtefactUpdate,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    artefact = await session.get(Artefact, artefact_id)
    if not artefact or artefact.project_id != project_id:
        raise HTTPException(status_code=404, detail="Artefact not found")
    artefact = await update_artefact(session, artefact, payload, current.user.user_id)
    await session.commit()
    return ApiEnvelope(data=ArtefactRead.model_validate(artefact))
