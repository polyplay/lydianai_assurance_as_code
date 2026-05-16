from collections import defaultdict
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aac_backend.models.artefacts import Artefact, Relationship
from aac_backend.models.impact import SuspectState
from aac_backend.models.projects import AssuranceProfile, Project, ProjectConfiguration, TailoringDecision
from aac_backend.models.repository_integrations import RepositoryConnector
from aac_backend.models.validation import ValidationIssue, ValidationRule, ValidationRun
from aac_backend.rules.catalog import RULE_CATALOG
from aac_backend.services.assurance_configuration_service import (
    ASIL_D_MANDATORY_ARTEFACT_TYPES,
    RELATIONSHIP_TYPES,
)
from aac_backend.services.artefact_schema_service import required_fields_for_artefact_type
from aac_backend.services.event_service import record_event

VALID_ASIL_LEVELS = {"QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D", "mixed"}
REQUIREMENT_TYPES = {"SoftwareRequirement", "SoftwareSafetyRequirement", "DerivedSoftwareRequirement"}
SAFETY_SOURCE_TYPES = {"TechnicalSafetyRequirement", "HardwareSoftwareInterface", "SafetyGoal"}
TEST_TYPES = {"TestCase", "TestSpecification", "TestResult"}
VALID_VERIFICATION_INTENTS = {
    "analysis",
    "formal_verification",
    "inspection",
    "review",
    "simulation",
    "test",
}
MANDATORY_ASIL_D_ARTEFACT_TYPES = set(ASIL_D_MANDATORY_ARTEFACT_TYPES)


async def seed_rule_catalog(session: AsyncSession) -> None:
    existing_ids = set(
        await session.scalars(
            select(ValidationRule.rule_id).where(ValidationRule.rule_id.in_(RULE_CATALOG))
        )
    )
    for rule in RULE_CATALOG.values():
        if rule.rule_id in existing_ids:
            continue
        session.add(
            ValidationRule(
                rule_id=rule.rule_id,
                title=rule.title,
                source_basis_json=[],
                standards_refs_json=[],
                default_severity=rule.severity,
                rule_payload_json={
                    "execution_modes": list(rule.execution_modes),
                    "blocking_contexts": list(rule.blocking_contexts),
                },
                status="active",
            )
        )


async def run_validation(
    session: AsyncSession,
    project_id: str,
    actor_user_id: str,
    scope: dict | None = None,
) -> ValidationRun:
    await session.execute(
        update(ValidationIssue)
        .where(ValidationIssue.project_id == project_id, ValidationIssue.status == "open")
        .values(status="superseded", resolved_at=datetime.now(UTC))
    )
    run = ValidationRun(
        project_id=project_id,
        scope_json=scope or {"type": "project", "id": project_id},
        state="running",
        started_at=datetime.now(UTC),
    )
    session.add(run)
    await session.flush()

    issues: list[ValidationIssue] = []
    artefacts = list(
        await session.scalars(
            select(Artefact).where(Artefact.project_id == project_id, Artefact.deleted_at.is_(None))
        )
    )
    relationships = list(
        await session.scalars(
            select(Relationship).where(
                Relationship.project_id == project_id,
                Relationship.deleted_at.is_(None),
            )
        )
    )
    tailoring_decisions = list(
        await session.scalars(
            select(TailoringDecision).where(TailoringDecision.project_id == project_id)
        )
    )
    open_suspects = list(
        await session.scalars(
            select(SuspectState).where(
                SuspectState.project_id == project_id,
                SuspectState.status == "open",
            )
        )
    )
    repository_connectors = list(
        await session.scalars(
            select(RepositoryConnector).where(
                RepositoryConnector.project_id == project_id,
                RepositoryConnector.status == "active",
            )
        )
    )
    config = await session.scalar(
        select(ProjectConfiguration).where(ProjectConfiguration.project_id == project_id)
    )
    project = await session.get(Project, project_id)
    profile_id = (scope or {}).get("profile_id") or (project.active_profile_id if project else None)
    profile = await session.get(AssuranceProfile, profile_id) if profile_id else None
    context = ValidationContext(
        project_id=project_id,
        mode=_validation_mode(scope),
        artefacts=artefacts,
        relationships=relationships,
        tailoring_decisions=tailoring_decisions,
        open_suspects=open_suspects,
        validation_policy=(config.validation_policy_json if config else {}),
        profile_payload=(profile.profile_payload_json if profile else {}),
        repository_connectors=repository_connectors,
    )

    for rule_id, rule in RULE_CATALOG.items():
        if context.mode not in context.rule_execution_modes(rule_id, rule.execution_modes):
            continue
        if context.rule_disabled(rule_id):
            continue
        issues.extend(_evaluate_rule(run, context, rule_id))
    issues.extend(_meta_rule_issues(run, context, issues))

    for issue in issues:
        session.add(issue)

    run.state = "completed"
    run.completed_at = datetime.now(UTC)
    run.summary_json = {"issue_count": len(issues)}
    await record_event(
        session,
        event_type="validation.run_completed",
        project_id=project_id,
        actor_user_id=actor_user_id,
        payload=run.summary_json,
    )
    return run


