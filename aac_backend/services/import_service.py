from datetime import UTC, datetime
from math import ceil

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
from aac_backend.services.request_context import current_correlation_id


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


async def create_import_run(
    session: AsyncSession,
    project_id: str,
    data: ImportStart,
    actor_user_id: str,
    *,
    correlation_id: str | None = None,
    batch_size: int = 100,
) -> ImportRun:
    import_run = ImportRun(
        project_id=project_id,
        source_root=data.source_root,
        state="created",
        version_update_mode=data.version_update_mode or "ask_user",
        submitted_by=actor_user_id,
        submitted_at=datetime.now(UTC),
        source_payload_json=data.model_dump(),
        batch_size=batch_size,
        total_batches=ceil(len(data.sphinx_needs) / batch_size) if data.sphinx_needs else 0,
        last_committed_batch_index=-1,
        cancellation_requested=False,
        committed_effects_json={"exists": False, "last_committed_unit": None},
        correlation_id=correlation_id or current_correlation_id(),
        summary_json={},
        diagnostics_json=[],
    )
    session.add(import_run)
    await session.flush()
    await record_event(
        session,
        event_type="import.started",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload={
            "import_run_id": import_run.import_run_id,
            "submitted_item_count": len(data.sphinx_needs),
        },
    )
    return import_run


async def process_import_run(
    session: AsyncSession,
    import_run: ImportRun,
    actor_user_id: str,
    *,
    actor_roles: set[str] | None = None,
    job: Job | None = None,
) -> ImportRun:
    if import_run.state in {
        "completed",
        "completed_with_errors",
        "completed_no_changes_applied",
        "failed",
        "cancelled",
    }:
        return import_run
    data = ImportStart(**import_run.source_payload_json)
    return await import_sphinx_needs(
        session,
        import_run.project_id,
        data,
        actor_user_id,
        actor_roles=actor_roles,
        import_run=import_run,
        job=job,
    )


