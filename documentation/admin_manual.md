# Administrator Manual

## Audience

This manual is for system administrators and project administrators who configure LydianAI Assurance-as-Code for production use.

This manual derives from stakeholder needs `NEED-OP-001`, `NEED-AUD-001`,
`NEED-UI-004`, `NEED-UI-005`, and `NEED-DEV-UI-001`
and the controlled event, audit, import recovery, and release requirements
listed in `verification/requirements_traceability.yaml`.

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

If no project exists, the first administrator is taken directly to the
first-project form after sign-in.

To create another project:

1. Open **Administration**.
2. Enter project name, key, description, ASIL level, and ASPICE target capability.
3. Create the project.
4. Confirm the project appears in the project selector.

Use clear project keys. They are used in reports, audit trails, and traceability workflows.

## Configure Team Access

1. Open **Administration**.
2. Create a global user account when needed.
3. Select or enter the user under **Team access**.
4. Assign the minimum role needed:
   - `user` for evidence authors and reviewers
   - `quality_engineer` for release-gate and release activities
   - `project_lead` for project workflow and baseline ownership
   - `admin` only for configuration and user-management duties

Review role assignments before release milestones.

## Configure Assurance Scope

1. Open **Administration** and locate **Project defaults**.
2. Set ASIL, Automotive SPICE target capability, cybersecurity relevance, software-update relevance, and visibility policy.
3. Review **ASPICE process scope and expected capability**.
4. Select the Automotive SPICE processes that are in scope for the project.
5. Set the expected capability for each in-scope process when it differs from the project default.
6. Evaluate the active profile.
7. Confirm mandatory, conditional, optional, and not-applicable artefact classes.

The project-level Automotive SPICE target capability is a planning/default value.
It is not a consolidated project assessment rating. The effective evidence scope
comes from the in-scope process list and each process capability target. If no
per-process override exists, the process uses the project default.

Changing the Automotive SPICE default capability, process scope, or process
capability target is controlled tailoring. Before saving such a change, expand
**ASPICE tailoring approval** and enter:

- rationale for the process-scope or capability decision
- at least one evidence reference, such as an assessment scope record, project
  tailoring record, process tailoring plan, or management approval reference

The saving administrator is recorded as the approver. The tool records approved
tailoring decisions and audit events for the changed process scope and capability
targets.

Use tailoring decisions when a mandatory class is genuinely not applicable. Tailoring decisions must include rationale and evidence references.

## Repository Connector Setup

Admins configure GitHub repository connectors in **Administration**.

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

Audit events and domain events are separate records. Audit entries identify the
actor, role at the time of action, operation, request, and correlation context.
Domain events are delivered from the PostgreSQL outbox with retry and
idempotency records. Failed or dead-lettered delivery must be investigated; it
must not be treated as a rollback of the originating state change.

## Security Practices

- Use unique accounts, not shared admin credentials.
- Use GitHub Apps rather than broad personal access tokens in production.
- Rotate connector secrets when staff or repository access changes.
- Keep production `.env` files outside normal user access.
- Back up the database before upgrades.
- Verify backup restoration on a regular schedule.