def _validation_mode(scope: dict | None) -> str:
    trigger = (scope or {}).get("trigger")
    if trigger == "sphinx_import":
        return "import"
    if trigger == "baseline_eligibility":
        return "baseline"
    if trigger == "release_gate":
        return "release_gate"
    return (scope or {}).get("mode", "manual")


class ValidationContext:
    def __init__(
        self,
        *,
        project_id: str,
        mode: str,
        artefacts: list[Artefact],
        relationships: list[Relationship],
        tailoring_decisions: list[TailoringDecision],
        open_suspects: list[SuspectState],
        validation_policy: dict,
        profile_payload: dict,
        repository_connectors: list[RepositoryConnector] | None = None,
    ) -> None:
        self.project_id = project_id
        self.mode = mode
        self.artefacts = artefacts
        self.relationships = relationships
        self.tailoring_decisions = tailoring_decisions
        self.open_suspects = open_suspects
        self.repository_connectors = repository_connectors or []
        self.validation_policy = validation_policy or {}
        self.profile_payload = profile_payload or {}
        self.by_id = {artefact.artefact_id: artefact for artefact in artefacts}
        self.repository_connector_ids = {
            connector.repository_connector_id for connector in self.repository_connectors
        }
        self.by_source_object_id = {artefact.source_object_id: artefact for artefact in artefacts}
        self.by_type: dict[str, list[Artefact]] = defaultdict(list)
        self.by_source: dict[tuple[str, str], list[Relationship]] = defaultdict(list)
        self.by_target: dict[tuple[str, str], list[Relationship]] = defaultdict(list)
        for artefact in artefacts:
            self.by_type[artefact.artefact_type].append(artefact)
        for relationship in relationships:
            self.by_source[(relationship.source_artefact_id, relationship.relationship_type)].append(relationship)
            self.by_target[(relationship.target_artefact_id, relationship.relationship_type)].append(relationship)

    def rule_disabled(self, rule_id: str) -> bool:
        rule_cfg = self.rule_config(rule_id)
        return rule_cfg.get("enabled") is False or rule_cfg.get("severity") == "disabled"

    def rule_config(self, rule_id: str) -> dict:
        cfg = dict(((self.profile_payload.get("rules") or {}).get(rule_id)) or {})
        cfg.update(((self.validation_policy.get("rules") or {}).get(rule_id)) or {})
        return cfg

    def rule_execution_modes(self, rule_id: str, default: tuple[str, ...]) -> tuple[str, ...]:
        configured = self.rule_config(rule_id).get("execution_modes")
        return tuple(configured or default)

    def rule_severity(self, rule_id: str, default: str) -> str:
        return str(self.rule_config(rule_id).get("severity") or default)

    def rule_blocking_contexts(self, rule_id: str, default: list[str]) -> list[str]:
        return list(self.rule_config(rule_id).get("blocking_contexts", default))

    def payload_value(self, artefact: Artefact, key: str, default=None):
        if artefact is None:
            return default
        if hasattr(artefact, key):
            value = getattr(artefact, key)
            if value not in (None, "", [], {}):
                return value
        return artefact.payload_json.get(key, default)

    def artefact_by_ref(self, ref: str | None) -> Artefact | None:
        if not ref:
            return None
        return self.by_id.get(ref) or self.by_source_object_id.get(ref)

    def ref_exists(self, ref: str | None) -> bool:
        return self.artefact_by_ref(ref) is not None

    def mandatory_artefact_types(self) -> set[str]:
        artefact_classes = self.profile_payload.get("artefact_classes") or {}
        mandatory = {
            artefact_type
            for artefact_type, config in artefact_classes.items()
            if config.get("applicability") == "mandatory"
        }
        if "artefact_classes" in self.profile_payload:
            return mandatory
        return set(MANDATORY_ASIL_D_ARTEFACT_TYPES)

    def has_type_level_tailoring(self, artefact_type: str) -> bool:
        return any(
            decision.status == "approved"
            and decision.target_kind == "artefact_class"
            and decision.target_id == artefact_type
            and decision.tailored_applicability == "not_applicable"
            and decision.rationale
            and decision.evidence_refs_json
            for decision in self.tailoring_decisions
        )

    def has_tailoring_not_applicable(self, target_id: str) -> bool:
        return self.has_type_level_tailoring(target_id)

    def related(
        self,
        artefact_id: str,
        rel_type: str,
        direction: str,
        *,
        artefact_type: str | None = None,
        artefact_type_in: set[str] | None = None,
    ) -> list[Artefact]:
        related: list[Artefact] = []
        relationships = (
            self.by_source.get((artefact_id, rel_type), [])
            if direction == "outgoing"
            else self.by_target.get((artefact_id, rel_type), [])
        )
        for relationship in relationships:
            other_id = None
            if direction == "outgoing" and relationship.source_artefact_id == artefact_id:
                other_id = relationship.target_artefact_id
            if direction == "incoming" and relationship.target_artefact_id == artefact_id:
                other_id = relationship.source_artefact_id
            if other_id is None:
                continue
            other = self.by_id.get(other_id)
            if other is None:
                continue
            if artefact_type and other.artefact_type != artefact_type:
                continue
            if artefact_type_in and other.artefact_type not in artefact_type_in:
                continue
            related.append(other)
        return related

    def has_related(self, artefact_id: str, rel_type: str, direction: str, **kwargs) -> bool:
        return bool(self.related(artefact_id, rel_type, direction, **kwargs))

    def has_pass_test_result_for(self, artefact_id: str) -> bool:
        return any(
            self.payload_value(result, "verdict") == "pass"
            for result in self.related(
                artefact_id,
                "verifies",
                "incoming",
                artefact_type="TestResult",
            )
        )


