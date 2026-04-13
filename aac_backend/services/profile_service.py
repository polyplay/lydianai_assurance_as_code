from copy import deepcopy

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact
from aac_backend.models.projects import AssuranceProfile, TailoringDecision
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.services.validation_service import (
    MANDATORY_ASIL_D_ARTEFACT_TYPES,
    RELATIONSHIP_TYPES,
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
        if existing is not None:
            continue
        classification = profile_id.replace("_DEFAULT", "")
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
    mandatory_types = sorted(_mandatory_types_for(classification))
    return {
        "project_classification": classification,
        "artefact_classes": {
            artefact_type: {
                "applicability": "mandatory",
                "required_status_for_baseline": ["approved", "released"],
                "required_status_for_release": ["released"],
                "evidence_required": True,
                "tailoring_allowed": True,
                "tailoring_approval_role": "project_lead",
            }
            for artefact_type in mandatory_types
        },
        "relationship_types": {
            relationship_type: {
                "applicability": "optional",
                "source_types": [],
                "target_types": [],
                "min_count": None,
            }
            for relationship_type in sorted(RELATIONSHIP_TYPES)
        },
        "rules": {
            rule_id: {
                "enabled": True,
                "severity": rule.severity,
                "execution_modes": list(rule.execution_modes),
                "blocking_contexts": list(rule.blocking_contexts),
                "tailoring_allowed": rule.severity != "critical",
            }
            for rule_id, rule in RULE_CATALOG.items()
        },
        "reports": {
            "traceability_matrix": {"applicability": "mandatory"},
            "validation_summary": {"applicability": "mandatory"},
            "baseline_comparison": {"applicability": "mandatory"},
        },
    }


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
    if classification in {"ASIL_D", "ASIL_C"}:
        return set(MANDATORY_ASIL_D_ARTEFACT_TYPES)
    if classification == "ASIL_B":
        return set(MANDATORY_ASIL_D_ARTEFACT_TYPES) - {
            "ConfirmationMeasureRecord",
            "QualityAssuranceRecord",
        }
    if classification == "ASIL_A":
        return {
            "SoftwareRequirement",
            "SoftwareArchitecture",
            "SoftwareComponent",
            "ImplementationItem",
            "BuildConfiguration",
            "TestSpecification",
            "TestCase",
            "TestResult",
            "RequirementsCoverageRecord",
            "ChangeSet",
        }
    return {"SoftwareRequirement", "ImplementationItem", "TestCase", "TestResult"}
