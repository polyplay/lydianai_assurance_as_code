from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.projects import AssuranceProfile, Project, ProjectConfiguration, TailoringDecision
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
    tailoring_rationale: str | None = None,
    tailoring_evidence_refs: list[str] | str | None = None,
    require_tailoring_approval: bool = False,
    previous_assurance_configuration: dict[str, Any] | None = None,
) -> AssuranceProfile:
    previous_config = (
        previous_assurance_configuration
        if previous_assurance_configuration is not None
        else (config.validation_policy_json or {}).get("project_assurance_configuration") or {}
    )
    assurance_config = normalize_assurance_configuration(raw_configuration)
    tailoring_changes = aspice_tailoring_changes(previous_config, assurance_config)
    evidence_refs = _normalize_evidence_refs(tailoring_evidence_refs)
    if require_tailoring_approval and tailoring_changes:
        if not tailoring_rationale or not tailoring_rationale.strip():
            raise ValueError("ASPICE process scope or capability changes require tailoring_rationale")
        if not evidence_refs:
            raise ValueError("ASPICE process scope or capability changes require tailoring_evidence_refs")
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
    if tailoring_changes and tailoring_rationale and evidence_refs:
        await _record_aspice_tailoring_decisions(
            session,
            project_id=project.project_id,
            actor_user_id=actor_user_id,
            changes=tailoring_changes,
            rationale=tailoring_rationale.strip(),
            evidence_refs=evidence_refs,
        )
    await record_event(
        session,
        event_type=event_type,
        project_id=project.project_id,
        actor_user_id=actor_user_id,
        payload={"assurance_configuration": assurance_config, "profile_id": profile.profile_id},
    )
    return profile


def aspice_tailoring_changes(
    previous_raw: dict[str, Any] | None,
    updated_raw: dict[str, Any] | None,
) -> list[dict[str, str]]:
    if not previous_raw:
        return []
    previous = normalize_assurance_configuration(previous_raw)
    updated = normalize_assurance_configuration(updated_raw)
    changes: list[dict[str, str]] = []

    previous_default = previous["aspice_default_capability_level"]
    updated_default = updated["aspice_default_capability_level"]
    if previous_default != updated_default:
        changes.append(
            {
                "target_kind": "aspice_default_capability",
                "target_id": "ASPICE_DEFAULT_CAPABILITY",
                "previous": f"CL{previous_default}",
                "current": f"CL{updated_default}",
            }
        )

    previous_scope = set(previous["aspice_scoped_processes"])
    updated_scope = set(updated["aspice_scoped_processes"])
    previous_targets = previous["aspice_process_capability_targets"]
    updated_targets = updated["aspice_process_capability_targets"]
    for process in sorted(updated_scope - previous_scope):
        changes.append(
            {
                "target_kind": "aspice_process_scope",
                "target_id": process,
                "previous": "out_of_scope",
                "current": "in_scope",
            }
        )
        changes.append(
            {
                "target_kind": "aspice_process_capability",
                "target_id": process,
                "previous": "not_applicable",
                "current": f"CL{updated_targets.get(process)}",
            }
        )
    for process in sorted(previous_scope - updated_scope):
        changes.append(
            {
                "target_kind": "aspice_process_scope",
                "target_id": process,
                "previous": "in_scope",
                "current": "out_of_scope",
            }
        )
        changes.append(
            {
                "target_kind": "aspice_process_capability",
                "target_id": process,
                "previous": f"CL{previous_targets.get(process)}",
                "current": "not_applicable",
            }
        )

    for process in sorted(previous_scope & updated_scope):
        previous_target = previous_targets.get(process)
        updated_target = updated_targets.get(process)
        if previous_target != updated_target:
            changes.append(
                {
                    "target_kind": "aspice_process_capability",
                    "target_id": process,
                    "previous": f"CL{previous_target}",
                    "current": f"CL{updated_target}",
                }
            )
    return changes


def _normalize_evidence_refs(value: list[str] | str | None) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        candidates = value.replace(",", "\n").splitlines()
    else:
        candidates = [str(item) for item in value]
    return [candidate.strip() for candidate in candidates if candidate.strip()]


async def _record_aspice_tailoring_decisions(
    session: AsyncSession,
    *,
    project_id: str,
    actor_user_id: str,
    changes: list[dict[str, str]],
    rationale: str,
    evidence_refs: list[str],
) -> None:
    approved_at = datetime.now(UTC)
    decisions: list[TailoringDecision] = []
    for change in changes:
        decision = TailoringDecision(
            project_id=project_id,
            scope_type="project",
            scope_id=project_id,
            target_kind=change["target_kind"],
            target_id=change["target_id"],
            previous_applicability=change["previous"],
            tailored_applicability=change["current"],
            rationale=rationale,
            evidence_refs_json=evidence_refs,
            requested_by=actor_user_id,
            approved_by=actor_user_id,
            approved_at=approved_at,
            status="approved",
        )
        session.add(decision)
        decisions.append(decision)
    await session.flush()
    for decision in decisions:
        await record_event(
            session,
            event_type="tailoring.approved",
            project_id=project_id,
            actor_user_id=actor_user_id,
            payload={
                "tailoring_decision_id": decision.tailoring_decision_id,
                "target_kind": decision.target_kind,
                "target_id": decision.target_id,
                "previous": decision.previous_applicability,
                "current": decision.tailored_applicability,
            },
        )
    await record_event(
        session,
        event_type="project.aspice_tailoring_updated",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload={
            "tailoring_decision_ids": [
                decision.tailoring_decision_id for decision in decisions
            ],
            "changes": changes,
            "evidence_refs": evidence_refs,
        },
    )


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
