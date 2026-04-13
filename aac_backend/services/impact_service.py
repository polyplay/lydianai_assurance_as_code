from collections import defaultdict, deque
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.impact import ImpactAnalysisItem, ImpactAnalysisRun, SuspectState
from aac_backend.services.event_service import record_event

FORWARD_PROPAGATION = {"allocates_to", "depends_on", "constrains"}
BACKWARD_PROPAGATION = {
    "assumes",
    "derives_from",
    "implements",
    "produces_result_for",
    "protects",
    "satisfies",
    "verifies",
}
NON_PROPAGATING = {"references", "interacts_via", "guarantees", "mitigates", "traces_to"}
MAX_PROPAGATION_DEPTH = 10
PropagationIndexes = tuple[dict[str, list[tuple[str, str]]], dict[str, list[tuple[str, str]]]]


async def analyze_impact(
    session: AsyncSession,
    *,
    project_id: str,
    artefact_id: str,
    actor_user_id: str | None,
    persist: bool = True,
) -> ImpactAnalysisRun:
    run = ImpactAnalysisRun(
        project_id=project_id,
        state="running",
        requested_by=actor_user_id,
        scope_json={"artefact_id": artefact_id},
        started_at=datetime.now(UTC),
    )
    if persist:
        session.add(run)
        await session.flush()

    traversal = await _traverse_dependents(session, project_id, artefact_id)
    informational = await _informational_relationships(session, project_id, artefact_id)

    for node in traversal:
        if persist:
            session.add(
                ImpactAnalysisItem(
                    impact_analysis_id=run.impact_analysis_id,
                    impacted_artefact_id=node["artefact_id"],
                    impact_type="direct" if node["depth"] == 1 else "indirect",
                    reason_path_json=node["path"],
                    retest_recommendation_json={"recommended": True},
                )
            )
    for relationship in informational:
        if persist:
            session.add(
                ImpactAnalysisItem(
                    impact_analysis_id=run.impact_analysis_id,
                    impacted_relationship_id=relationship.relationship_id,
                    impact_type="affected_informational",
                    reason_path_json=[artefact_id],
                    retest_recommendation_json={"recommended": False},
                )
            )

    run.state = "completed"
    run.completed_at = datetime.now(UTC)
    run.summary_json = {
        "trigger_artefact_id": artefact_id,
        "affected_count": len(traversal),
        "informational_count": len(informational),
        "affected_artefacts": traversal,
    }
    if persist:
        await record_event(
            session,
            event_type="impact_analysis.completed",
            project_id=project_id,
            actor_user_id=actor_user_id,
            payload=run.summary_json,
        )
    return run


async def propagate_suspects(
    session: AsyncSession,
    *,
    project_id: str,
    trigger_artefact_id: str,
    trigger_revision_id: str | None,
    trigger_event_type: str,
    actor_user_id: str | None,
) -> list[SuspectState]:
    trigger = await session.get(Artefact, trigger_artefact_id)
    if trigger is None:
        return []
    if trigger.status != "released" and not await _artefact_in_approved_or_released_baseline(
        session,
        trigger_artefact_id,
    ):
        return []

    traversal = await _traverse_dependents(session, project_id, trigger_artefact_id)
    created: list[SuspectState] = []
    for node in traversal:
        existing = await session.scalar(
            select(SuspectState).where(
                SuspectState.project_id == project_id,
                SuspectState.artefact_id == node["artefact_id"],
                SuspectState.trigger_artefact_id == trigger_artefact_id,
                SuspectState.status == "open",
            )
        )
        if existing:
            continue
        suspect = SuspectState(
            project_id=project_id,
            artefact_id=node["artefact_id"],
            trigger_artefact_id=trigger_artefact_id,
            trigger_revision_id=trigger_revision_id,
            trigger_event_type=trigger_event_type,
            propagation_depth=node["depth"],
            propagation_path_json=node["path"],
            reason=f"{trigger_event_type} on upstream artefact {trigger_artefact_id}",
            status="open",
            created_at=datetime.now(UTC),
        )
        session.add(suspect)
        created.append(suspect)
    if created:
        await record_event(
            session,
            event_type="suspect.propagated",
            project_id=project_id,
            actor_user_id=actor_user_id,
            payload={
                "trigger_artefact_id": trigger_artefact_id,
                "suspect_count": len(created),
            },
            affected_artefact_ids=[item.artefact_id for item in created],
        )
    return created


