from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.projects import AssuranceProfile, Project, ProjectConfiguration
from aac_backend.schemas.domain import ProjectCreate
from aac_backend.services.assurance_configuration_service import (
    assurance_configuration_from_profile_id,
    derive_profile_payload,
    derive_validation_policy,
    normalize_assurance_configuration,
)
from aac_backend.services.event_service import record_event
from aac_backend.services.profile_service import seed_default_profiles


async def create_project(session: AsyncSession, data: ProjectCreate, actor_user_id: str) -> Project:
    await seed_default_profiles(session)
    existing = await session.scalar(select(Project).where(Project.project_key == data.project_key))
    if existing:
        raise ValueError("project_key already exists")
    assurance_config = (
        normalize_assurance_configuration(data.assurance_configuration.model_dump())
        if data.assurance_configuration
        else assurance_configuration_from_profile_id(data.active_profile_id)
    )
    project = Project(
        project_key=data.project_key,
        name=data.name,
        description=data.description,
        active_profile_id=data.active_profile_id or None,
        status="active",
    )
    session.add(project)
    await session.flush()
    config = ProjectConfiguration(
        project_id=project.project_id,
        version_update_mode="ask_user",
        baseline_policy_json={},
        validation_policy_json={},
        reporting_policy_json={},
    )
    session.add(config)
    if data.assurance_configuration:
        await apply_assurance_configuration(
            session,
            project=project,
            config=config,
            raw_configuration=assurance_config,
            actor_user_id=actor_user_id,
            event_type="project.assurance_configuration_created",
        )
    else:
        project.active_profile_id = data.active_profile_id or "ASIL_D_DEFAULT"
        config.validation_policy_json = derive_validation_policy(assurance_config)
    await record_event(
        session,
        event_type="project.created",
        project_id=project.project_id,
        actor_user_id=actor_user_id,
        payload={
            "project_key": project.project_key,
            "assurance_configuration": assurance_config,
        },
    )
    return project


async def apply_assurance_configuration(
    session: AsyncSession,
    *,
    project: Project,
    config: ProjectConfiguration,
    raw_configuration: dict,
    actor_user_id: str,
    event_type: str = "project.assurance_configuration_updated",
) -> AssuranceProfile:
    assurance_config = normalize_assurance_configuration(raw_configuration)
    profile_payload = derive_profile_payload(assurance_config)
    profile = await _active_project_profile(session, project)
    if profile is None:
        profile = AssuranceProfile(
            project_id=project.project_id,
            name=f"{project.project_key} derived assurance profile",
            classification=assurance_config["asil_level"],
            inherits_from_profile_id=f"{assurance_config['asil_level']}_DEFAULT",
            profile_payload_json=profile_payload,
            status="active",
        )
        session.add(profile)
        await session.flush()
    else:
        profile.name = f"{project.project_key} derived assurance profile"
        profile.classification = assurance_config["asil_level"]
        profile.inherits_from_profile_id = f"{assurance_config['asil_level']}_DEFAULT"
        profile.profile_payload_json = profile_payload
        profile.status = "active"
    project.active_profile_id = profile.profile_id
    config.validation_policy_json = derive_validation_policy(
        assurance_config,
        existing_policy=config.validation_policy_json,
    )
    await record_event(
        session,
        event_type=event_type,
        project_id=project.project_id,
        actor_user_id=actor_user_id,
        payload={"assurance_configuration": assurance_config, "profile_id": profile.profile_id},
    )
    return profile


async def _active_project_profile(
    session: AsyncSession,
    project: Project,
) -> AssuranceProfile | None:
    if not project.active_profile_id:
        return None
    profile = await session.get(AssuranceProfile, project.active_profile_id)
    if profile is not None and profile.project_id == project.project_id:
        return profile
    return None


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
