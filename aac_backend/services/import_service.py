from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship, RelationshipRevision
from aac_backend.models.imports import ImportRun, ImportRunItem
from aac_backend.models.jobs import Job
from aac_backend.repositories.domain import ArtefactRepository
from aac_backend.repositories.domain import RelationshipRepository
from aac_backend.schemas.domain import (
    ArtefactCreate,
    ArtefactSource,
    ArtefactUpdate,
    ImportStart,
    RelationshipCreate,
)
from aac_backend.services.artefact_service import (
    create_artefact,
    create_relationship,
    fingerprint,
    obsolete_artefact,
    update_artefact,
)
from aac_backend.services.event_service import record_event
from aac_backend.services.validation_service import run_validation


TYPE_FIELD = "type"
ID_FIELD = "id"
SPHINX_TYPE_TO_ARTEFACT_TYPE = {
    "project_scope": "ProjectScope",
    "aspice_scope_decision": "ASPICEScopeDecision",
    "safety_plan": "SafetyPlan",
    "sw_safety_plan": "SoftwareSafetyPlan",
    "safety_case": "SafetyCase",
    "system_safety_concept": "SystemSafetyConcept",
    "verification_plan": "VerificationPlan",
    "config_mgmt_plan": "ConfigurationManagementPlan",
    "change_record": "ChangeManagementRecord",
    "confirmation_record": "ConfirmationMeasureRecord",
    "dev_environment": "DevelopmentEnvironmentRecord",
    "quality_assurance": "QualityAssuranceRecord",
    "item_def": "ItemDefinition",
    "hara_ref": "HazardAnalysisRiskAssessment",
    "safety_goal": "SafetyGoal",
    "fsr": "FunctionalSafetyRequirement",
    "tsr": "TechnicalSafetyRequirement",
    "sw_safety_req": "SoftwareSafetyRequirement",
    "sw_req": "SoftwareRequirement",
    "derived_sw_req": "DerivedSoftwareRequirement",
    "assumption": "Assumption",
    "req_review": "RequirementReviewRecord",
    "sw_arch": "SoftwareArchitecture",
    "sw_comp": "SoftwareComponent",
    "sw_interface": "InterfaceContract",
    "ag_contract": "AssumptionGuaranteeContract",
    "safeguard": "Safeguard",
    "partitioning_element": "SoftwarePartitioningElement",
    "resource_constraint": "ResourceUsageConstraint",
    "arch_review": "ArchitectureReviewRecord",
    "sw_unit": "SoftwareUnit",
    "unit_design": "SoftwareUnitDesign",
    "impl_item": "ImplementationItem",
    "source_ref": "SourceCodeReference",
    "build_config": "BuildConfiguration",
    "toolchain_config": "CompilerToolchainConfiguration",
    "impl_review": "ImplementationReviewRecord",
    "static_analysis": "StaticAnalysisResult",
    "coding_compliance": "CodingGuidelineComplianceRecord",
    "test_spec": "TestSpecification",
    "test_case": "TestCase",
    "test_procedure": "TestProcedure",
    "test_environment": "TestEnvironment",
    "test_result": "TestResult",
    "coverage_result": "CoverageResult",
    "requirements_coverage": "RequirementsCoverageRecord",
    "safety_analysis": "SafetyAnalysis",
    "interface_risk": "InterfaceRiskAnalysis",
    "ffi_argument": "FreedomFromInterferenceArgument",
    "asil_decomposition": "ASILDecompositionArgument",
    "assurance_argument": "AssuranceArgument",
    "tara": "ThreatAnalysisRiskAssessment",
    "cybersecurity_requirement": "CybersecurityRequirement",
    "cybersecurity_evidence": "CybersecurityManagementEvidence",
    "cybersecurity_interface": "CybersecurityInterfaceEvidence",
    "sums_evidence": "SoftwareUpdateManagementEvidence",
    "software_version": "SoftwareVersionRecord",
    "update_campaign": "UpdateCampaign",
    "update_integrity": "UpdateIntegrityEvidence",
    "sbom": "SoftwareBillOfMaterials",
    "test_risk": "TestRiskAssessment",
    "tool_inventory": "ToolInventoryItem",
    "tool_confidence": "ToolConfidenceAssessment",
    "tool_qualification": "ToolQualificationEvidence",
    "process_compliance": "ProcessComplianceRecord",
    "defect_record": "DefectRecord",
    "change_request": "ChangeRequest",
    "evidence_ref": "EvidenceReference",
}
LINK_TO_RELATIONSHIP = {
    "allocates_to": "allocates_to",
    "satisfies": "satisfies",
    "depends_on": "depends_on",
    "interacts_via": "interacts_via",
    "constrains": "constrains",
    "assumes": "assumes",
    "guarantees": "guarantees",
    "protects": "protects",
    "implements": "implements",
    "verifies": "verifies",
    "produces_result_for": "produces_result_for",
    "derived_from": "derives_from",
    "derives_from": "derives_from",
    "references": "references",
}