def _evaluate_rule(
    run: ValidationRun,
    context: ValidationContext,
    rule_id: str,
) -> list[ValidationIssue]:
    evaluator = RULE_EVALUATORS.get(rule_id)
    if evaluator is None:
        return []
    issues = evaluator(run, context)
    for issue in issues:
        issue.severity = context.rule_severity(rule_id, issue.severity)
        issue.blocking_contexts_json = context.rule_blocking_contexts(
            rule_id,
            issue.blocking_contexts_json,
        )
    return issues


def _issue_for_artefact(
    run: ValidationRun,
    rule_id: str,
    artefact: Artefact,
    message: str,
) -> ValidationIssue:
    return _issue(run, rule_id, message, [artefact.artefact_id])


def _issue_for_relationship(
    run: ValidationRun,
    rule_id: str,
    relationship: Relationship,
    message: str,
) -> ValidationIssue:
    issue = _issue(run, rule_id, message, [])
    issue.affected_relationship_ids_json = [relationship.relationship_id]
    return issue


def _rule_001(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_relationship(
            run,
            "AAC-RULE-RULE-001",
            relationship,
            "Relationship references a missing or deleted artefact",
        )
        for relationship in context.relationships
        if relationship.source_artefact_id not in context.by_id
        or relationship.target_artefact_id not in context.by_id
    ]


def _relationship_type_allowed(context: ValidationContext, relationship: Relationship) -> bool:
    source = context.by_id.get(relationship.source_artefact_id)
    target = context.by_id.get(relationship.target_artefact_id)
    if source is None or target is None:
        return False
    return relationship_type_allowed_for_types(
        source.artefact_type,
        target.artefact_type,
        relationship.relationship_type,
        same_artefact=source.artefact_id == target.artefact_id,
    )


def relationship_type_allowed_for_types(
    source_type: str,
    target_type: str,
    rel_type: str,
    *,
    same_artefact: bool = False,
) -> bool:
    if same_artefact:
        return False
    if rel_type not in RELATIONSHIP_TYPES:
        return False
    if rel_type == "allocates_to":
        return target_type in {"SoftwareComponent", "SoftwareUnit", "ImplementationItem"}
    if rel_type == "verifies":
        return source_type in TEST_TYPES
    if rel_type == "implements":
        return source_type in {"ImplementationItem", "SoftwareUnit"}
    if rel_type == "interacts_via":
        return source_type == "SoftwareComponent" and target_type == "SoftwareComponent"
    if rel_type == "protects":
        return source_type == "Safeguard"
    if rel_type == "produces_result_for":
        return source_type == "TestResult"
    if rel_type == "derives_from":
        return source_type in REQUIREMENT_TYPES | {"FunctionalSafetyRequirement", "TechnicalSafetyRequirement"}
    if rel_type == "satisfies":
        return source_type in {
            "SoftwareArchitecture",
            "SoftwareComponent",
            "SoftwareUnit",
            "AssumptionGuaranteeContract",
        }
    if rel_type == "depends_on":
        return source_type in {"SoftwareComponent", "SoftwareUnit", "ImplementationItem"}
    if rel_type in {"references", "traces_to"}:
        return True
    if rel_type in {"assumes", "guarantees"}:
        return source_type == "AssumptionGuaranteeContract"
    if rel_type == "constrains":
        return target_type in {"SoftwareRequirement", "SoftwareSafetyRequirement", "InterfaceContract"}
    if rel_type == "mitigates":
        return source_type in {"Safeguard", "SafetyMechanism", "CybersecurityInterfaceEvidence"}
    return False


def _rule_002(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_relationship(
            run,
            "AAC-RULE-RULE-002",
            relationship,
            "Relationship type is not permitted for the source and target artefact types",
        )
        for relationship in context.relationships
        if not _relationship_type_allowed(context, relationship)
    ]


def _rule_003(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    seen: dict[tuple[str, str], Artefact] = {}
    issues: list[ValidationIssue] = []
    for artefact in context.artefacts:
        key = (artefact.source_document, artefact.source_object_id)
        if key in seen:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-003",
                    artefact,
                    "Artefact source identity is not unique",
                )
            )
        seen[key] = artefact
    return issues


def _rule_004(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for artefact in context.artefacts:
        payload_required_fields = required_fields_for_artefact_type(artefact.artefact_type)
        missing = [
            field
            for field in ("artefact_type", "title", "source_object_id", *payload_required_fields)
            if not context.payload_value(artefact, field)
        ]
        if missing:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-004",
                    artefact,
                    f"Artefact required metadata is incomplete: {', '.join(missing)}",
                )
            )
    return issues


