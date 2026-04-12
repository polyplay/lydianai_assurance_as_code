from aac_backend.main import create_app
from aac_backend.rules.catalog import RULE_CATALOG


def test_app_exposes_core_routes() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/projects" in paths
    assert "/api/v1/projects/{project_id}/artefacts" in paths
    assert "/api/v1/projects/{project_id}/imports/sphinx" in paths
    assert "/api/v1/projects/{project_id}/validation/run" in paths
    assert "/api/v1/projects/{project_id}/release-gate/run" in paths


def test_app_exposes_documented_mvp_endpoint_methods() -> None:
    app = create_app()
    operations = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }
    expected = {
        ("POST", "/api/v1/auth/login"),
        ("POST", "/api/v1/users/{user_id}/password-reset"),
        ("POST", "/api/v1/users/me/password"),
        ("GET", "/api/v1/projects/{project_id}/schemas"),
        ("PUT", "/api/v1/projects/{project_id}/schemas/{artefact_type}"),
        ("POST", "/api/v1/projects/{project_id}/tailoring-decisions"),
        ("DELETE", "/api/v1/projects/{project_id}/artefacts/{artefact_id}"),
        ("GET", "/api/v1/projects/{project_id}/artefacts/{artefact_id}/revisions"),
        ("POST", "/api/v1/projects/{project_id}/imports/{import_run_id}/decisions"),
        ("POST", "/api/v1/projects/{project_id}/validation/issues/{issue_id}/suppress"),
        ("GET", "/api/v1/projects/{project_id}/trace/{artefact_id}/forward"),
        ("GET", "/api/v1/projects/{project_id}/trace/{artefact_id}/backward"),
        ("POST", "/api/v1/projects/{project_id}/impact"),
        ("GET", "/api/v1/projects/{project_id}/impact/{impact_id}"),
        ("GET", "/api/v1/projects/{project_id}/suspect-states"),
        ("POST", "/api/v1/projects/{project_id}/suspect-states/{suspect_id}/clear"),
        ("POST", "/api/v1/projects/{project_id}/baselines/{baseline_id}/approve"),
        ("POST", "/api/v1/projects/{project_id}/baselines/{baseline_id}/release"),
        (
            "GET",
            "/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/latest",
        ),
        ("POST", "/api/v1/jobs/{job_id}/cancel"),
    }
    assert expected <= operations


def test_rule_catalog_contains_mvp_blocking_rules() -> None:
    assert len(RULE_CATALOG) == 45
    assert "AAC-RULE-RULE-001" in RULE_CATALOG
    assert "AAC-RULE-RULE-004" in RULE_CATALOG
    assert "AAC-RULE-RULE-081" in RULE_CATALOG
    assert RULE_CATALOG["AAC-RULE-RULE-081"].blocking_contexts == ("release_gate",)
