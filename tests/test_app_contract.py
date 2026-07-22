from aac_backend.main import create_app
from aac_backend.rules.catalog import RULE_CATALOG


def test_app_exposes_core_routes() -> None:
    app = create_app()
    paths = {route.path for route in app.routes}
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/projects" in paths
    assert "/api/v1/projects/{project_id}/artefacts" in paths
    assert "/api/v1/projects/{project_id}/imports/sphinx" in paths
    assert "/api/v1/projects/{project_id}/workspace" in paths
    assert "/api/v1/projects/{project_id}/validation/run" in paths
    assert "/api/v1/projects/{project_id}/release-gate/run" in paths
    assert "/app" in paths


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
        ("GET", "/api/v1/projects/{project_id}/workspace"),
        ("GET", "/api/v1/projects/{project_id}/schemas/{artefact_type}"),
        ("PUT", "/api/v1/projects/{project_id}/schemas/{artefact_type}"),
        ("PUT", "/api/v1/projects/{project_id}"),
        ("POST", "/api/v1/projects/{project_id}/tailoring-decisions"),
        (
            "POST",
            "/api/v1/projects/{project_id}/tailoring-decisions/{tailoring_decision_id}/approve",
        ),
        ("GET", "/api/v1/projects/{project_id}/profiles"),
        ("POST", "/api/v1/projects/{project_id}/profiles"),
        ("GET", "/api/v1/projects/{project_id}/profiles/{profile_id}"),
        ("PUT", "/api/v1/projects/{project_id}/profiles/{profile_id}"),
        ("POST", "/api/v1/projects/{project_id}/profiles/{profile_id}/evaluate"),
        ("GET", "/api/v1/projects/{project_id}/standards-references"),
        ("POST", "/api/v1/projects/{project_id}/standards-references"),
        ("PUT", "/api/v1/projects/{project_id}/standards-references/{standards_reference_id}"),
        ("GET", "/api/v1/projects/{project_id}/standards-mappings"),
        ("PUT", "/api/v1/projects/{project_id}/standards-mappings"),
        ("DELETE", "/api/v1/projects/{project_id}/artefacts/{artefact_id}"),
        ("GET", "/api/v1/projects/{project_id}/artefacts/{artefact_id}/revisions"),
        ("POST", "/api/v1/projects/{project_id}/imports/{import_run_id}/decisions"),
        ("POST", "/api/v1/projects/{project_id}/validation/issues/{issue_id}/suppress"),
        ("GET", "/api/v1/projects/{project_id}/trace/{artefact_id}/forward"),
        ("GET", "/api/v1/projects/{project_id}/trace/{artefact_id}/backward"),
        ("POST", "/api/v1/projects/{project_id}/relationships/{relationship_id}/compare"),
        ("POST", "/api/v1/projects/{project_id}/impact"),
        ("GET", "/api/v1/projects/{project_id}/impact/{impact_id}"),
        ("GET", "/api/v1/projects/{project_id}/suspect-states"),
        ("POST", "/api/v1/projects/{project_id}/suspect-states/{suspect_id}/clear"),
        ("POST", "/api/v1/projects/{project_id}/baselines/{baseline_id}/approve"),
        ("POST", "/api/v1/projects/{project_id}/baselines/{baseline_id}/cancel"),
        ("POST", "/api/v1/projects/{project_id}/baselines/{baseline_id}/release"),
        ("POST", "/api/v1/projects/{project_id}/test-results/import"),
        ("GET", "/api/v1/projects/{project_id}/test-results"),
        ("POST", "/api/v1/projects/{project_id}/evidence/upload"),
        ("GET", "/api/v1/projects/{project_id}/audit-events"),
        (
            "GET",
            "/api/v1/projects/{project_id}/baselines/{baseline_id}/release-gate/results/latest",
        ),
        ("GET", "/api/v1/projects/{project_id}/repo-connectors"),
        ("POST", "/api/v1/projects/{project_id}/repo-connectors"),
        ("GET", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}"),
        ("PUT", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}"),
        ("DELETE", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}"),
        ("POST", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}/test"),
        ("GET", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}/status"),
        ("POST", "/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan"),
        (
            "GET",
            "/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scans/{scan_id}",
        ),
        (
            "GET",
            "/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals",
        ),
        (
            "POST",
            "/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals",
        ),
        ("GET", "/api/v1/projects/{project_id}/repo-checks/{check_id}"),
        ("POST", "/api/v1/integrations/github/webhook/{connector_id}"),
        ("POST", "/api/v1/jobs/{job_id}/cancel"),
    }
    assert expected <= operations


def test_rule_catalog_contains_mvp_blocking_rules() -> None:
    assert len(RULE_CATALOG) == 45
    assert "AAC-RULE-RULE-001" in RULE_CATALOG
    assert "AAC-RULE-RULE-004" in RULE_CATALOG
    assert "AAC-RULE-RULE-081" in RULE_CATALOG
    assert RULE_CATALOG["AAC-RULE-RULE-081"].blocking_contexts == ("release_gate",)
