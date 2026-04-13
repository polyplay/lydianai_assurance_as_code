from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.api.dependencies import (
    CurrentUser,
    get_current_user,
    global_role_dependency,
    project_role_dependency,
)
from aac_backend.database import get_session
from aac_backend.models.access import ProjectMembership, Role, User
from aac_backend.models.projects import AssuranceProfile, Project, ProjectConfiguration, TailoringDecision
from aac_backend.models.standards import ArtefactStandardMapping, StandardsReference
from aac_backend.schemas.common import ApiEnvelope
from aac_backend.schemas.domain import ProjectCreate, ProjectRead
from aac_backend.services.project_service import archive_project, create_project
from aac_backend.services.profile_service import (
    clone_profile_payload,
    evaluate_profile_applicability,
    seed_default_profiles,
)

router = APIRouter(tags=["projects"])


@router.get("/projects", response_model=ApiEnvelope)
async def list_projects(
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    projects = list(await session.scalars(select(Project).where(Project.status != "deleted")))
    return ApiEnvelope(data=[ProjectRead.model_validate(project) for project in projects])


@router.post("/projects", response_model=ApiEnvelope)
async def create_project_endpoint(
    payload: ProjectCreate,
    current: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    try:
        project = await create_project(session, payload, current.user.user_id)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    await session.commit()
    return ApiEnvelope(data=ProjectRead.model_validate(project))


@router.get("/projects/{project_id}", response_model=ApiEnvelope)
async def get_project(
    project_id: str,
    _: CurrentUser = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiEnvelope(data=ProjectRead.model_validate(project))


@router.put("/projects/{project_id}", response_model=ApiEnvelope)
async def update_project(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.name = payload.get("name", project.name)
    project.description = payload.get("description", project.description)
    project.active_profile_id = payload.get("active_profile_id", project.active_profile_id)
    project.status = payload.get("status", project.status)
    await session.commit()
    return ApiEnvelope(data=ProjectRead.model_validate(project))


@router.get("/projects/{project_id}/status", response_model=ApiEnvelope)
async def project_status(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return ApiEnvelope(
        data={
            "project_id": project.project_id,
            "status": project.status,
            "active_profile_id": project.active_profile_id,
        }
    )


@router.post("/projects/{project_id}/archive", response_model=ApiEnvelope)
async def archive_project_endpoint(
    project_id: str,
    current: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    await archive_project(session, project, current.user.user_id)
    await session.commit()
    return ApiEnvelope(data=ProjectRead.model_validate(project))


@router.delete("/projects/{project_id}", response_model=ApiEnvelope)
async def delete_project(
    project_id: str,
    current: CurrentUser = Depends(global_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    project = await session.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    project.status = "deleted"
    await session.commit()
    return ApiEnvelope(data=ProjectRead.model_validate(project))


@router.get("/projects/{project_id}/members", response_model=ApiEnvelope)
async def list_members(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    rows = await session.execute(
        select(ProjectMembership, User, Role)
        .join(User, User.user_id == ProjectMembership.user_id)
        .join(Role, Role.role_id == ProjectMembership.role_id)
        .where(ProjectMembership.project_id == project_id)
    )
    return ApiEnvelope(
        data=[
            {
                "user_id": user.user_id,
                "username": user.username,
                "role": role.role_name,
            }
            for _, user, role in rows.all()
        ]
    )


@router.post("/projects/{project_id}/members", response_model=ApiEnvelope)
async def add_member(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    role = await session.scalar(select(Role).where(Role.role_name == payload["role"]))
    user = await session.get(User, payload["user_id"])
    if not role or not user:
        raise HTTPException(status_code=404, detail="User or role not found")
    membership = ProjectMembership(
        project_id=project_id,
        user_id=user.user_id,
        role_id=role.role_id,
        created_at=datetime.now(UTC),
    )
    session.add(membership)
    await session.commit()
    return ApiEnvelope(data={"project_id": project_id, "user_id": user.user_id, "role": role.role_name})


@router.delete("/projects/{project_id}/members/{user_id}", response_model=ApiEnvelope)
async def remove_member(
    project_id: str,
    user_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    memberships = list(
        await session.scalars(
            select(ProjectMembership).where(
                ProjectMembership.project_id == project_id,
                ProjectMembership.user_id == user_id,
            )
        )
    )
    for membership in memberships:
        await session.delete(membership)
    await session.commit()
    return ApiEnvelope(data={"project_id": project_id, "user_id": user_id, "removed": len(memberships)})


@router.get("/projects/{project_id}/config", response_model=ApiEnvelope)
async def get_config(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    config = await session.scalar(
        select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
    )
    if not config:
        raise HTTPException(status_code=404, detail="Project config not found")
    return ApiEnvelope(data=_config_data(config))


@router.put("/projects/{project_id}/config", response_model=ApiEnvelope)
async def update_config(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    config = await session.scalar(
        select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
    )
    if not config:
        raise HTTPException(status_code=404, detail="Project config not found")
    config.version_update_mode = payload.get("version_update_mode", config.version_update_mode)
    config.sphinx_source_root = payload.get("sphinx_source_root", config.sphinx_source_root)
    config.baseline_policy_json = payload.get("baseline_policy", config.baseline_policy_json)
    config.validation_policy_json = payload.get("validation_policy", config.validation_policy_json)
    config.reporting_policy_json = payload.get("reporting_policy", config.reporting_policy_json)
    await session.commit()
    return ApiEnvelope(data=_config_data(config))


@router.get("/projects/{project_id}/profiles", response_model=ApiEnvelope)
async def list_profiles(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    await seed_default_profiles(session)
    profiles = list(
        await session.scalars(
            select(AssuranceProfile).where(
                (AssuranceProfile.project_id.is_(None)) | (AssuranceProfile.project_id == project_id),
                AssuranceProfile.status == "active",
            )
        )
    )
    await session.commit()
    return ApiEnvelope(data=[_profile_data(profile) for profile in profiles])


@router.post("/projects/{project_id}/profiles", response_model=ApiEnvelope)
async def create_profile(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    source_profile_id = payload.get("inherits_from_profile_id") or payload.get("inherits_from")
    source_payload = {}
    if source_profile_id:
        source = await session.get(AssuranceProfile, source_profile_id)
        if not source:
            raise HTTPException(status_code=404, detail="Source profile not found")
        source_payload = source.profile_payload_json
    profile = AssuranceProfile(
        project_id=project_id,
        name=payload["name"],
        classification=payload.get("classification", "ASIL_D"),
        inherits_from_profile_id=source_profile_id,
        profile_payload_json=clone_profile_payload(source_payload, payload.get("profile_payload", {})),
        status="active",
    )
    session.add(profile)
    await session.commit()
    return ApiEnvelope(data=_profile_data(profile))


@router.get("/projects/{project_id}/profiles/{profile_id}", response_model=ApiEnvelope)
async def get_profile(
    project_id: str,
    profile_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    profile = await _get_profile_or_404(session, project_id, profile_id)
    return ApiEnvelope(data=_profile_data(profile))


@router.put("/projects/{project_id}/profiles/{profile_id}", response_model=ApiEnvelope)
async def update_profile(
    project_id: str,
    profile_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    profile = await _get_profile_or_404(session, project_id, profile_id)
    if profile.project_id is None:
        raise HTTPException(status_code=409, detail="Default profiles cannot be modified")
    profile.name = payload.get("name", profile.name)
    profile.classification = payload.get("classification", profile.classification)
    profile.profile_payload_json = payload.get("profile_payload", profile.profile_payload_json)
    profile.status = payload.get("status", profile.status)
    await session.commit()
    return ApiEnvelope(data=_profile_data(profile))


@router.post("/projects/{project_id}/profiles/{profile_id}/evaluate", response_model=ApiEnvelope)
async def evaluate_profile(
    project_id: str,
    profile_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    profile = await _get_profile_or_404(session, project_id, profile_id)
    return ApiEnvelope(data=await evaluate_profile_applicability(session, project_id=project_id, profile=profile))


@router.get("/projects/{project_id}/standards-references", response_model=ApiEnvelope)
async def list_standards_references(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    _ = project_id
    refs = list(await session.scalars(select(StandardsReference)))
    return ApiEnvelope(data=[_standards_reference_data(ref) for ref in refs])


@router.post("/projects/{project_id}/standards-references", response_model=ApiEnvelope)
async def create_standards_reference(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    _ = project_id
    ref = StandardsReference(
        standard=payload["standard"],
        edition=payload.get("edition", ""),
        part_or_process=payload.get("part_or_process", ""),
        clause_or_process_id=payload["clause_or_process_id"],
        title=payload.get("title", ""),
        reference_type=payload.get("reference_type", "requirement"),
        source_access=payload.get("source_access", "public"),
        review_status=payload.get("review_status", "draft_public_reference"),
    )
    session.add(ref)
    await session.commit()
    return ApiEnvelope(data=_standards_reference_data(ref))


@router.put("/projects/{project_id}/standards-references/{standards_reference_id}", response_model=ApiEnvelope)
async def update_standards_reference(
    project_id: str,
    standards_reference_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    _ = project_id
    ref = await session.get(StandardsReference, standards_reference_id)
    if not ref:
        raise HTTPException(status_code=404, detail="Standards reference not found")
    for field in (
        "standard",
        "edition",
        "part_or_process",
        "clause_or_process_id",
        "title",
        "reference_type",
        "source_access",
        "review_status",
    ):
        if field in payload:
            setattr(ref, field, payload[field])
    await session.commit()
    return ApiEnvelope(data=_standards_reference_data(ref))


@router.get("/projects/{project_id}/standards-mappings", response_model=ApiEnvelope)
async def list_standards_mappings(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    _ = project_id
    mappings = list(await session.scalars(select(ArtefactStandardMapping)))
    return ApiEnvelope(data=[_standards_mapping_data(mapping) for mapping in mappings])


@router.put("/projects/{project_id}/standards-mappings", response_model=ApiEnvelope)
async def upsert_standards_mapping(
    project_id: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    _ = project_id
    artefact_type = payload["artefact_type"]
    standards_reference_id = payload["standards_reference_id"]
    mapping = await session.get(ArtefactStandardMapping, (artefact_type, standards_reference_id))
    if mapping is None:
        mapping = ArtefactStandardMapping(
            artefact_type=artefact_type,
            standards_reference_id=standards_reference_id,
        )
        session.add(mapping)
    mapping.required_content_json = payload.get("required_content", mapping.required_content_json)
    mapping.review_expectation = payload.get("review_expectation", mapping.review_expectation)
    mapping.independence_expectation = payload.get(
        "independence_expectation",
        mapping.independence_expectation,
    )
    mapping.verification_method_expectation = payload.get(
        "verification_method_expectation",
        mapping.verification_method_expectation,
    )
    await session.commit()
    return ApiEnvelope(data=_standards_mapping_data(mapping))


@router.get("/projects/{project_id}/schemas", response_model=ApiEnvelope)
async def list_schemas(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
) -> ApiEnvelope:
    return ApiEnvelope(data={"project_id": project_id, "schema_mode": "generic_artefact_payload"})


@router.get("/projects/{project_id}/schemas/{artefact_type}", response_model=ApiEnvelope)
async def get_schema(
    project_id: str,
    artefact_type: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
) -> ApiEnvelope:
    return ApiEnvelope(
        data={
            "project_id": project_id,
            "artefact_type": artefact_type,
            "enabled_fields": ["base", "payload"],
            "mandatory_fields": ["artefact_type", "title", "source.source_object_id"],
        }
    )


@router.put("/projects/{project_id}/schemas/{artefact_type}", response_model=ApiEnvelope)
async def tailor_schema(
    project_id: str,
    artefact_type: str,
    payload: dict,
    _: CurrentUser = Depends(project_role_dependency("admin")),
) -> ApiEnvelope:
    return ApiEnvelope(data={"project_id": project_id, "artefact_type": artefact_type, **payload})


@router.post("/projects/{project_id}/tailoring-decisions", response_model=ApiEnvelope)
async def create_tailoring_decision(
    project_id: str,
    payload: dict,
    current: CurrentUser = Depends(project_role_dependency("admin", "project_lead")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    decision = TailoringDecision(
        project_id=project_id,
        scope_type=payload["scope_type"],
        scope_id=payload["scope_id"],
        target_kind=payload["target_kind"],
        target_id=payload["target_id"],
        previous_applicability=payload.get("previous_applicability", "mandatory"),
        tailored_applicability=payload["tailored_applicability"],
        rationale=payload["rationale"],
        evidence_refs_json=payload.get("evidence_refs", []),
        requested_by=current.user.user_id,
        approved_by=current.user.user_id,
        approved_at=datetime.now(UTC),
        status="approved",
    )
    session.add(decision)
    await session.commit()
    return ApiEnvelope(data=_tailoring_data(decision))


@router.get("/projects/{project_id}/tailoring-decisions", response_model=ApiEnvelope)
async def list_tailoring_decisions(
    project_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin", "project_lead", "quality_engineer", "user")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    decisions = list(
        await session.scalars(select(TailoringDecision).where(TailoringDecision.project_id == project_id))
    )
    return ApiEnvelope(data=[_tailoring_data(decision) for decision in decisions])


@router.post(
    "/projects/{project_id}/tailoring-decisions/{tailoring_decision_id}/revoke",
    response_model=ApiEnvelope,
)
async def revoke_tailoring_decision(
    project_id: str,
    tailoring_decision_id: str,
    _: CurrentUser = Depends(project_role_dependency("admin")),
    session: AsyncSession = Depends(get_session),
) -> ApiEnvelope:
    decision = await session.get(TailoringDecision, tailoring_decision_id)
    if not decision or decision.project_id != project_id:
        raise HTTPException(status_code=404, detail="Tailoring decision not found")
    decision.status = "obsolete"
    await session.commit()
    return ApiEnvelope(data=_tailoring_data(decision))


def _config_data(config: ProjectConfiguration) -> dict:
    return {
        "project_config_id": config.project_config_id,
        "project_id": config.project_id,
        "version_update_mode": config.version_update_mode,
        "sphinx_source_root": config.sphinx_source_root,
        "baseline_policy": config.baseline_policy_json,
        "validation_policy": config.validation_policy_json,
        "reporting_policy": config.reporting_policy_json,
    }


def _tailoring_data(decision: TailoringDecision) -> dict:
    return {
        "tailoring_decision_id": decision.tailoring_decision_id,
        "project_id": decision.project_id,
        "target_kind": decision.target_kind,
        "target_id": decision.target_id,
        "tailored_applicability": decision.tailored_applicability,
        "status": decision.status,
        "rationale": decision.rationale,
        "evidence_refs": decision.evidence_refs_json,
    }


async def _get_profile_or_404(
    session: AsyncSession,
    project_id: str,
    profile_id: str,
) -> AssuranceProfile:
    await seed_default_profiles(session)
    profile = await session.get(AssuranceProfile, profile_id)
    if not profile or (profile.project_id is not None and profile.project_id != project_id):
        raise HTTPException(status_code=404, detail="Assurance profile not found")
    return profile


def _profile_data(profile: AssuranceProfile) -> dict:
    return {
        "profile_id": profile.profile_id,
        "project_id": profile.project_id,
        "name": profile.name,
        "classification": profile.classification,
        "inherits_from_profile_id": profile.inherits_from_profile_id,
        "status": profile.status,
        "profile_payload": profile.profile_payload_json,
    }


def _standards_reference_data(ref: StandardsReference) -> dict:
    return {
        "standards_reference_id": ref.standards_reference_id,
        "standard": ref.standard,
        "edition": ref.edition,
        "part_or_process": ref.part_or_process,
        "clause_or_process_id": ref.clause_or_process_id,
        "title": ref.title,
        "reference_type": ref.reference_type,
        "source_access": ref.source_access,
        "review_status": ref.review_status,
    }


def _standards_mapping_data(mapping: ArtefactStandardMapping) -> dict:
    return {
        "artefact_type": mapping.artefact_type,
        "standards_reference_id": mapping.standards_reference_id,
        "required_content": mapping.required_content_json,
        "review_expectation": mapping.review_expectation,
        "independence_expectation": mapping.independence_expectation,
        "verification_method_expectation": mapping.verification_method_expectation,
    }
