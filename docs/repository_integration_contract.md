# Repository Integration Contract

## 1. Purpose

The repository integration connects a project in the Assurance-as-Code tool to an external software repository. The tool remains the approval authority for safety, process, cybersecurity, update-management, and test evidence. The repository remains the source for code and build metadata.

The integration shall support a plug-and-play deployment model:

- Admin configures the repository connector during project setup.
- The tool reads repository status, commit metadata, mapping files, code paths, GitHub checks, and commit statuses.
- The tool imports code-related evidence as versioned artefacts.
- The project lead or quality engineer can release a tool baseline and publish the approval result back to the repository without opening the repository UI.

## 2. Supported Provider And Authentication

MVP provider: GitHub.

Supported authentication modes:

| Auth mode | Purpose | Required secret material | Notes |
|---|---|---|---|
| `github_app` | Production integration | GitHub App private key, installation ID, webhook secret | Preferred for checks API and organization deployment. |
| `access_token` | Test or simple deployment | GitHub access token | May publish a commit status if GitHub check-run creation is unavailable for token auth. |

All secret values shall be stored only in the backend encrypted secret store. Secrets shall not be returned by API responses, exported in reports, or written to repository mapping files.

## 3. Data Schemas

### 3.1 Repository Connector Create

Endpoint:

`POST /api/v1/projects/{project_id}/repo-connectors`

```json
{
  "provider": "github",
  "auth_mode": "github_app",
  "name": "org/software-system",
  "owner": "org",
  "repository": "software-system",
  "repository_url": "https://github.com/org/software-system",
  "default_branch": "main",
  "github_app": {
    "app_id": "123456",
    "installation_id": "987654",
    "private_key_pem": "-----BEGIN PRIVATE KEY-----...",
    "webhook_secret": "shared-webhook-secret"
  },
  "scan_policy": {
    "auto_scan_on_push": true,
    "auto_scan_on_pull_request": true
  },
  "mapping_policy": {
    "mapping_file_path": ".aac/repo.yml"
  }
}
```

For access-token mode:

```json
{
  "provider": "github",
  "auth_mode": "access_token",
  "name": "org/software-system",
  "owner": "org",
  "repository": "software-system",
  "repository_url": "https://github.com/org/software-system",
  "default_branch": "main",
  "access_token": {
    "access_token": "ghp_...",
    "webhook_secret": "optional-webhook-secret"
  },
  "scan_policy": {
    "auto_scan_on_push": true,
    "auto_scan_on_pull_request": true
  },
  "mapping_policy": {
    "mapping_file_path": ".aac/repo.yml"
  }
}
```

### 3.2 Repository Connector Response

```json
{
  "repository_connector_id": "RCON_...",
  "project_id": "PROJ_...",
  "provider": "github",
  "auth_mode": "access_token",
  "name": "org/software-system",
  "owner": "org",
  "repository": "software-system",
  "repository_url": "https://github.com/org/software-system",
  "default_branch": "main",
  "app_id": "",
  "installation_id": "",
  "has_access_token": true,
  "has_private_key": false,
  "has_webhook_secret": true,
  "scan_policy": {
    "auto_scan_on_push": true,
    "auto_scan_on_pull_request": true
  },
  "mapping_policy": {
    "mapping_file_path": ".aac/repo.yml"
  },
  "status": "active",
  "last_scan_run_id": "RSCAN_...",
  "last_revision_id": "RREV_..."
}
```

### 3.3 Repository Status Response

Endpoint:

`GET /api/v1/projects/{project_id}/repo-connectors/{connector_id}/status`

```json
{
  "repository_connector": {},
  "repository": {
    "full_name": "org/software-system",
    "default_branch": "main",
    "private": false,
    "html_url": "https://github.com/org/software-system"
  },
  "repository_state": "reachable",
  "latest_revision": {
    "repository_revision_id": "RREV_...",
    "commit_sha": "abc123",
    "branch": "main",
    "mapping_fingerprint": "sha256..."
  },
  "current_ref": "main",
  "current_commit": {
    "commit_sha": "abc123",
    "message": "update software",
    "author": "Developer",
    "timestamp": "2026-04-19T08:00:00Z",
    "html_url": "https://github.com/org/software-system/commit/abc123"
  },
  "github_checks": [
    {
      "id": 123,
      "name": "AAC Release Approval",
      "status": "completed",
      "conclusion": "success",
      "html_url": "https://github.com/org/software-system/runs/123"
    }
  ],
  "github_status": {
    "state": "success",
    "total_count": 1,
    "statuses": [
      {
        "context": "AAC Release Approval",
        "state": "success",
        "description": "Baseline approved in Assurance-as-Code",
        "target_url": "https://tool.example/projects/PROJ_..."
      }
    ]
  },
  "diagnostics": []
}
```