async def import_sphinx_needs(
    session: AsyncSession,
    project_id: str,
    data: ImportStart,
    actor_user_id: str,
    actor_roles: set[str] | None = None,
    import_run: ImportRun | None = None,
    job: Job | None = None,
) -> ImportRun:
    if import_run is None:
        import_run = await create_import_run(
            session,
            project_id,
            data,
            actor_user_id,
        )
        await session.commit()
    import_run.state = "parsed"
    import_run.source_payload_json = data.model_dump()
    import_run.total_batches = (
        ceil(len(data.sphinx_needs) / import_run.batch_size)
        if data.sphinx_needs
        else 0
    )

    repo = ArtefactRepository(session)
    existing_summary = import_run.summary_json or {}
    created = int(existing_summary.get("created", 0))
    changed = int(existing_summary.get("changed", 0))
    unchanged = int(existing_summary.get("unchanged", 0))
    waiting = int(existing_summary.get("waiting_for_user", 0))
    errors = int(existing_summary.get("errors", 0))
    deleted = int(existing_summary.get("deleted", 0))
    type_mismatches = int(existing_summary.get("type_mismatches", 0))
    conflicts = int(existing_summary.get("conflicts", 0))
    seen_source_keys: set[tuple[str, str]] = set()
    imported_documents: set[str] = set()
    raw_entries: list[dict] = []

    for raw_need in data.sphinx_needs:
        source_object_id = raw_need.get(ID_FIELD)
        if source_object_id is None:
            continue
        source_document = str(raw_need.get("source_document") or raw_need.get("docname") or "")
        seen_source_keys.add((source_document, str(source_object_id)))
        imported_documents.add(source_document)
        raw_entries.append(
            {
                "raw_need": raw_need,
                "source_object_id": str(source_object_id),
                "source_document": source_document,
            }
        )

    start_index = (import_run.last_committed_batch_index + 1) * import_run.batch_size

    async def checkpoint(item_index: int) -> None:
        await _commit_batch_if_boundary(
            session,
            import_run,
            job,
            item_index,
            len(data.sphinx_needs),
            _import_summary(
                created,
                changed,
                unchanged,
                waiting,
                errors,
                deleted,
                type_mismatches,
                conflicts,
                0,
            ),
        )

    for item_index, raw_need in enumerate(data.sphinx_needs):
        if item_index < start_index:
            continue
        if item_index % import_run.batch_size == 0:
            await _refresh_cancellation_state(session, import_run, job)
            if import_run.cancellation_requested or (job and job.cancellation_requested):
                return await _cancel_import_at_boundary(session, import_run, job, actor_user_id)
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
            await checkpoint(item_index)
            continue

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
                await checkpoint(item_index)
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
            await checkpoint(item_index)
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
            await checkpoint(item_index)
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
                if existing.status == "released" and not _can_revise_released(actor_roles):
                    errors += 1
                    item.decision_status = "rejected"
                    session.add(item)
                    import_run.diagnostics_json.append(
                        {
                            "level": "error",
                            "classification": "authorization_denied",
                            "source_object_id": source_object_id,
                            "message": "Quality Engineer or Admin required to revise released artefact",
                        }
                    )
                    await checkpoint(item_index)
                    continue
                try:
                    await update_artefact(
                        session,
                        existing,
                        ArtefactUpdate(
                            title=title,
                            description=description,
                            payload=payload,
                            base_revision_id=existing.current_revision_id,
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
                    await checkpoint(item_index)
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
            await checkpoint(item_index)
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
            await checkpoint(item_index)
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
            if existing.status == "released" and not _can_revise_released(actor_roles):
                errors += 1
                item.decision_status = "rejected"
                session.add(item)
                import_run.diagnostics_json.append(
                    {
                        "level": "error",
                        "classification": "authorization_denied",
                        "source_object_id": source_object_id,
                        "message": "Quality Engineer or Admin required to revise released artefact",
                    }
                )
                await checkpoint(item_index)
                continue
            try:
                await update_artefact(
                    session,
                    existing,
                    ArtefactUpdate(
                        title=title,
                        description=description,
                        payload=payload,
                        base_revision_id=existing.current_revision_id,
                        change_reason="sphinx import",
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
                await checkpoint(item_index)
                continue
            item.new_revision_id = existing.current_revision_id
            item.decision_status = "automatic"
            changed += 1
        else:
            item.decision_status = "pending"
            import_run.state = "waiting_for_user"
            waiting += 1
        session.add(item)
        await checkpoint(item_index)

    await _refresh_cancellation_state(session, import_run, job)
    if import_run.cancellation_requested or (job and job.cancellation_requested):
        return await _cancel_import_at_boundary(session, import_run, job, actor_user_id)

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
    elif not any((created, changed, deleted, relationships_created)):
        final_state = "completed_no_changes_applied"
    else:
        final_state = "completed"
    import_run.state = final_state
    import_run.completed_at = None if waiting else datetime.now(UTC)
    import_run.diagnostics_json = list(import_run.diagnostics_json)
    import_run.summary_json = _import_summary(
        created,
        changed,
        unchanged,
        waiting,
        errors,
        deleted,
        type_mismatches,
        conflicts,
        relationships_created,
    )
    effects_exist = bool(created or changed or deleted or relationships_created)
    import_run.committed_effects_json = {
        "exists": effects_exist,
        "last_committed_unit": (
            f"batch:{import_run.last_committed_batch_index}"
            if import_run.last_committed_batch_index >= 0
            else None
        ),
    }
    if job is not None:
        job.committed_effects_json = import_run.committed_effects_json
        job.last_committed_unit = import_run.committed_effects_json["last_committed_unit"]
    await record_event(
        session,
        event_type="import.completed" if final_state.startswith("completed") else "import.waiting_for_user",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload={
            "import_run_id": import_run.import_run_id,
            "state": final_state,
            **import_run.summary_json,
        },
        idempotency_key=(
            f"import:{import_run.import_run_id}:completed"
            if final_state.startswith("completed")
            else None
        ),
    )
    await session.commit()
    return import_run


def _import_summary(
    created: int,
    changed: int,
    unchanged: int,
    waiting: int,
    errors: int,
    deleted: int,
    type_mismatches: int,
    conflicts: int,
    relationships_created: int,
) -> dict:
    return {
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


async def _commit_batch_if_boundary(
    session: AsyncSession,
    import_run: ImportRun,
    job: Job | None,
    item_index: int,
    item_count: int,
    summary: dict,
) -> None:
    if item_count == 0:
        return
    at_boundary = (
        (item_index + 1) % import_run.batch_size == 0
        or item_index + 1 == item_count
    )
    if not at_boundary:
        return
    batch_index = item_index // import_run.batch_size
    import_run.last_committed_batch_index = batch_index
    import_run.summary_json = summary
    import_run.diagnostics_json = list(import_run.diagnostics_json)
    effects_exist = bool(
        summary["created"]
        or summary["changed"]
        or summary["deleted"]
        or summary["relationships_created"]
    )
    import_run.committed_effects_json = {
        "exists": effects_exist,
        "last_committed_unit": f"batch:{batch_index}",
    }
    if job is not None:
        job.progress_percent = min(
            int(((item_index + 1) / max(item_count, 1)) * 90),
            90,
        )
        job.committed_effects_json = import_run.committed_effects_json
        job.last_committed_unit = f"batch:{batch_index}"
    await session.flush()
    await session.commit()


async def _refresh_cancellation_state(
    session: AsyncSession,
    import_run: ImportRun,
    job: Job | None,
) -> None:
    refresh = getattr(session, "refresh", None)
    if refresh is None:
        return
    await refresh(import_run, attribute_names=["cancellation_requested"])
    if job is not None:
        await refresh(job, attribute_names=["cancellation_requested"])


async def _cancel_import_at_boundary(
    session: AsyncSession,
    import_run: ImportRun,
    job: Job | None,
    actor_user_id: str,
) -> ImportRun:
    import_run.state = "cancelled"
    import_run.completed_at = datetime.now(UTC)
    if job is not None:
        job.state = "cancelled"
        job.completed_at = import_run.completed_at
        job.committed_effects_json = import_run.committed_effects_json
        job.last_committed_unit = import_run.committed_effects_json.get(
            "last_committed_unit"
        )
    await record_event(
        session,
        event_type="import.cancelled",
        project_id=import_run.project_id,
        actor_user_id=actor_user_id,
        payload={
            "import_run_id": import_run.import_run_id,
            "committed_effects": import_run.committed_effects_json,
            "last_committed_batch_index": import_run.last_committed_batch_index,
        },
        idempotency_key=f"import:{import_run.import_run_id}:cancelled",
    )
    await session.commit()
    return import_run


async def mark_import_failed(
    session: AsyncSession,
    *,
    import_run_id: str,
    job_id: str | None,
    actor_user_id: str,
    error: Exception,
) -> tuple[ImportRun | None, Job | None]:
    await session.rollback()
    import_run = await session.get(ImportRun, import_run_id)
    job = await session.get(Job, job_id) if job_id else None
    now = datetime.now(UTC)
    error_payload = {"error": type(error).__name__, "message": str(error)}
    if import_run is not None:
        import_run.state = "failed"
        import_run.completed_at = now
        import_run.diagnostics_json = [
            *(import_run.diagnostics_json or []),
            {"level": "error", **error_payload},
        ]
    if job is not None:
        job.state = "failed"
        job.completed_at = now
        job.error_json = error_payload
    if import_run is not None:
        await record_event(
            session,
            event_type="import.failed",
            project_id=import_run.project_id,
            actor_user_id=actor_user_id,
            payload={
                "import_run_id": import_run.import_run_id,
                "error": error_payload,
                "committed_effects": import_run.committed_effects_json,
            },
            idempotency_key=f"import:{import_run.import_run_id}:failed",
        )
    await session.commit()
    return import_run, job


async def mark_import_interrupted(
    session: AsyncSession,
    *,
    import_run_id: str,
    job_id: str | None,
    actor_user_id: str,
    error: Exception,
    attempt: int,
) -> tuple[ImportRun | None, Job | None]:
    await session.rollback()
    import_run = await session.get(ImportRun, import_run_id)
    job = await session.get(Job, job_id) if job_id else None
    error_payload = {
        "error": type(error).__name__,
        "message": str(error),
        "attempt": attempt,
        "retryable": True,
    }
    if import_run is not None:
        import_run.state = "parsed"
        import_run.completed_at = None
        import_run.diagnostics_json = [
            *(import_run.diagnostics_json or []),
            {"level": "warning", **error_payload},
        ]
    if job is not None:
        job.state = "queued"
        job.completed_at = None
        job.error_json = error_payload
    if import_run is not None:
        await record_event(
            session,
            event_type="import.interrupted",
            project_id=import_run.project_id,
            actor_user_id=actor_user_id,
            payload={
                "import_run_id": import_run.import_run_id,
                "attempt": attempt,
                "error": error_payload,
                "last_committed_batch_index": import_run.last_committed_batch_index,
                "committed_effects": import_run.committed_effects_json,
            },
            idempotency_key=f"import:{import_run.import_run_id}:interrupted:{attempt}",
        )
    await session.commit()
    return import_run, job


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
        previous_revision_id = relationship.current_revision_id
        audit = await record_event(
            session,
            event_type="relationship.deleted",
            project_id=artefact.project_id,
            actor_user_id=actor_user_id,
            affected_relationship_ids=[relationship.relationship_id],
        )
        await session.flush()
        revision = RelationshipRevision(
            relationship_id=relationship.relationship_id,
            previous_revision_id=previous_revision_id,
            project_id=artefact.project_id,
            revision_number=await repo.next_revision_number(relationship.relationship_id),
            payload_json={**relationship.payload_json, "status": "obsolete"},
            changed_by=actor_user_id,
            changed_at=datetime.now(UTC),
            audit_event_id=audit.audit_event_id,
        )
        session.add(revision)
        await session.flush()
        relationship.current_revision_id = revision.relationship_revision_id


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
    actor_roles: set[str] | None = None,
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
                if artefact.status == "released" and not _can_revise_released(actor_roles):
                    raise PermissionError(
                        "Quality Engineer or Admin required to revise released artefact"
                    )
                await update_artefact(
                    session,
                    artefact,
                    ArtefactUpdate(
                        payload=item.proposed_payload_json,
                        base_revision_id=artefact.current_revision_id,
                        change_reason="import decision",
                    ),
                    actor_user_id,
                )
                item.new_revision_id = artefact.current_revision_id
                item.decision_status = "accepted"
                accepted += 1
        elif decision["decision"] == "reject_keep_current":
            item.decision_status = "rejected"
            rejected += 1
        else:
            raise ValueError(f"Unsupported import decision: {decision['decision']}")
        item.decision_by = actor_user_id
        item.decision_at = datetime.now(UTC)

    pending = [item for item in item_by_id.values() if item.decision_status == "pending"]
    if not pending:
        if int((import_run.summary_json or {}).get("errors", 0)) > 0:
            import_run.state = "completed_with_errors"
        elif accepted:
            import_run.state = "completed"
        else:
            import_run.state = "completed_no_changes_applied"
        import_run.completed_at = datetime.now(UTC)
    import_run.summary_json = {
        **import_run.summary_json,
        "accepted_decisions": accepted,
        "rejected_decisions": rejected,
        "pending_decisions": len(pending),
    }
    await record_event(
        session,
        event_type="import.decision_submitted",
        project_id=import_run.project_id,
        actor_user_id=actor_user_id,
        payload=import_run.summary_json,
    )
    if not pending:
        await record_event(
            session,
            event_type="import.completed",
            project_id=import_run.project_id,
            actor_user_id=actor_user_id,
            payload={
                "import_run_id": import_run.import_run_id,
                "state": import_run.state,
                **import_run.summary_json,
            },
            idempotency_key=f"import:{import_run.import_run_id}:completed",
        )
    return import_run


def _can_revise_released(actor_roles: set[str] | None) -> bool:
    return bool({"admin", "quality_engineer"}.intersection(actor_roles or set()))
