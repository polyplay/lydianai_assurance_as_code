import asyncio
from datetime import UTC, datetime
from types import SimpleNamespace

from aac_backend.api.dependencies import CurrentUser
from aac_backend.main import create_app
from aac_backend.models.artefacts import Artefact
from aac_backend.models.baselines import Baseline
from aac_backend.models.projects import Project
from aac_backend.models.validation import ValidationIssue
from aac_backend.services.artefact_schema_service import schema_for_artefact_type
from aac_backend.services.auth_service import user_roles
from aac_backend.services.presentation_policy import (
    artefact_allowed_actions,
    baseline_allowed_actions,
    project_capabilities,
    validation_issue_allowed_actions,
)
from aac_backend.services import workspace_service


class _Scalars:
    def __init__(self, values):
        self.values = values

    def __iter__(self):
        return iter(self.values)


class _WorkspaceSession:
    def __init__(self, project, scalar_groups):
        self.project = project
        self.scalar_groups = list(scalar_groups)

    async def get(self, model, object_id):
        if model is Project and object_id == self.project.project_id:
            return self.project
        return None

    async def scalars(self, _statement):
        return _Scalars(self.scalar_groups.pop(0))


class _RoleSession:
    def __init__(self):
        self.executed = False

    async def get(self, _model, _object_id):
        return SimpleNamespace(global_roles_json=["admin"])

    async def execute(self, _statement):
        self.executed = True
        values = SimpleNamespace(all=lambda: ["quality_engineer"])
        return SimpleNamespace(scalars=lambda: values)


def _current(user_id="USER_1"):
    return CurrentUser(
        user=SimpleNamespace(
            user_id=user_id,
            username="user",
            display_name="Project User",
        ),
        global_roles=[],
    )


def test_workspace_route_is_exposed() -> None:
    paths = {route.path for route in create_app().routes}
    assert "/api/v1/projects/{project_id}/workspace" in paths


def test_global_roles_do_not_include_unscoped_project_memberships() -> None:
    session = _RoleSession()

    global_only = asyncio.run(user_roles(session, "USER_1"))
    project_roles = asyncio.run(user_roles(session, "USER_1", "PROJ_1"))

    assert global_only == ["admin"]
    assert project_roles == ["admin", "quality_engineer"]
    assert session.executed is True


def test_schema_metadata_is_backward_compatible_and_guided() -> None:
    schema = schema_for_artefact_type("SoftwareSafetyRequirement").as_dict()

    assert "statement" in schema["enabled_fields"]
    statement = next(field for field in schema["fields"] if field["name"] == "statement")
    asil = next(field for field in schema["fields"] if field["name"] == "asil_level")
    refs = next(field for field in schema["fields"] if field["name"] == "source_refs")

    assert statement["required"] is True
    assert statement["widget"] == "textarea"
    assert asil["allowed_values"] == ["QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"]
    assert refs["data_type"] == "array"


def test_presentation_actions_mirror_role_and_state_guards() -> None:
    artefact = Artefact(
        artefact_id="ART_1",
        project_id="PROJ_1",
        artefact_type="SoftwareRequirement",
        title="Requirement",
        status="reviewed",
        owner_user_id="USER_1",
        source_object_id="REQ-1",
    )
    baseline = Baseline(
        baseline_id="BASE_1",
        project_id="PROJ_1",
        name="Candidate",
        state="approved",
        release_gate_status="passed",
        created_by="USER_1",
        created_at=datetime.now(UTC),
    )
    issue = ValidationIssue(
        validation_issue_id="VISS_1",
        project_id="PROJ_1",
        rule_id="AAC-RULE-RULE-001",
        severity="critical",
        status="open",
        message="Missing evidence",
        created_at=datetime.now(UTC),
    )

    assert artefact_allowed_actions(
        artefact,
        actor_user_id="USER_1",
        roles=["project_lead"],
    ) == ["edit", "reject", "approve"]
    assert baseline_allowed_actions(baseline, roles=["quality_engineer"]) == ["release"]
    assert validation_issue_allowed_actions(issue, roles=["user"]) == []
    assert validation_issue_allowed_actions(issue, roles=["admin"]) == ["suppress"]
    assert project_capabilities(["quality_engineer"])["baseline.release"] is True
    assert project_capabilities(["quality_engineer"])["baseline.approve"] is False


def test_workspace_projection_reports_work_and_release_blockers(monkeypatch) -> None:
    project = Project(
        project_id="PROJ_1",
        project_key="DEMO",
        name="Demo",
        description="",
        status="active",
    )
    artefact = Artefact(
        artefact_id="ART_1",
        project_id="PROJ_1",
        artefact_type="SoftwareRequirement",
        title="Requirement",
        status="draft",
        source_object_id="REQ-1",
    )
    issue = ValidationIssue(
        validation_issue_id="VISS_1",
        project_id="PROJ_1",
        rule_id="AAC-RULE-RULE-001",
        severity="critical",
        status="open",
        message="Missing evidence",
        blocking_contexts_json=["release_gate"],
        created_at=datetime.now(UTC),
    )
    session = _WorkspaceSession(
        project,
        [
            [artefact],
            [],
            [],
            [issue],
            [],
            [],
            [],
        ],
    )

    async def roles(_session, _user_id, _project_id):
        return ["user"]

    monkeypatch.setattr(workspace_service, "user_roles", roles)
    result = asyncio.run(
        workspace_service.workspace_projection(
            session,
            project_id="PROJ_1",
            current=_current(),
        )
    )

    assert result["actor"]["effective_roles"] == ["user"]
    assert result["summary"]["artefacts"]["total"] == 1
    assert result["summary"]["validation"]["release_blocking"] == 1
    assert result["release_readiness"]["state"] == "blocked"
    assert result["actionable_work"][0]["kind"] == "release_blocker"