Allowed `repository_state` values:

| State | Meaning |
|---|---|
| `reachable` | Repository metadata and current commit can be read. |
| `empty` | Repository exists but has no commit on the selected branch. |
| `unavailable` | Repository could not be read with the configured credentials. |

### 3.4 Repository Scan Start

Endpoint:

`POST /api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan`

```json
{
  "trigger": "manual",
  "branch": "main",
  "commit_sha": "abc123",
  "pull_request_id": "42"
}
```

### 3.5 Repository Approval Publish

Endpoint:

`POST /api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals`

```json
{
  "baseline_id": "BASE_...",
  "details_url": "https://tool.example/projects/PROJ_.../baselines/BASE_..."
}
```

Response:

```json
[
  {
    "repository_check_run_id": "RCHK_...",
    "repository_connector_id": "RCON_...",
    "project_id": "PROJ_...",
    "release_gate_result_id": "RGATE_...",
    "baseline_id": "BASE_...",
    "commit_sha": "abc123",
    "github_check_run_id": "123456",
    "check_type": "github_check_run",
    "status": "completed",
    "conclusion": "success",
    "details_url": "https://tool.example/projects/PROJ_.../baselines/BASE_...",
    "summary": "Baseline approved in Assurance-as-Code",
    "requested_by": "USER_...",
    "error": null
  }
]
```

Allowed `check_type` values:

| Type | Meaning |
|---|---|
| `github_check_run` | Approval was published as a GitHub check run. |
| `github_commit_status` | Approval was published as a GitHub commit status fallback. |

## 4. Mapping File Schema

Default path: `.aac/repo.yml`.

```yaml
version: 1
implementation_items:
  - id: brake_monitor
    title: Brake monitor implementation
    path: src/brake/monitor.py
    language: Python
    file_type: source
    satisfies:
      - SSR-001
source_references:
  - id: brake_monitor_lines
    title: Brake monitor source lines
    path: src/brake/monitor.py
    lines: 10-80
    language: Python
    implements:
      - brake_monitor
build_configurations:
  - id: ci-main
    title: Main CI build
    workflow: github-actions
    build_ref: .github/workflows/ci.yml
    compiler_toolchain: gcc-13
    build_options:
      optimization: O2
    dependencies:
      - requirements.txt
    artifact_refs:
      - dist/software-system.bin
```

Mapping rules:

- `version` shall be `1`.
- `implementation_items[].path` and `source_references[].path` are mandatory.
- All mapped paths shall exist in the scanned repository tree at the scanned commit.
- `satisfies` links shall reference requirement artefact IDs or source object IDs in the project.
- `implements` links shall reference implementation item IDs or artefact IDs in the project.
- A mapping file change creates a new repository revision fingerprint and may create new artefact revisions.

## 5. State Machines

### 5.1 Connector State

| State | Allowed transitions | Meaning |
|---|---|---|
| `active` | `disabled`, `deleted` | Connector is usable for status, scan, webhook, and approval publishing. |
| `disabled` | `active`, `deleted` | Connector is retained but not used by automatic workflows. |
| `deleted` | none | Connector is soft-deleted and hidden from normal project views. |

### 5.2 Scan Run State

| State | Allowed transitions | Meaning |
|---|---|---|
| `queued` | `running`, `failed` | Scan was accepted and waits for execution. |
| `running` | `completed`, `failed` | Repository metadata and mapping are being read. |
| `completed` | none | Repository revision and mapped artefacts were stored. |
| `failed` | none | Scan failed; diagnostics are stored on the scan run or job. |

Failure conditions:

- Repository cannot be reached.
- Commit or branch cannot be resolved.
- Mapping file is missing.
- Mapping file is invalid YAML or invalid schema.
- Mapping references paths that do not exist at the scanned commit.
- Artefact creation or relationship creation fails validation.

### 5.3 Approval Publish State

| Local status | GitHub outcome | Meaning |
|---|---|---|
| `queued` | not sent | Local check record was created. |
| `completed` | success | Approval was published as a check run or commit status. |
| `failed` | failed API call | Approval could not be published and must be retried after connector correction. |

Approval preconditions:

- Baseline exists in the same project.
- Latest release gate result for the baseline is `passed`.
- Baseline includes at least one repository revision for approval publishing.
- Actor has `admin`, `project_lead`, or `quality_engineer` role.

