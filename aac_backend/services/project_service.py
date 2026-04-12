from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.projects import Project, ProjectConfiguration
from aac_backend.schemas.domain import ProjectCreate
from aac_backend.services.event_service import record_event


async def create_project(session: AsyncSession, data: ProjectCreate, actor_user_id: str) -> Project:
    existing = await session.scalar(select(Project).where(Project.project_key == data.project_key))
    if existing:
        raise ValueError("project_key already exists")
    project = Project(
        project_key=data.project_key,
        name=data.name,
        description=data.description,
        active_profile_id=data.active_profile_id,
        status="active",
    )
    session.add(project)
    await session.flush()
    session.add(
        ProjectConfiguration(
            project_id=project.project_id,
            version_update_mode="ask_user",
            baseline_policy_json={},
            validation_policy_json={},
            reporting_policy_json={},
        )
    )
    await record_event(
        session,
        event_type="project.created",
        project_id=project.project_id,
        actor_user_id=actor_user_id,
        payload={"project_key": project.project_key},
    )
    return project


async def archive_project(session: AsyncSession, project: Project, actor_user_id: str) -> Project:
    project.status = "archived"
    project.updated_at = datetime.now(UTC)
    await record_event(
        session,
        event_type="project.archived",
        project_id=project.project_id,
        actor_user_id=actor_user_id,
    )
    return project