async def clear_suspect_state(
    session: AsyncSession,
    *,
    suspect_state: SuspectState,
    actor_user_id: str,
    clearing_method: str,
    evidence_refs: list[str],
    reason: str | None,
) -> SuspectState:
    suspect_state.status = "cleared"
    suspect_state.cleared_by = actor_user_id
    suspect_state.cleared_at = datetime.now(UTC)
    suspect_state.clearing_method = clearing_method
    suspect_state.clearing_evidence_refs_json = evidence_refs
    suspect_state.clearance_reason = reason
    await record_event(
        session,
        event_type="suspect.cleared",
        project_id=suspect_state.project_id,
        actor_user_id=actor_user_id,
        payload={
            "suspect_state_id": suspect_state.suspect_state_id,
            "clearing_method": clearing_method,
            "evidence_refs": evidence_refs,
        },
        affected_artefact_ids=[suspect_state.artefact_id],
    )
    return suspect_state


async def open_suspects_for_project(session: AsyncSession, project_id: str) -> list[SuspectState]:
    return list(
        await session.scalars(
            select(SuspectState).where(
                SuspectState.project_id == project_id,
                SuspectState.status == "open",
            )
        )
    )


async def _traverse_dependents(
    session: AsyncSession,
    project_id: str,
    trigger_artefact_id: str,
) -> list[dict]:
    indexes = await _load_propagation_indexes(session, project_id)
    visited = {trigger_artefact_id}
    queue = deque([(trigger_artefact_id, [trigger_artefact_id], 0)])
    affected: list[dict] = []
    while queue:
        current_id, path, depth = queue.popleft()
        if depth >= MAX_PROPAGATION_DEPTH:
            continue
        for dependent_id, relationship_type in _dependent_edges(indexes, current_id):
            if dependent_id in visited:
                continue
            visited.add(dependent_id)
            next_path = [*path, dependent_id]
            node = {
                "artefact_id": dependent_id,
                "relationship_type": relationship_type,
                "depth": depth + 1,
                "path": next_path,
            }
            affected.append(node)
            queue.append((dependent_id, next_path, depth + 1))
    return affected


async def _load_propagation_indexes(
    session: AsyncSession,
    project_id: str,
) -> PropagationIndexes:
    forward_index: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
    backward_index: defaultdict[str, list[tuple[str, str]]] = defaultdict(list)
    relationships = await session.scalars(
        select(Relationship).where(
            Relationship.project_id == project_id,
            Relationship.deleted_at.is_(None),
        )
    )
    for relationship in relationships:
        if relationship.relationship_type in FORWARD_PROPAGATION:
            forward_index[relationship.source_artefact_id].append(
                (relationship.target_artefact_id, relationship.relationship_type)
            )
        if relationship.relationship_type in BACKWARD_PROPAGATION:
            backward_index[relationship.target_artefact_id].append(
                (relationship.source_artefact_id, relationship.relationship_type)
            )
    return dict(forward_index), dict(backward_index)


def _dependent_edges(indexes: PropagationIndexes, artefact_id: str) -> list[tuple[str, str]]:
    forward_index, backward_index = indexes
    return [
        *forward_index.get(artefact_id, []),
        *backward_index.get(artefact_id, []),
    ]


async def _informational_relationships(
    session: AsyncSession,
    project_id: str,
    artefact_id: str,
) -> list[Relationship]:
    return list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.relationship_type.in_(NON_PROPAGATING),
                Relationship.deleted_at.is_(None),
                (
                    (Relationship.source_artefact_id == artefact_id)
                    | (Relationship.target_artefact_id == artefact_id)
                ),
            )
        )
    )


async def _artefact_in_approved_or_released_baseline(
    session: AsyncSession,
    artefact_id: str,
) -> bool:
    from aac_backend.models.baselines import Baseline, BaselineArtefactRevision

    found = await session.scalar(
        select(Baseline.baseline_id)
        .join(BaselineArtefactRevision, BaselineArtefactRevision.baseline_id == Baseline.baseline_id)
        .where(
            BaselineArtefactRevision.artefact_id == artefact_id,
            Baseline.state.in_(("approved", "released")),
        )
        .limit(1)
    )
    return found is not None