## 6. GitHub Check And Status Semantics

The release approval context name shall be:

`AAC Release Approval`

For `github_app` authentication, the tool shall publish:

- GitHub check run name: `AAC Release Approval`
- Status: `completed`
- Conclusion: `success`
- Head SHA: the repository commit captured in the baseline
- Summary: baseline ID, baseline name, and release gate approval statement
- Details URL: tool baseline URL when configured

For `access_token` authentication, the tool shall first attempt GitHub check-run creation. If GitHub rejects check-run creation because token authentication does not support it, the tool shall publish a commit status:

- Context: `AAC Release Approval`
- State: `success`
- Description: baseline approved in Assurance-as-Code
- Target URL: tool baseline URL when configured

Branch protection can be configured to require either the check run or the commit status context, depending on deployment mode.

## 7. Conflict And Versioning Rules

Repository data is never edited by the tool. The tool stores evidence derived from repository state.

Versioning rules:

- A repository scan resolves a single commit SHA and stores it as `RepositoryRevision`.
- A baseline snapshots the latest repository revision per active connector.
- If the same commit SHA is scanned again and the mapping fingerprint is unchanged, no new mapped artefact revisions are required.
- If the same source object ID maps to different content, the backend artefact versioning rules create a new artefact revision.
- If mapped paths move or disappear, the scan fails and no approval shall be published for that commit.
- If a baseline contains repository revision A and the repository branch later moves to revision B, the baseline remains linked to revision A.

Conflict handling:

| Conflict | Required behavior |
|---|---|
| Mapping references unknown requirement | Import mapped implementation item, skip unresolved relationship, and report diagnostic. |
| Mapping references missing path | Fail scan before artefact updates. |
| Repository branch moved during scan | Use the resolved commit SHA for all scan actions. |
| Baseline commit differs from current branch head | Publish approval to the baseline commit only, not to the moving branch name. |
| Existing artefact changed by repository scan | Create a new artefact revision using normal backend versioning. |

## 8. API Endpoints

| Method | Path | Role |
|---|---|---|
| `GET` | `/api/v1/projects/{project_id}/repo-connectors` | Project member |
| `POST` | `/api/v1/projects/{project_id}/repo-connectors` | Admin |
| `GET` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Project member |
| `PUT` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Admin |
| `DELETE` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}` | Admin |
| `POST` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/test` | Admin |
| `GET` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/status` | Project member |
| `POST` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan` | Admin, project lead |
| `GET` | `/api/v1/projects/{project_id}/repo-connectors/{connector_id}/scans/{scan_id}` | Project member |
| `GET` | `/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals` | Project member |
| `POST` | `/api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals` | Admin, project lead, quality engineer |
| `GET` | `/api/v1/projects/{project_id}/repo-checks/{check_id}` | Project member |
| `POST` | `/api/v1/integrations/github/webhook/{connector_id}` | GitHub webhook |

## 9. Deployment Acceptance Criteria

| ID | Criterion |
|---|---|
| REPO-ACC-001 | Admin can create a GitHub connector using GitHub App credentials. |
| REPO-ACC-002 | Admin can create a GitHub connector using an access token for test deployments. |
| REPO-ACC-003 | Connector responses never return private key, access token, or webhook secret values. |
| REPO-ACC-004 | Repository status reads current repository metadata, current commit, checks, and combined status. |
| REPO-ACC-005 | Empty repositories are reported as `repository_state = empty` instead of causing an unhandled error. |
| REPO-ACC-006 | Manual scan imports implementation, source reference, build configuration, and relationships from `.aac/repo.yml`. |
| REPO-ACC-007 | Scan fails when `.aac/repo.yml` references a missing repository path. |
| REPO-ACC-008 | Baseline creation snapshots the latest repository revision for every active connector. |
| REPO-ACC-009 | Release is blocked unless the latest release gate result for the baseline passed. |
| REPO-ACC-010 | Project lead or quality engineer can release a baseline and publish repository approval from the tool. |
| REPO-ACC-011 | GitHub App deployments publish `AAC Release Approval` as a check run. |
| REPO-ACC-012 | Access-token deployments publish `AAC Release Approval` as a commit status fallback when check runs are unavailable. |
| REPO-ACC-013 | Approval is published to the exact baseline commit SHA, not to a mutable branch name. |
| REPO-ACC-014 | Webhooks are rejected when signature verification fails. |
| REPO-ACC-015 | Repository connector, scan, webhook, revision, and approval events are auditable in backend storage. |
