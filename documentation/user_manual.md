# User Manual

## Audience

This manual is for project users, project leads, and quality engineers who work with assurance evidence in LydianAI Assurance-as-Code.

This manual derives from stakeholder needs `NEED-USER-001`, `NEED-QE-001`,
`NEED-UI-001`, `NEED-UI-002`, `NEED-UI-003`, and `NEED-UI-005`
and the controlled authorization, import, job, baseline, and release requirements
listed in `verification/requirements_traceability.yaml`.

## Role Capabilities

### User

Users can normally:

- view assigned projects
- create and update draft artefacts
- create traceability relationships
- view validation issues
- view traceability and reports
- contribute evidence and review data

### Project Lead

Project leads can also:

- manage project workflow
- trigger imports and repository scans
- create baselines
- approve baselines when release-gate conditions are satisfied

### Quality Engineer

Quality engineers can also:

- run release-gate evaluations
- release approved baselines
- publish repository approval checks/statuses
- review release-blocking validation evidence

Your exact permissions depend on project role assignment.

## Sign In

1. Open the web console URL provided by your administrator.
2. Enter your username and password.
3. Select your project.

If you cannot see a project, ask an admin to confirm your role assignment.

## Project Workspace

After project selection, **Overview** displays active jobs, pending import
decisions, validation blockers, suspect states, and release readiness. Data
loads automatically; use the refresh control only when an immediate reload is
needed.

The navigation is organized by task:

- **Workspace**: Overview, My Work, and Jobs
- **Evidence**: Artefacts and Relationships, Imports, and Traceability
- **Assurance**: Validation, Impact and Suspects, and Release
- **Management**: role-appropriate project administration

Controls are shown from server-provided capabilities and resource actions. The
server validates the role and current lifecycle state again when an action is
submitted.

## Understand Assurance Scope

The project assurance scope controls which artefacts, relationships, and
validation rules are expected. It is derived from:

- ISO 26262 ASIL level
- Automotive SPICE target capability and in-scope processes
- UNECE R155 and R156 applicability
- test scope and project visibility policy

For Automotive SPICE, the project-level target capability is a default planning
value. The effective expectation is the per-process capability target configured
for each in-scope Automotive SPICE process. For example, a project may use CL2 as
the default while one process is explicitly targeted at CL3.

Validation issues and release-gate blockers use the effective project
configuration. If the configured scope requires a process at CL3, the tool may
require process definition/deployment evidence such as `ASPICEScopeDecision` and
`ProcessComplianceRecord`. If a required artefact or process expectation is not
applicable to the project, ask a project lead or administrator to record a
documented tailoring decision with rationale and evidence. Do not work around the
issue by deleting evidence, weakening traceability, or suppressing a validation
issue without approval.

## Create Artefacts

Artefacts are canonical evidence records. Examples include:

- Software requirements
- Software safety requirements
- Architecture elements
- Software units
- Implementation items
- Source code references
- Test specifications
- Test cases
- Test results
- Build configurations

To create an artefact:

1. Select the project.
2. Open **Artefacts and Relationships**.
3. Select the artefact type.
4. Fill the guided canonical fields. Required fields are marked.
5. Save the artefact.

Use **Advanced JSON override** only when a guided field does not represent the
required structured payload. The canonical schema remains authoritative.

Each content change creates a new revision. Released artefacts have stricter change behavior and may trigger suspect propagation.

## Import Sphinx-Needs Evidence

When your project uses Sphinx-Needs:

1. Export Sphinx-Needs JSON from the documentation build.
2. Open **Imports**.
3. Upload or submit the JSON export.
4. Choose the version update mode:
   - automatic new version
   - ask user for import conflicts
5. Review import diagnostics.

Only the original import submitter, a quality engineer, or an administrator may
submit import decisions. Revising a released artefact through import requires a
quality engineer or administrator. Cancelling an import is limited to its
requester or an administrator, and the cancellation result identifies any
already committed batches.

Imported content is not canonical until it is normalized, validated, and persisted by the backend.

## Repository Evidence

If a project has a repository connector, repository scans can import code evidence from `.aac/repo.yml`.

Repository scans can create:

- `ImplementationItem`
- `SourceCodeReference`
- `BuildConfiguration`
- relationships from code evidence to requirements and implementation items

Project leads can trigger manual repository scans. Users can view imported repository evidence.

## Traceability

Traceability shows how assurance evidence connects across lifecycle layers.

Common chains include:

```text
SafetyGoal -> TechnicalSafetyRequirement -> SoftwareSafetyRequirement -> SoftwareComponent -> ImplementationItem -> TestResult
```

Use forward trace from an upstream artefact to see downstream implementation and verification coverage. Use backward trace from a test result or implementation item to see the requirement basis.

## Validation Issues

Validation runs check evidence completeness and consistency.

Issue severity:

- critical: normally blocks baseline or release
- major: significant gap requiring review
- minor/info: lower-risk gap or advisory finding

Typical actions:

1. Open **Validation**.
2. Review issue message, affected artefacts, and rule ID.
3. Fix missing artefacts, fields, or relationships.
4. Re-run validation.
5. Ask a project lead/admin about suppression only when a documented waiver is justified.

## Baselines

A baseline freezes the current project state for review or release.

Baseline creation captures:

- current artefact revisions
- current relationship revisions
- validation summary
- suspect-state summary
- repository revision snapshots

Project leads create baselines after evidence is complete enough for review.

## Release Gate

The release gate evaluates whether a baseline can be released.

The **Release** workspace presents each available action separately. Quality
engineers normally:

1. Select the baseline.
2. Run release gate.
3. Review blocking issues and suspect states.
4. Confirm all blocking issues are resolved.
5. Have a project lead or administrator approve the current gate result.
6. Have a quality engineer or administrator release the approved baseline.
7. Publish repository approval when configured.

Releasing a baseline does not publish repository approval automatically.

A later blocking-relevant change makes a passed gate stale and invalidates an
existing approval. The gate must pass again and the baseline must be re-approved
before release.

Release approval is published to the exact commit captured in the baseline, not to a moving branch name.

## Reports

Users can generate reports for:

- traceability
- validation status
- baseline comparison
- release-gate status
- audit and evidence summaries

Use reports during reviews and release readiness meetings.

## Good Evidence Practices

- Use stable artefact IDs and clear titles.
- Link implementation and tests back to requirements.
- Keep source references specific enough to review.
- Add rationale for safety and cybersecurity decisions.
- Resolve validation issues before baseline creation.
- Do not suppress issues without documented approval.
