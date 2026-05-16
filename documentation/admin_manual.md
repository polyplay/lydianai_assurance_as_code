# Administrator Manual

## Audience

This manual is for system administrators and project administrators who configure LydianAI Assurance-as-Code for production use.

## Admin Responsibilities

Admins can:

- create and manage user accounts
- assign project roles
- create and configure projects
- manage assurance profiles and project configuration
- configure repository connectors
- test integrations
- review audit events
- manage production secrets and backups with the operations team

## First Login

1. Open the web console.
2. Sign in with the admin account created during installation.
3. Change the initial password if your deployment process used a temporary password.
4. Confirm the API health endpoint is reachable.

## Create A Project

1. Open the **Setup** stage.
2. Enter project name, key, description, ASIL level, and process targets.
3. Create the project.
4. Confirm the project appears in the project selector.

Use clear project keys. They are used in reports, audit trails, and traceability workflows.

## Configure Team Access

1. Open the **Team** stage.
2. Create or select users.
3. Assign the minimum role needed:
   - `user` for evidence authors and reviewers
   - `quality_engineer` for release-gate and release activities
   - `project_lead` for project workflow and baseline ownership
   - `admin` only for configuration and user-management duties

Review role assignments before release milestones.

## Configure Assurance Scope

1. Open project configuration.
2. Set ASIL, Automotive SPICE target, cybersecurity relevance, software-update relevance, and visibility policy.
3. Evaluate the active profile.
4. Confirm mandatory, conditional, optional, and not-applicable artefact classes.

Use tailoring decisions when a mandatory class is genuinely not applicable. Tailoring decisions must include rationale and evidence references.

## Repository Connector Setup

Admins configure GitHub repository connectors in the **Repository** stage.

Supported authentication modes:

- GitHub App for production integrations
- access token for test/simple deployments

For GitHub App production setup:

1. Create a GitHub App with repository metadata read, contents read, checks write, and pull requests read permissions.
2. Subscribe the app to `push` and `pull_request` events.
3. Install the app on the target repository.
4. Enter owner, repository, default branch, app ID, installation ID, private key, and webhook secret.
5. Create the connector.
6. Test the connector.
7. Trigger a manual scan.

Connector secret values are encrypted at rest and are never returned by API responses after submission.

## Repository Mapping File

Each connected repository should include:

```text
.aac/repo.yml
```

Minimum example:

```yaml
version: 1
implementation_items:
  - id: brake_monitor
    path: src/brake/monitor.py
    language: python
    satisfies:
      - SSR-001
source_references:
  - id: brake_monitor_lines
    path: src/brake/monitor.py
    lines: 10-80
    implements:
      - brake_monitor
build_configurations:
  - id: ci-main
    workflow: github-actions
    build_ref: .github/workflows/ci.yml
```

Scans import `ImplementationItem`, `SourceCodeReference`, and `BuildConfiguration` artefacts and create traceability relationships where referenced targets exist.

## Validation And Baselines

Admins can inspect validation, but release accountability normally belongs to project leads and quality engineers.

Baseline workflow:

1. Ensure project evidence is complete.
2. Run validation.
3. Resolve blocking issues.
4. Create a baseline.
5. Run release gate.
6. Approve baseline.
7. Release baseline.
8. Publish repository approval where configured.

Baselines snapshot artefact revisions, relationship revisions, validation state, suspect state, release-gate state, and active repository revisions.

## Audit Review

Use audit views and reports to review:

- artefact creation, revision, deletion, and lifecycle changes
- relationship creation and changes
- validation runs
- baseline creation and release-gate results
- suspect propagation and clearance
- repository connector changes
- webhook receipt and repository scan events
- repository approval publishing

Audit events are append-only under normal operation.

## Security Practices

- Use unique accounts, not shared admin credentials.
- Use GitHub Apps rather than broad personal access tokens in production.
- Rotate connector secrets when staff or repository access changes.
- Keep production `.env` files outside normal user access.
- Back up the database before upgrades.
- Verify backup restoration on a regular schedule.