def _rule_005(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for artefact_type in sorted(context.mandatory_artefact_types()):
        if context.by_type.get(artefact_type) or context.has_type_level_tailoring(artefact_type):
            continue
        issues.append(
            _issue(
                run,
                "AAC-RULE-RULE-005",
                f"Mandatory artefact type is absent and not tailored: {artefact_type}",
                [],
            )
        )
    return issues


def _rule_006(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for decision in context.tailoring_decisions:
        missing = []
        if not decision.rationale:
            missing.append("rationale")
        if not decision.evidence_refs_json:
            missing.append("evidence_refs")
        if not decision.scope_type or not decision.scope_id:
            missing.append("scope")
        if not decision.approved_by or not decision.approved_at:
            missing.append("approval")
        if not decision.previous_applicability or not decision.tailored_applicability:
            missing.append("applicability")
        if missing:
            issues.append(
                _issue(
                    run,
                    "AAC-RULE-RULE-006",
                    f"Tailoring decision is incomplete: {', '.join(missing)}",
                    [],
                )
            )
    return issues


def _rule_010(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-010",
            artefact,
            "SoftwareSafetyRequirement has no allocation to a SoftwareComponent",
        )
        for artefact in context.by_type.get("SoftwareSafetyRequirement", [])
        if not context.has_related(
            artefact.artefact_id,
            "allocates_to",
            "outgoing",
            artefact_type="SoftwareComponent",
        )
    ]


def _rule_011(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for artefact in context.artefacts:
        is_parent = bool(
            context.payload_value(artefact, "is_parent_requirement")
            or context.payload_value(artefact, "has_children")
            or context.payload_value(artefact, "decomposition_type")
        )
        if artefact.artefact_type in REQUIREMENT_TYPES and is_parent and not context.has_related(
            artefact.artefact_id,
            "derives_from",
            "incoming",
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-011",
                    artefact,
                    "Parent requirement has no child decomposition trace",
                )
            )
    return issues


def _verification_intent_valid(intent) -> bool:
    if isinstance(intent, str):
        return intent in VALID_VERIFICATION_INTENTS
    if isinstance(intent, list):
        return bool(intent) and all(item in VALID_VERIFICATION_INTENTS for item in intent)
    if isinstance(intent, dict):
        methods = intent.get("methods") or intent.get("verification_methods") or []
        if isinstance(methods, str):
            methods = [methods]
        return bool(methods) and all(method in VALID_VERIFICATION_INTENTS for method in methods)
    return False


def _rule_012(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-012",
            artefact,
            "Requirement has no recognized verification intent",
        )
        for artefact in context.artefacts
        if artefact.artefact_type in {"SoftwareSafetyRequirement", "SoftwareRequirement"}
        and not _verification_intent_valid(context.payload_value(artefact, "verification_intent"))
    ]


def _rule_013(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-013",
            artefact,
            "Released requirement has no passing TestResult verification evidence",
        )
        for artefact in context.artefacts
        if artefact.artefact_type in {"SoftwareSafetyRequirement", "SoftwareRequirement"}
        and artefact.status == "released"
        and not context.has_pass_test_result_for(artefact.artefact_id)
    ]


def _rule_014(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-014",
            artefact,
            "SoftwareSafetyRequirement does not derive from a safety source",
        )
        for artefact in context.by_type.get("SoftwareSafetyRequirement", [])
        if not context.has_related(
            artefact.artefact_id,
            "derives_from",
            "outgoing",
            artefact_type_in=SAFETY_SOURCE_TYPES,
        )
    ]


def _component_criticality(context: ValidationContext, component: Artefact | None) -> str | None:
    if component is None:
        return None
    return context.payload_value(component, "criticality_classification") or context.payload_value(
        component,
        "classification",
    )


def _rule_020(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-020",
            artefact,
            "SoftwareComponent criticality classification is missing or invalid",
        )
        for artefact in context.by_type.get("SoftwareComponent", [])
        if _component_criticality(context, artefact) not in VALID_ASIL_LEVELS
    ]


def _rule_021(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for req in context.by_type.get("SoftwareSafetyRequirement", []):
        if req.status == "released" and not context.has_related(
            req.artefact_id,
            "allocates_to",
            "outgoing",
            artefact_type="SoftwareComponent",
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-021",
                    req,
                    "Released SoftwareSafetyRequirement has no component allocation",
                )
            )
    for component in context.by_type.get("SoftwareComponent", []):
        if not (
            context.has_related(component.artefact_id, "allocates_to", "incoming")
            or context.has_related(component.artefact_id, "satisfies", "outgoing")
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-021",
                    component,
                    "SoftwareComponent is not covered by architecture relationships",
                )
            )
    return issues


