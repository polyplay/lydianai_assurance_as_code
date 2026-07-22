from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import CurrentUser, project_role_dependency
from aac_backend.database import get_session
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.services.workspace_service import workspace_projection

router = APIRouter(tags=["workspace"])
PROJECT_ROLES = ("admin", "project_lead", "quality_engineer", "user")


@router.get("/projects/{project_id}/workspace", response_model=ApiEnvelope)
async def project_workspace(
    project_id: str,
    current: CurrentUser = Depends(project_role_dependency(*PROJECT_ROLES)),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    try:
        data = await workspace_projection(
            session,
            project_id=project_id,
            current=current,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ApiEnvelope(data=data)