async def import_sphinx_needs(
    session: AsyncSession,
    project_id: str,
    data: ImportStart,
    actor_user_id: str,
) -> ImportRun:
    import_run = ImportRun(
        project_id=project_id,
        source_root=data.source_root,
        state="parsed",
        version_update_mode=data.version_update_mode or "ask_user",
        submitted_by=actor_user_id,
        submitted_at=datetime.now(UTC),
        summary_json={},
        diagnostics_json=[],
    )
    session.add(import_run)
    await session.flush()

    repo = ArtefactRepository(session)
    created = changed = unchanged = waiting = errors = deleted = type_mismatches = conflicts = 0
    seen_source_keys: set[tuple[str, str]] = set()
    imported_documents: set[str] = set()
    raw_entries: list[dict] = []

    for raw_need in data.sphinx_needs:
        try:
            source_object_id = str(raw_need[ID_FIELD])
            artefact_type = _canonical_artefact_type(raw_need)
            source_document = str(raw_need.get("source_document") or raw_need.get("docname") or "")
            payload = _normalize_payload(raw_need, artefact_type)
            base_revision_id = raw_need.get("_aac_base_revision_id") or payload.get("_aac_base_revision_id")
            title = str(raw_need.get("title") or source_object_id)
            description = str(raw_need.get("description") or raw_need.get("content") or "")
        except Exception as exc:
            errors += 1
            import_run.diagnostics_json.append({"level": "error", "message": str(exc), "raw": raw_need})
            continue

        seen_source_keys.add((source_document, source_object_id))
        imported_documents.add(source_document)
        raw_entries.append(
            {
                "raw_need": raw_need,
                "source_object_id": source_object_id,
                "source_document": source_document,
            }
        )
        existing = await repo.by_source_identity(project_id, source_document, source_object_id)
        proposed_fingerprint = fingerprint(payload)
        if existing is None:
            try:
                artefact = await create_artefact(
                    session,
                    project_id,
                    ArtefactCreate(
                        artefact_type=artefact_type,
                        title=title,
                        description=description,
                        source=ArtefactSource(
                            source_kind="sphinx",
                            source_tool="sphinx-needs",
                            source_object_id=source_object_id,
                            source_document=source_document,
                        ),
                        payload=payload,
                    ),
                    actor_user_id,
                )
            except ValueError as exc:
                errors += 1
                import_run.diagnostics_json.append(
                    {
                        "level": "error",
                        "classification": "artefact_rejected",
                        "source_object_id": source_object_id,
                        "source_document": source_document,
                        "message": str(exc),
                    }
                )
                continue
            created += 1
            session.add(
                _item(
                    import_run,
                    source_object_id,
                    source_document,
                    artefact_type,
                    "new",
                    artefact.artefact_id,
                    proposed_fingerprint,
                    payload,
                )
            )
            continue

        if existing.artefact_type != artefact_type:
            type_mismatches += 1
            item = _item(
                import_run,
                source_object_id,
                source_document,
                artefact_type,
                "type_mismatch",
                existing.artefact_id,
                proposed_fingerprint,
                payload,
            )
            item.previous_fingerprint = existing.current_fingerprint
            item.current_revision_id = existing.current_revision_id
            item.decision_status = "rejected"
            session.add(item)
            import_run.diagnostics_json.append(
                {
                    "level": "error",
                    "classification": "type_mismatch",
                    "source_object_id": source_object_id,
                    "source_document": source_document,
                    "stored_type": existing.artefact_type,
                    "imported_type": artefact_type,
                }
            )
            continue

        if base_revision_id and existing.current_revision_id != base_revision_id:
            conflicts += 1
            item = _item(
                import_run,
                source_object_id,
                source_document,
                artefact_type,
                "conflict",
                existing.artefact_id,
                proposed_fingerprint,
                payload,
            )
            item.previous_fingerprint = existing.current_fingerprint
            item.current_revision_id = existing.current_revision_id
            if import_run.version_update_mode == "automatic_new_version":
                try:
                    await update_artefact(
                        session,
                        existing,
                        ArtefactUpdate(
                            title=title,
                            description=description,
                            payload=payload,
                            change_reason="sphinx import stale base accepted automatically",
                        ),
                        actor_user_id,
                    )
                except ValueError as exc:
                    errors += 1
                    item.decision_status = "rejected"
                    session.add(item)
                    import_run.diagnostics_json.append(
                        {
                            "level": "error",
                            "classification": "artefact_rejected",
                            "source_object_id": source_object_id,
                            "source_document": source_document,
                            "message": str(exc),
                        }
                    )
                    continue
                item.new_revision_id = existing.current_revision_id
                item.decision_status = "automatic"
                changed += 1
            else:
                item.decision_status = "pending"
                waiting += 1
                import_run.state = "waiting_for_user"
            session.add(item)
            import_run.diagnostics_json.append(
                {
                    "level": "warning",
                    "classification": "conflict",
                    "source_object_id": source_object_id,
                    "source_document": source_document,
                    "base_revision_id": base_revision_id,
                    "current_revision_id": existing.current_revision_id,
                }
            )
            continue

        if existing.current_fingerprint == proposed_fingerprint:
            unchanged += 1
            session.add(
                _item(
                    import_run,
                    source_object_id,
                    source_document,
                    artefact_type,
                    "unchanged",
                    existing.artefact_id,
                    proposed_fingerprint,
                    payload,
                )
            )
            continue

        item = _item(
            import_run,
            source_object_id,
            source_document,
            artefact_type,
            "changed",
            existing.artefact_id,
            proposed_fingerprint,
            payload,
        )
        item.previous_fingerprint = existing.current_fingerprint
        item.current_revision_id = existing.current_revision_id
        if import_run.version_update_mode == "automatic_new_version":
            try:
                await update_artefact(
                    session,
                    existing,
                    ArtefactUpdate(title=title, description=description, payload=payload, change_reason="sphinx import"),
                    actor_user_id,
                )
            except ValueError as exc:
                errors += 1
                item.decision_status = "rejected"
                session.add(item)
                import_run.diagnostics_json.append(
                    {
                        "level": "error",
                        "classification": "artefact_rejected",
                        "source_object_id": source_object_id,
                        "source_document": source_document,
                        "message": str(exc),
                    }
                )
                continue
            item.new_revision_id = existing.current_revision_id
            item.decision_status = "automatic"
            changed += 1
        else:
            item.decision_status = "pending"
            import_run.state = "waiting_for_user"
            waiting += 1
        session.add(item)

    if imported_documents:
        existing_sphinx_artefacts = list(
            await session.scalars(
                select(Artefact).where(
                    Artefact.project_id == project_id,
                    Artefact.source_kind == "sphinx",
                    Artefact.source_document.in_(imported_documents),
                    Artefact.deleted_at.is_(None),
                )
            )
        )
        for artefact in existing_sphinx_artefacts:
            key = (artefact.source_document, artefact.source_object_id)
            if key in seen_source_keys:
                continue
            await _soft_delete_active_relationships_for_artefact(session, artefact, actor_user_id)
            await obsolete_artefact(session, artefact, actor_user_id)
            deleted += 1
            item = _item(
                import_run,
                artefact.source_object_id,
                artefact.source_document,
                artefact.artefact_type,
                "deleted",
                artefact.artefact_id,
                artefact.current_fingerprint or "",
                artefact.payload_json,
            )
            item.current_revision_id = artefact.current_revision_id
            item.previous_fingerprint = artefact.current_fingerprint
            item.decision_status = "automatic"
            session.add(item)

    relationships_created, relationship_errors = await _import_relationships(
        session,
        project_id,
        raw_entries,
        actor_user_id,
        import_run.diagnostics_json,
    )
    errors += relationship_errors

    if waiting:
        final_state = "waiting_for_user"
    elif errors or type_mismatches:
        final_state = "completed_with_errors"
    else:
        final_state = "completed"
    import_run.state = final_state
    import_run.completed_at = None if waiting else datetime.now(UTC)
    import_run.summary_json = {
        "created": created,
        "changed": changed,
        "unchanged": unchanged,
        "waiting_for_user": waiting,
        "errors": errors,
        "deleted": deleted,
        "type_mismatches": type_mismatches,
        "conflicts": conflicts,
        "relationships_created": relationships_created,
    }
    if final_state.startswith("completed"):
        validation_job = Job(
            project_id=project_id,
            job_type="validation_run",
            state="running",
            submitted_by=actor_user_id,
            submitted_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        session.add(validation_job)
        await session.flush()
        validation_run = await run_validation(
            session,
            project_id,
            actor_user_id,
            scope={"type": "project", "trigger": "sphinx_import", "import_run_id": import_run.import_run_id},
        )
        validation_job.state = "completed"
        validation_job.completed_at = datetime.now(UTC)
        validation_job.progress_percent = 100
        validation_job.result_ref_json = {
            "resource_type": "ValidationRun",
            "resource_id": validation_run.validation_run_id,
        }
        import_run.summary_json["validation_job_id"] = validation_job.job_id
        import_run.summary_json["validation_run_id"] = validation_run.validation_run_id
    await record_event(
        session,
        event_type="import.completed" if final_state.startswith("completed") else "import.waiting_for_user",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=import_run.summary_json,
    )
    return import_run


def _canonical_artefact_type(raw_need: dict) -> str:
    raw_type = str(raw_need.get(TYPE_FIELD) or raw_need.get("artefact_type"))
    return SPHINX_TYPE_TO_ARTEFACT_TYPE.get(raw_type, raw_type)


def _normalize_payload(raw_need: dict, artefact_type: str) -> dict:
    payload = dict(raw_need.get("payload") or raw_need)
    if "content" in raw_need and "statement" not in payload:
        payload["statement"] = raw_need["content"]
    if "asil" in raw_need and "asil_level" not in payload:
        payload["asil_level"] = raw_need["asil"]
    if "verification_method" in raw_need and "verification_intent" not in payload:
        payload["verification_intent"] = {"methods": _as_list(raw_need["verification_method"])}
    if artefact_type == "InterfaceContract":
        if "source_component_id" in payload and "source_component" not in payload:
            payload["source_component"] = payload["source_component_id"]
        if "destination_component_id" in payload and "destination_component" not in payload:
            payload["destination_component"] = payload["destination_component_id"]
        if "data_elements" in payload and "payload_definition" not in payload:
            payload["payload_definition"] = payload["data_elements"]
    if artefact_type == "SoftwareComponent" and "criticality_classification" in payload and "classification" not in payload:
        payload["classification"] = payload["criticality_classification"]
    payload["raw_sphinx_need"] = raw_need
    return payload


def _as_list(value) -> list:
    if isinstance(value, list):
        return value
    if value in (None, ""):
        return []
    return [value]


async def _import_relationships(
    session: AsyncSession,
    project_id: str,
    raw_entries: list[dict],
    actor_user_id: str,
    diagnostics: list,
) -> tuple[int, int]:
    created = 0
    errors = 0
    for entry in raw_entries:
        source = await _artefact_by_source_object_id(
            session,
            project_id,
            entry["source_object_id"],
            entry["source_document"],
        )
        if source is None:
            continue
        raw_need = entry["raw_need"]
        for link_name, relationship_type in LINK_TO_RELATIONSHIP.items():
            for target_ref in _as_list(raw_need.get(link_name)):
                target = await _artefact_by_source_object_id(
                    session,
                    project_id,
                    str(target_ref),
                    entry["source_document"],
                )
                if target is None:
                    errors += 1
                    diagnostics.append(
                        {
                            "level": "warning",
                            "classification": "relationship_target_missing",
                            "source_object_id": entry["source_object_id"],
                            "target_ref": target_ref,
                            "relationship_type": relationship_type,
                        }
                    )
                    continue
                if await _relationship_exists(
                    session,
                    project_id,
                    source.artefact_id,
                    target.artefact_id,
                    relationship_type,
                ):
                    continue
                try:
                    await create_relationship(
                        session,
                        project_id,
                        RelationshipCreate(
                            relationship_type=relationship_type,
                            source_artefact_id=source.artefact_id,
                            target_artefact_id=target.artefact_id,
                            payload={"source": "sphinx-needs", "link_name": link_name},
                        ),
                        actor_user_id,
                    )
                    created += 1
                except ValueError as exc:
                    errors += 1
                    diagnostics.append(
                        {
                            "level": "warning",
                            "classification": "relationship_rejected",
                            "source_object_id": entry["source_object_id"],
                            "target_ref": target_ref,
                            "relationship_type": relationship_type,
                            "message": str(exc),
                        }
                    )
    return created, errors


async def _artefact_by_source_object_id(
    session: AsyncSession,
    project_id: str,
    source_object_id: str,
    preferred_source_document: str,
) -> Artefact | None:
    artefact = await session.scalar(
        select(Artefact).where(
            Artefact.project_id == project_id,
            Artefact.source_object_id == source_object_id,
            Artefact.source_document == preferred_source_document,
            Artefact.deleted_at.is_(None),
        )
    )
    if artefact is not None:
        return artefact
    return await session.scalar(
        select(Artefact).where(
            Artefact.project_id == project_id,
            Artefact.source_object_id == source_object_id,
            Artefact.deleted_at.is_(None),
        )
    )


async def _relationship_exists(
    session: AsyncSession,
    project_id: str,
    source_artefact_id: str,
    target_artefact_id: str,
    relationship_type: str,
) -> bool:
    existing = await session.scalar(
        select(Relationship.relationship_id).where(
            Relationship.project_id == project_id,
            Relationship.source_artefact_id == source_artefact_id,
            Relationship.target_artefact_id == target_artefact_id,
            Relationship.relationship_type == relationship_type,
            Relationship.deleted_at.is_(None),
        )
    )
    return existing is not None


async def _soft_delete_active_relationships_for_artefact(
    session: AsyncSession,
    artefact: Artefact,
    actor_user_id: str,
) -> None:
    relationships = list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == artefact.project_id,
                Relationship.deleted_at.is_(None),
                (
                    (Relationship.source_artefact_id == artefact.artefact_id)
                    | (Relationship.target_artefact_id == artefact.artefact_id)
                ),
            )
        )
    )
    repo = RelationshipRepository(session)
    for relationship in relationships:
        relationship.status = "obsolete"
        relationship.deleted_at = datetime.now(UTC)
        revision = RelationshipRevision(
            relationship_id=relationship.relationship_id,
            project_id=artefact.project_id,
            revision_number=await repo.next_revision_number(relationship.relationship_id),
            payload_json={**relationship.payload_json, "status": "obsolete"},
            changed_by=actor_user_id,
            changed_at=datetime.now(UTC),
        )
        session.add(revision)
        await session.flush()
        relationship.current_revision_id = revision.relationship_revision_id
        await record_event(
            session,
            event_type="relationship.deleted",
            project_id=artefact.project_id,
            actor_user_id=actor_user_id,
            affected_relationship_ids=[relationship.relationship_id],
        )