def _rule_022(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for relationship in context.relationships:
        source = context.by_id.get(relationship.source_artefact_id)
        target = context.by_id.get(relationship.target_artefact_id)
        if (
            relationship.relationship_type != "depends_on"
            or source is None
            or target is None
            or source.artefact_type != "SoftwareComponent"
            or target.artefact_type != "SoftwareComponent"
        ):
            continue
        has_interface_relation = any(
            rel.relationship_type == "interacts_via"
            and rel.source_artefact_id == relationship.source_artefact_id
            and rel.target_artefact_id == relationship.target_artefact_id
            for rel in context.relationships
        )
        has_interface_artefact = any(
            context.artefact_by_ref(
                context.payload_value(interface, "source_component_id")
                or context.payload_value(interface, "source_component")
            )
            is source
            and context.artefact_by_ref(
                context.payload_value(interface, "destination_component_id")
                or context.payload_value(interface, "destination_component")
            )
            is target
            for interface in context.by_type.get("InterfaceContract", [])
        )
        if not has_interface_relation and not has_interface_artefact:
            issues.append(
                _issue_for_relationship(
                    run,
                    "AAC-RULE-RULE-022",
                    relationship,
                    "Component interaction has no InterfaceContract",
                )
            )
    return issues


def _rule_023(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for interface in context.by_type.get("InterfaceContract", []):
        source_id = context.payload_value(interface, "source_component_id") or context.payload_value(interface, "source_component")
        dest_id = context.payload_value(interface, "destination_component_id") or context.payload_value(interface, "destination_component")
        source = context.artefact_by_ref(source_id)
        dest = context.artefact_by_ref(dest_id)
        if (
            not source
            or not dest
            or source.artefact_type != "SoftwareComponent"
            or dest.artefact_type != "SoftwareComponent"
            or source_id == dest_id
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-023",
                    interface,
                    "InterfaceContract source or destination component is invalid",
                )
            )
    return issues


def _rule_024(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for interface in context.by_type.get("InterfaceContract", []):
        data_elements = (
            context.payload_value(interface, "data_elements", [])
            or context.payload_value(interface, "payload_definition", [])
            or []
        )
        invalid_elements = [
            element
            for element in data_elements
            if not element.get("name")
            or not element.get("type")
            or (element.get("range") is None and element.get("allowed_range") is None)
        ]
        if not (
            context.payload_value(interface, "payload_type")
            or context.payload_value(interface, "interaction_kind")
        ) or not data_elements or invalid_elements:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-024",
                    interface,
                    "InterfaceContract payload semantics are incomplete",
                )
            )
    return issues


def _rule_025(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for interface in context.by_type.get("InterfaceContract", []):
        source = context.artefact_by_ref(
            context.payload_value(interface, "source_component_id")
            or context.payload_value(interface, "source_component")
        )
        dest = context.artefact_by_ref(
            context.payload_value(interface, "destination_component_id")
            or context.payload_value(interface, "destination_component")
        )
        source_class = _component_criticality(context, source)
        dest_class = _component_criticality(context, dest)
        interface_classification = (
            context.payload_value(interface, "criticality_classification")
            or context.payload_value(interface, "classification")
        )
        crosses_qm_to_asil = interface_classification == "QM_to_ASIL" or (
            source_class == "QM" and dest_class in {"ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"}
        )
        if not crosses_qm_to_asil:
            continue
        validity = context.payload_value(interface, "validity_semantics", {}) or {}
        error_handling = context.payload_value(interface, "error_handling", {}) or {}
        timing = context.payload_value(interface, "timing", {}) or {}
        if not validity.get("invalid_value_behavior") or not error_handling.get("on_invalid"):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-025",
                    interface,
                    "QM-to-ASIL interface is missing failure behavior",
                )
            )
        elif timing.get("timeout_ms") is not None and not error_handling.get("on_timeout"):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-025",
                    interface,
                    "QM-to-ASIL interface timeout behavior is missing",
                )
            )
    return issues


def _rule_026(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for interface in context.by_type.get("InterfaceContract", []):
        timing = context.payload_value(interface, "timing", {}) or {}
        timing_relevant = any(
            timing.get(key) is not None
            for key in (
                "period_ms",
                "deadline_ms",
                "jitter_ms",
                "update_period_ms",
                "timeout_ms",
                "freshness_ms",
                "response_time_ms",
            )
        )
        if not timing_relevant:
            continue
        has_spec = any(
            (
                interface.artefact_id in (context.payload_value(spec, "test_basis_refs", []) or [])
                or interface.source_object_id in (context.payload_value(spec, "test_basis_refs", []) or [])
            )
            and context.payload_value(spec, "timing_verification") is True
            for spec in context.by_type.get("TestSpecification", [])
        )
        if not has_spec and not context.has_pass_test_result_for(interface.artefact_id):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-026",
                    interface,
                    "Timing-relevant interface has no timing verification evidence",
                )
            )
    return issues


def _rule_027(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for interface in context.by_type.get("InterfaceContract", []):
        source = context.artefact_by_ref(
            context.payload_value(interface, "source_component_id")
            or context.payload_value(interface, "source_component")
        )
        dest = context.artefact_by_ref(
            context.payload_value(interface, "destination_component_id")
            or context.payload_value(interface, "destination_component")
        )
        classifications = {_component_criticality(context, component) for component in (source, dest)}
        classifications.discard(None)
        if not classifications.intersection({"ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"}):
            continue
        if not context.has_related(
            interface.artefact_id,
            "references",
            "incoming",
            artefact_type="AssumptionGuaranteeContract",
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-027",
                    interface,
                    "ASIL-relevant interface has no AssumptionGuaranteeContract",
                )
            )
    return issues


def _rule_030(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-030",
            artefact,
            "Assumption has no safeguard or test coverage",
        )
        for artefact in context.by_type.get("Assumption", [])
        if not context.has_related(
            artefact.artefact_id,
            "protects",
            "incoming",
            artefact_type="Safeguard",
        )
        and not context.has_related(
            artefact.artefact_id,
            "verifies",
            "incoming",
            artefact_type_in={"TestCase", "TestSpecification"},
        )
    ]


