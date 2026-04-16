from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact
from aac_backend.models.projects import AssuranceProfile, TailoringDecision
from aac_backend.services.assurance_configuration_service import (
    MANDATORY_ARTEFACTS_BY_ASIL,
    default_assurance_configuration_for_asil,
    derive_profile_payload,
)

DEFAULT_PROFILE_IDS = (
    "ASIL_D_DEFAULT",
    "ASIL_C_DEFAULT",
    "ASIL_B_DEFAULT",
    "ASIL_A_DEFAULT",
    "QM_DEFAULT",
)


async def seed_default_profiles(session: AsyncSession) -> None:
    for profile_id in DEFAULT_PROFILE_IDS:
        existing = await session.get(AssuranceProfile, profile_id)
        classification = profile_id.replace("_DEFAULT", "")
        if existing is not None:
            existing.name = profile_id
            existing.classification = classification
            existing.inherits_from_profile_id = (
                "ASIL_D_DEFAULT" if profile_id != "ASIL_D_DEFAULT" else None
            )
            existing.profile_payload_json = default_profile_payload(classification)
            existing.status = "active"
            continue
        session.add(
            AssuranceProfile(
                profile_id=profile_id,
                project_id=None,
                name=profile_id,
                classification=classification,
                inherits_from_profile_id="ASIL_D_DEFAULT" if profile_id != "ASIL_D_DEFAULT" else None,
                profile_payload_json=default_profile_payload(classification),
                status="active",
            )
        )


def default_profile_payload(classification: str) -> dict:
    return derive_profile_payload(default_assurance_configuration_for_asil(classification))


async def evaluate_profile_applicability(
    session: AsyncSession,
    *,
    project_id: str,
    profile: AssuranceProfile,
) -> dict:
    payload = profile.profile_payload_json or {}
    artefact_classes = payload.get("artefact_classes") or {}
    active_artefact_types = set(
        await session.scalars(
            select(Artefact.artefact_type).where(
                Artefact.project_id == project_id,
                Artefact.deleted_at.is_(None),
            )
        )
    )
    tailored_not_applicable = {
        decision.target_id
        for decision in await session.scalars(
            select(TailoringDecision).where(
                TailoringDecision.project_id == project_id,
                TailoringDecision.status == "approved",
                TailoringDecision.tailored_applicability == "not_applicable",
            )
        )
        if decision.rationale and decision.evidence_refs_json
    }
    mandatory = {
        artefact_type
        for artefact_type, config in artefact_classes.items()
        if config.get("applicability") == "mandatory"
    }
    missing = sorted(mandatory - active_artefact_types - tailored_not_applicable)
    tailored = sorted(mandatory & tailored_not_applicable)
    present = sorted(mandatory & active_artefact_types)
    return {
        "profile_id": profile.profile_id,
        "classification": profile.classification,
        "mandatory_artefact_types": sorted(mandatory),
        "conditional_artefact_types": sorted(
            artefact_type
            for artefact_type, config in artefact_classes.items()
            if config.get("applicability") == "conditional"
        ),
        "optional_artefact_types": sorted(
            artefact_type
            for artefact_type, config in artefact_classes.items()
            if config.get("applicability") == "optional"
        ),
        "not_applicable_artefact_types": sorted(
            artefact_type
            for artefact_type, config in artefact_classes.items()
            if config.get("applicability") == "not_applicable"
        ),
        "visible_artefact_types": sorted(
            artefact_type
            for artefact_type, config in artefact_classes.items()
            if config.get("visible") is True
        ),
        "enabled_rules": sorted(
            rule_id
            for rule_id, config in (payload.get("rules") or {}).items()
            if config.get("enabled") is True
        ),
        "disabled_rules": sorted(
            rule_id
            for rule_id, config in (payload.get("rules") or {}).items()
            if config.get("enabled") is False or config.get("severity") == "disabled"
        ),
        "assurance_configuration": payload.get("project_assurance_configuration", {}),
        "present_mandatory_artefact_types": present,
        "tailored_not_applicable_artefact_types": tailored,
        "missing_mandatory_artefact_types": missing,
        "is_applicable": not missing,
    }


def clone_profile_payload(payload: dict, updates: dict) -> dict:
    clone = deepcopy(payload or {})
    for key, value in updates.items():
        if key == "profile_id":
            continue
        clone[key] = value
    return clone


def _mandatory_types_for(classification: str) -> set[str]:
    return set(MANDATORY_ARTEFACTS_BY_ASIL.get(classification, MANDATORY_ARTEFACTS_BY_ASIL["ASIL_D"]))