def _item(
    import_run: ImportRun,
    source_object_id: str,
    source_document: str,
    artefact_type: str,
    change_type: str,
    artefact_id: str,
    proposed_fingerprint: str,
    proposed_payload: dict,
) -> ImportRunItem:
    return ImportRunItem(
        import_run_id=import_run.import_run_id,
        project_id=import_run.project_id,
        source_object_id=source_object_id,
        source_document=source_document,
        artefact_type=artefact_type,
        artefact_id=artefact_id,
        detected_change_type=change_type,
        proposed_fingerprint=proposed_fingerprint,
        proposed_payload_json=proposed_payload,
    )


async def apply_import_decisions(
    session: AsyncSession,
    import_run: ImportRun,
    decisions: list[dict],
    actor_user_id: str,
) -> ImportRun:
    item_by_id = {
        item.import_run_item_id: item
        for item in await session.scalars(
            select(ImportRunItem).where(ImportRunItem.import_run_id == import_run.import_run_id)
        )
    }
    accepted = rejected = 0
    for decision in decisions:
        item = item_by_id.get(decision["decision_id"])
        if item is None or item.decision_status != "pending":
            continue
        if decision["decision"] == "accept_new_revision":
            artefact = await session.get(Artefact, item.artefact_id)
            if artefact is not None:
                await update_artefact(
                    session,
                    artefact,
                    ArtefactUpdate(payload=item.proposed_payload_json, change_reason="import decision"),
                    actor_user_id,
                )
                item.new_revision_id = artefact.current_revision_id
                item.decision_status = "accepted"
                accepted += 1
        else:
            item.decision_status = "rejected"
            rejected += 1
        item.decision_by = actor_user_id
        item.decision_at = datetime.now(UTC)

    pending = [item for item in item_by_id.values() if item.decision_status == "pending"]
    if not pending:
        import_run.state = "completed"
        import_run.completed_at = datetime.now(UTC)
        validation_job = Job(
            project_id=import_run.project_id,
            job_type="validation_run",
            state="running",
            submitted_by=actor_user_id,
            submitted_at=datetime.now(UTC),
            started_at=datetime.now(UTC),
        )
        session.add(validation_job)
        await session.flush()
        validation_run = await run_validation(
            session,
            import_run.project_id,
            actor_user_id,
            scope={"type": "project", "trigger": "sphinx_import", "import_run_id": import_run.import_run_id},
        )
        validation_job.state = "completed"
        validation_job.completed_at = datetime.now(UTC)
        validation_job.progress_percent = 100
        validation_job.result_ref_json = {
            "resource_type": "ValidationRun",
            "resource_id": validation_run.validation_run_id,
        }
    import_run.summary_json = {
        **import_run.summary_json,
        "accepted_decisions": accepted,
        "rejected_decisions": rejected,
        "pending_decisions": len(pending),
    }
    if not pending:
        import_run.summary_json["validation_job_id"] = validation_job.job_id
        import_run.summary_json["validation_run_id"] = validation_run.validation_run_id
    await record_event(
        session,
        event_type="import.decision_submitted",
        project_id=import_run.project_id,
        actor_user_id=actor_user_id,
        payload=import_run.summary_json,
    )
    return import_run
