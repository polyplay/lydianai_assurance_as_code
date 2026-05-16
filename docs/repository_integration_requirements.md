# Repository Integration Requirements

## Purpose

The tool shall support plug-and-play integration with a software code repository so that implementation evidence can be imported into the assurance database and linked to requirements, architecture, verification, baselines, and release gates.

The MVP repository provider is GitHub. The implementation shall keep a provider boundary so GitLab or local Git integrations can be added later without changing the canonical artefact model. The exact connector schemas, state machines, mapping-file schema, GitHub check semantics, and deployment acceptance criteria are controlled by [Repository Integration Contract](repository_integration_contract.md).

## Scope

The MVP repository integration shall:

- allow an Admin to configure a GitHub repository connector per project
- support GitHub App authentication for production deployments
- support encrypted GitHub access-token authentication for test and simple deployments
- store connector secrets encrypted at rest
- verify GitHub webhook signatures
- support webhook-triggered scans for `push` and `pull_request`
- support manual repository scans by Admin or Project Lead
- read `.aac/repo.yml` from the scanned commit
- create or update canonical `ImplementationItem`, `SourceCodeReference`, and `BuildConfiguration` artefacts
- create traceability relationships from repository mappings
- read current repository status, commit checks, and commit statuses
- publish release approval to GitHub checks or commit statuses where configured
- bind baselines to the exact repository revision included in the project snapshot

The MVP shall not write source code, generated documents, or mapping files back to the repository.

## Roles And Authorization

| Capability | Admin | Project Lead | Quality Engineer | User |
|---|---:|---:|---:|---:|
| View repository connectors | Yes | Yes | Yes | Yes |
| Create repository connector | Yes | No | No | No |
| Update repository connector | Yes | No | No | No |
| Soft-delete repository connector | Yes | No | No | No |
| Test repository connector | Yes | No | No | No |
| Read repository status | Yes | Yes | Yes | Yes |
| Trigger manual repository scan | Yes | Yes | No | No |
| Publish repository approval | Yes | Yes | Yes | No |
| Receive GitHub webhook | System | System | System | System |

## Connector Configuration

A `RepositoryConnector` shall include provider, project identifier, name, owner, repository, repository URL, default branch, authentication mode, GitHub App ID where applicable, installation ID where applicable, encrypted private key secret reference where applicable, encrypted access token secret reference where applicable, encrypted webhook secret reference, scan policy, mapping policy, status, last scan reference, and last repository revision reference.

Connector secret values shall never be returned by an API response or displayed after submission in the web console.

## Repository Mapping File

The default mapping file path shall be `.aac/repo.yml`.

The mapping file shall be versioned in the software repository and read from the exact commit being scanned.

Minimum supported structure:

```yaml
version: 1
implementation_items:
  - id: brake_monitor
    path: src/brake/monitor.py
    language: python
    satisfies:
      - SSR-001
source_references:
  - path: src/brake/monitor.py
    lines: 10-80
    implements:
      - brake_monitor
build_configurations:
  - id: ci-main
    workflow: github-actions
    build_ref: main
```

The scanner shall reject a mapping file when the YAML root is not an object, the version is unsupported, entries are not objects, required paths are omitted, or a referenced path does not exist in the scanned repository tree when tree data is available.

## API Endpoints

The API shall provide:

- `GET /api/v1/projects/{project_id}/repo-connectors`
- `POST /api/v1/projects/{project_id}/repo-connectors`
- `GET /api/v1/projects/{project_id}/repo-connectors/{connector_id}`
- `PUT /api/v1/projects/{project_id}/repo-connectors/{connector_id}`
- `DELETE /api/v1/projects/{project_id}/repo-connectors/{connector_id}`
- `POST /api/v1/projects/{project_id}/repo-connectors/{connector_id}/test`
- `GET /api/v1/projects/{project_id}/repo-connectors/{connector_id}/status`
- `POST /api/v1/projects/{project_id}/repo-connectors/{connector_id}/scan`
- `GET /api/v1/projects/{project_id}/repo-connectors/{connector_id}/scans/{scan_id}`
- `GET /api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals`
- `POST /api/v1/projects/{project_id}/baselines/{baseline_id}/repository-approvals`
- `GET /api/v1/projects/{project_id}/repo-checks/{check_id}`
- `POST /api/v1/integrations/github/webhook/{connector_id}`

All request and response bodies shall use JSON, except GitHub webhook payloads which shall be accepted as raw JSON bytes for signature verification before parsing.

## Webhook Behavior

The GitHub webhook endpoint shall verify `X-Hub-Signature-256`, record each delivery ID and payload hash, reject invalid signatures with HTTP 401, ignore unsupported event types after recording the delivery, and enqueue a repository scan for configured `push` and `pull_request` events.

For a `push` event, the scan commit shall be the payload `after` SHA.

For a `pull_request` event, the scan commit shall be the pull request head SHA.

## Canonical Artefact Mapping

Repository scans shall create or update `ImplementationItem`, `SourceCodeReference`, and `BuildConfiguration` artefacts.

Repository-sourced artefacts shall include repository connector ID, repository URL, repository path, commit SHA, branch where known, source document `repo:{connector_id}`, source kind `repository`, and source tool `github`.

The scanner shall create relationships:

- `ImplementationItem implements SoftwareRequirement|SoftwareSafetyRequirement` from `implementation_items[].satisfies`
- `SourceCodeReference references ImplementationItem` from `source_references[].implements`

## Validation And Release Gate

When a project has an active repository connector, `ImplementationItem` and `SourceCodeReference` shall reference a configured connector, commit SHA, and repository path. `BuildConfiguration` shall include repository revision evidence. Baselines shall snapshot active repository revisions. A released baseline shall be able to publish repository approval only when the latest release gate result passed.

## Baseline Behavior

When creating a baseline, the tool shall store the latest scanned repository revision for every active repository connector in the project. The baseline repository snapshot shall include baseline ID, connector ID, repository revision ID, and commit SHA.

## Security Requirements

The backend shall encrypt GitHub private keys, GitHub access tokens, and webhook secrets at rest, never log connector secrets, never return connector secrets in API responses, verify webhook signatures before state-changing webhook processing, use least-privilege GitHub App permissions, and audit connector creation, update, scan completion, approval publishing, and webhook receipt.

Required GitHub App permissions for MVP:

- repository metadata: read
- contents: read
- checks: write
- pull requests: read

Required GitHub App events for MVP:

- push
- pull_request
