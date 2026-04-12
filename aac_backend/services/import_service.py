from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact
from aac_backend.models.imports import ImportRun, ImportRunItem
from aac_backend.repositories.domain import ArtefactRepository
from aac_backend.schemas.domain import ArtefactCreate, ArtefactSource, ArtefactUpdate, ImportStart
from aac_backend.services.artefact_service import create_artefact, fingerprint, update_artefact
from aac_backend.services.event_service import record_event


TYPE_FIELD = "type"
ID_FIELD = "id"


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
    created = changed = unchanged = waiting = errors = 0

    for raw_need in data.sphinx_needs:
        try:
            source_object_id = str(raw_need[ID_FIELD])
            artefact_type = str(raw_need.get(TYPE_FIELD) or raw_need.get("artefact_type"))
            source_document = str(raw_need.get("source_document") or raw_need.get("docname") or "")
            payload = dict(raw_need.get("payload") or raw_need)
            title = str(raw_need.get("title") or source_object_id)
            description = str(raw_need.get("description") or raw_need.get("content") or "")
        except Exception as exc:
            errors += 1
            import_run.diagnostics_json.append({"level": "error", "message": str(exc), "raw": raw_need})
            continue

        existing = await repo.by_source_identity(project_id, source_document, source_object_id)
        proposed_fingerprint = fingerprint(payload)
        if existing is None:
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
            await update_artefact(
                session,
                existing,
                ArtefactUpdate(title=title, description=description, payload=payload, change_reason="sphinx import"),
                actor_user_id,
            )
            item.new_revision_id = existing.current_revision_id
            item.decision_status = "automatic"
            changed += 1
        else:
            item.decision_status = "pending"
            import_run.state = "waiting_for_user"
            waiting += 1
        session.add(item)

    if waiting:
        final_state = "waiting_for_user"
    elif errors:
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
    }
    await record_event(
        session,
        event_type="import.completed" if final_state.startswith("completed") else "import.waiting_for_user",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=import_run.summary_json,
    )
    return import_run


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
    return import_run