def _rule_031(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for contract in context.by_type.get("AssumptionGuaranteeContract", []):
        guarantees = context.payload_value(contract, "guarantees", []) or []
        untraced = [guarantee for guarantee in guarantees if not guarantee.get("satisfies_refs")]
        if untraced:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-031",
                    contract,
                    "AssumptionGuaranteeContract contains guarantees without requirement or safeguard mapping",
                )
            )
    return issues


def _rule_032(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for safeguard in context.by_type.get("Safeguard", []):
        components = context.related(
            safeguard.artefact_id,
            "allocates_to",
            "outgoing",
            artefact_type="SoftwareComponent",
        )
        if not components or any(
            _component_criticality(context, component) not in {"ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"}
            for component in components
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-032",
                    safeguard,
                    "Safeguard is not allocated to an ASIL-classified component",
                )
            )
    return issues


def _rule_033(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-033",
            safeguard,
            "Released safeguard has no implementation evidence",
        )
        for safeguard in context.by_type.get("Safeguard", [])
        if safeguard.status == "released"
        and not context.has_related(
            safeguard.artefact_id,
            "implements",
            "incoming",
            artefact_type="ImplementationItem",
        )
    ]


def _rule_034(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-034",
            safeguard,
            "Released safeguard has no verification evidence",
        )
        for safeguard in context.by_type.get("Safeguard", [])
        if safeguard.status == "released"
        and not (
            context.has_pass_test_result_for(safeguard.artefact_id)
            or context.has_related(
                safeguard.artefact_id,
                "verifies",
                "incoming",
                artefact_type="TestSpecification",
            )
        )
    ]


def _rule_040(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-040",
            unit,
            "SoftwareUnit lacks design or requirement trace",
        )
        for unit in context.by_type.get("SoftwareUnit", [])
        if not context.has_related(
            unit.artefact_id,
            "satisfies",
            "outgoing",
            artefact_type="SoftwareUnitDesign",
        )
        or not context.has_related(
            unit.artefact_id,
            "implements",
            "outgoing",
            artefact_type_in={"SoftwareRequirement", "SoftwareSafetyRequirement"},
        )
    ]


def _rule_041(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for item in context.by_type.get("ImplementationItem", []):
        refs = context.payload_value(item, "source_references", []) or []
        repository_connector_id = context.payload_value(item, "repository_connector_id")
        if context.repository_connectors and (
            not repository_connector_id
            or repository_connector_id not in context.repository_connector_ids
            or not context.payload_value(item, "commit_sha")
            or not context.payload_value(item, "repo_path")
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-041",
                    item,
                    "ImplementationItem is not linked to a configured repository connector, commit, and path",
                )
            )
            continue
        if not refs or any(
            ref.get("reference_type") not in {"source_file", "build_artifact", "configuration_file"}
            or not ref.get("location")
            for ref in refs
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-041",
                    item,
                    "ImplementationItem source references are missing or invalid",
                )
            )
    for ref in context.by_type.get("SourceCodeReference", []):
        repository_connector_id = context.payload_value(ref, "repository_connector_id")
        if context.repository_connectors and (
            not repository_connector_id
            or repository_connector_id not in context.repository_connector_ids
            or not context.payload_value(ref, "commit_sha")
            or not context.payload_value(ref, "repo_path")
        ):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-041",
                    ref,
                    "SourceCodeReference is not linked to a configured repository connector, commit, and path",
                )
            )
    return issues


def _rule_042(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    build_configs = context.by_type.get("BuildConfiguration", [])
    if not build_configs and not context.has_tailoring_not_applicable("BuildConfiguration"):
        return [_issue(run, "AAC-RULE-RULE-042", "BuildConfiguration is absent", [])]
    issues = []
    for build_config in build_configs:
        repository_connector_id = context.payload_value(build_config, "repository_connector_id")
        if repository_connector_id or build_config.source_kind == "repository":
            missing = []
            if not repository_connector_id or repository_connector_id not in context.repository_connector_ids:
                missing.append("repository_connector_id")
            if not (
                context.payload_value(build_config, "source_revision")
                or context.payload_value(build_config, "commit_sha")
            ):
                missing.append("source_revision")
            if not context.payload_value(build_config, "compiler_toolchain"):
                missing.append("compiler_toolchain")
        else:
            required = ["compiler_version", "build_flags", "target_architecture"]
            missing = [
                key
                for key in required
                if not context.payload_value(build_config, key)
            ]
        if missing:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-042",
                    build_config,
                    f"BuildConfiguration is incomplete: {', '.join(missing)}",
                )
            )
    return issues


def _rule_043(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    if context.by_type.get("StaticAnalysisResult") or context.has_type_level_tailoring("StaticAnalysisResult"):
        return []
    return [_issue(run, "AAC-RULE-RULE-043", "Static analysis evidence is absent and not tailored", [])]


def _rule_044(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    if context.by_type.get("CodingGuidelineComplianceRecord") or context.has_type_level_tailoring(
        "CodingGuidelineComplianceRecord"
    ):
        return []
    return [
        _issue(
            run,
            "AAC-RULE-RULE-044",
            "Coding guideline compliance evidence is absent and not tailored",
            [],
        )
    ]


def _rule_050(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for spec in context.by_type.get("TestSpecification", []):
        refs = context.payload_value(spec, "test_basis_refs", []) or []
        if not refs or any(not context.ref_exists(ref) for ref in refs):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-050",
                    spec,
                    "TestSpecification has no valid test basis references",
                )
            )
    return issues


def _rule_051(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-051",
            artefact,
            "TestCase lacks expected result or pass criteria",
        )
        for artefact in context.by_type.get("TestCase", [])
        if not context.payload_value(artefact, "expected_result")
        or not context.payload_value(artefact, "pass_criteria")
    ]


