# User Manual

## Audience

This manual is for project users, project leads, and quality engineers who work with assurance evidence in LydianAI Assurance-as-Code.

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

## Project Workflow

The web console is organized as workflow stages:

1. Setup
2. Team
3. Repository
4. Requirements
5. V-model Artefacts
6. Traceability
7. Review And Release
8. Validation
9. Baseline

Some stages may be read-only depending on your role.

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
2. Choose the relevant workflow stage.
3. Select the artefact type.
4. Fill required fields.
5. Save the artefact.

Each content change creates a new revision. Released artefacts have stricter change behavior and may trigger suspect propagation.

## Import Sphinx-Needs Evidence

When your project uses Sphinx-Needs:

1. Export Sphinx-Needs JSON from the documentation build.
2. Open the import workflow.
3. Upload or submit the JSON export.
4. Choose the version update mode:
   - automatic new version
   - ask user for import conflicts
5. Review import diagnostics.

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

1. Open the validation view.
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

Quality engineers normally:

1. Select the baseline.
2. Run release gate.
3. Review blocking issues and suspect states.
4. Confirm all blocking issues are resolved.
5. Release the approved baseline.
6. Publish repository approval when configured.

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