def _rule_052(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for procedure in context.by_type.get("TestProcedure", []):
        environment_ref = context.payload_value(procedure, "test_environment_ref")
        environment = context.artefact_by_ref(environment_ref)
        if not environment or environment.artefact_type != "TestEnvironment":
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-052",
                    procedure,
                    "TestProcedure has no valid TestEnvironment reference",
                )
            )
    return issues


def _rule_053(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for result in context.by_type.get("TestResult", []):
        test_case_ref = context.payload_value(result, "test_case_ref")
        test_spec_ref = context.payload_value(result, "test_spec_ref")
        if context.ref_exists(test_case_ref) or context.ref_exists(test_spec_ref):
            continue
        issues.append(
            _issue_for_artefact(
                run,
                "AAC-RULE-RULE-053",
                result,
                "TestResult references neither a valid TestCase nor TestSpecification",
            )
        )
    return issues


def _rule_054(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    issues = []
    for result in context.by_type.get("TestResult", []):
        if context.payload_value(result, "verdict") != "fail":
            continue
        waiver_ref = context.payload_value(result, "waiver_ref")
        has_defect = context.has_related(
            result.artefact_id,
            "references",
            "outgoing",
            artefact_type="DefectRecord",
        )
        if not has_defect and not context.ref_exists(waiver_ref):
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-054",
                    result,
                    "Failed TestResult has no linked defect or waiver",
                )
            )
    return issues


def _rule_055(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    records = context.by_type.get("RequirementsCoverageRecord", [])
    if not records and not context.has_tailoring_not_applicable("RequirementsCoverageRecord"):
        return [_issue(run, "AAC-RULE-RULE-055", "Requirements coverage record is absent", [])]
    minimum = context.validation_policy.get("requirements_coverage_minimum", 100)
    if records and not any(
        (context.payload_value(record, "coverage_percentage") or 0) >= minimum for record in records
    ):
        return [_issue(run, "AAC-RULE-RULE-055", f"Requirements coverage is below {minimum} percent", [])]
    return []


def _rule_060(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-060",
            change_set,
            "ChangeSet has no impact analysis reference",
        )
        for change_set in context.by_type.get("ChangeSet", [])
        if not context.has_related(
            change_set.artefact_id,
            "references",
            "outgoing",
            artefact_type="ImpactAnalysisResult",
        )
    ]


def _rule_061(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    closed_statuses = {"closed", "wont_fix", "not_reproducible"}
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-061",
            defect,
            "DefectRecord is not closed and lacks resolution description",
        )
        for defect in context.by_type.get("DefectRecord", [])
        if context.payload_value(defect, "status") not in closed_statuses
        and not context.payload_value(defect, "resolution_description")
    ]


def _rule_062(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    if context.mode != "baseline":
        return []
    return [
        _issue_for_artefact(
            run,
            "AAC-RULE-RULE-062",
            artefact,
            "Released artefact lacks current revision and cannot be baselined",
        )
        for artefact in context.artefacts
        if artefact.status == "released" and not artefact.current_revision_id
    ]


def _rule_063(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    records = context.by_type.get("ConfirmationMeasureRecord", [])
    if not records and not context.has_type_level_tailoring("ConfirmationMeasureRecord"):
        return [_issue(run, "AAC-RULE-RULE-063", "Confirmation measure evidence is absent", [])]
    issues = []
    for record in records:
        reviewer = context.payload_value(record, "independent_reviewer_id")
        author = context.payload_value(record, "primary_author_id")
        if not reviewer or reviewer == author:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-063",
                    record,
                    "ConfirmationMeasureRecord lacks independent reviewer evidence",
                )
            )
    return issues


def _rule_070(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    if not context.validation_policy.get("has_cybersecurity_relevance"):
        return []
    issues = []
    for artefact in context.artefacts:
        security_relevant = context.payload_value(artefact, "security_relevant") is True or (
            artefact.artefact_type == "InterfaceContract"
            and context.payload_value(artefact, "security_classification") is not None
        )
        if not security_relevant:
            continue
        has_evidence = context.has_related(
            artefact.artefact_id,
            "references",
            "outgoing",
            artefact_type_in={"CybersecurityManagementEvidence", "CybersecurityInterfaceEvidence"},
        )
        if not has_evidence:
            issues.append(
                _issue_for_artefact(
                    run,
                    "AAC-RULE-RULE-070",
                    artefact,
                    "Cybersecurity-relevant artefact has no cybersecurity evidence",
                )
            )
    return issues


def _rule_071(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    if not context.validation_policy.get("has_software_update_relevance"):
        return []
    if context.by_type.get("SoftwareUpdateManagementEvidence"):
        return []
    return [
        _issue(
            run,
            "AAC-RULE-RULE-071",
            "Software update relevance is enabled but SUMS evidence is absent",
            [],
        )
    ]


def _rule_081(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue(
            run,
            "AAC-RULE-RULE-081",
            f"Open suspect state blocks release for artefact {suspect.artefact_id}",
            [suspect.artefact_id],
        )
        for suspect in context.open_suspects
    ]


def _rule_080(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return [
        _issue(
            run,
            "AAC-RULE-RULE-080",
            f"Released upstream change created open suspect state for artefact {suspect.artefact_id}",
            [suspect.artefact_id],
        )
        for suspect in context.open_suspects
    ]


def _rule_090(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return []


def _rule_091(run: ValidationRun, context: ValidationContext) -> list[ValidationIssue]:
    return []


def _meta_rule_issues(
    run: ValidationRun,
    context: ValidationContext,
    issues: list[ValidationIssue],
) -> list[ValidationIssue]:
    critical_baseline = [
        issue
        for issue in issues
        if issue.rule_id not in {"AAC-RULE-RULE-090", "AAC-RULE-RULE-091"}
        and issue.severity == "critical"
        and "baseline" in issue.blocking_contexts_json
    ]
    critical_release_gate = [
        issue
        for issue in issues
        if issue.rule_id not in {"AAC-RULE-RULE-090", "AAC-RULE-RULE-091"}
        and issue.severity == "critical"
        and "release_gate" in issue.blocking_contexts_json
    ]
    meta_issues = []
    if context.mode == "baseline" and critical_baseline and not context.rule_disabled("AAC-RULE-RULE-090"):
        meta_issues.append(
            _issue(
                run,
                "AAC-RULE-RULE-090",
                f"Baseline contains {len(critical_baseline)} critical blocking issue(s)",
                [],
            )
        )
    if context.mode == "release_gate" and critical_release_gate and not context.rule_disabled("AAC-RULE-RULE-091"):
        meta_issues.append(
            _issue(
                run,
                "AAC-RULE-RULE-091",
                f"Release gate fails because {len(critical_release_gate)} critical issue(s) are open",
                [],
            )
        )
    return meta_issues


RULE_EVALUATORS = {
    "AAC-RULE-RULE-001": _rule_001,
    "AAC-RULE-RULE-002": _rule_002,
    "AAC-RULE-RULE-003": _rule_003,
    "AAC-RULE-RULE-004": _rule_004,
    "AAC-RULE-RULE-005": _rule_005,
    "AAC-RULE-RULE-006": _rule_006,
    "AAC-RULE-RULE-010": _rule_010,
    "AAC-RULE-RULE-011": _rule_011,
    "AAC-RULE-RULE-012": _rule_012,
    "AAC-RULE-RULE-013": _rule_013,
    "AAC-RULE-RULE-014": _rule_014,
    "AAC-RULE-RULE-020": _rule_020,
    "AAC-RULE-RULE-021": _rule_021,
    "AAC-RULE-RULE-022": _rule_022,
    "AAC-RULE-RULE-023": _rule_023,
    "AAC-RULE-RULE-024": _rule_024,
    "AAC-RULE-RULE-025": _rule_025,
    "AAC-RULE-RULE-026": _rule_026,
    "AAC-RULE-RULE-027": _rule_027,
    "AAC-RULE-RULE-030": _rule_030,
    "AAC-RULE-RULE-031": _rule_031,
    "AAC-RULE-RULE-032": _rule_032,
    "AAC-RULE-RULE-033": _rule_033,
    "AAC-RULE-RULE-034": _rule_034,
    "AAC-RULE-RULE-040": _rule_040,
    "AAC-RULE-RULE-041": _rule_041,
    "AAC-RULE-RULE-042": _rule_042,
    "AAC-RULE-RULE-043": _rule_043,
    "AAC-RULE-RULE-044": _rule_044,
    "AAC-RULE-RULE-050": _rule_050,
    "AAC-RULE-RULE-051": _rule_051,
    "AAC-RULE-RULE-052": _rule_052,
    "AAC-RULE-RULE-053": _rule_053,
    "AAC-RULE-RULE-054": _rule_054,
    "AAC-RULE-RULE-055": _rule_055,
    "AAC-RULE-RULE-060": _rule_060,
    "AAC-RULE-RULE-061": _rule_061,
    "AAC-RULE-RULE-062": _rule_062,
    "AAC-RULE-RULE-063": _rule_063,
    "AAC-RULE-RULE-070": _rule_070,
    "AAC-RULE-RULE-071": _rule_071,
    "AAC-RULE-RULE-080": _rule_080,
    "AAC-RULE-RULE-081": _rule_081,
    "AAC-RULE-RULE-090": _rule_090,
    "AAC-RULE-RULE-091": _rule_091,
}


def _issue(
    run: ValidationRun,
    rule_id: str,
    message: str,
    affected_artefact_ids: list[str],
) -> ValidationIssue:
    rule = RULE_CATALOG[rule_id]
    return ValidationIssue(
        project_id=run.project_id,
        validation_run_id=run.validation_run_id,
        rule_id=rule_id,
        severity=rule.severity,
        status="open",
        message=message,
        affected_artefact_ids_json=affected_artefact_ids,
        affected_relationship_ids_json=[],
        blocking_contexts_json=list(rule.blocking_contexts),
        remediation_hint="Correct the artefact or relationship and rerun validation.",
        created_at=datetime.now(UTC),
    )
