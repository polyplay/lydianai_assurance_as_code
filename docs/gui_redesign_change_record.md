# GUI Redesign Change Record

## Classification And Approval

- Change class: `Class D`
- Rationale: the change replaces the browser presentation architecture and adds
  public read-only API metadata used to render authorization-aware workflows.
- Requirements approval: the user approved the full workflow redesign plan.
- Architecture approval: the same approval selected modular ES modules, a
  server-owned workspace/capability projection, canonical UI schema metadata,
  WCAG 2.2 AA, and direct replacement of `/app`.

## Stakeholder Needs

| ID | Stakeholder | Need |
|---|---|---|
| `NEED-UI-001` | Project user | Complete routine evidence work without understanding API payloads or manually loading each resource. |
| `NEED-UI-002` | Project lead | See project blockers, pending decisions, and release readiness as task-oriented work. |
| `NEED-UI-003` | Quality engineer | Review validation, suspect, baseline, gate, release, and repository-publication state without ambiguous combined actions. |
| `NEED-UI-004` | Administrator | Configure projects, members, schemas, and repository connections through guided controls while retaining advanced technical detail. |
| `NEED-UI-005` | Keyboard or assistive-technology user | Operate and understand the web application with equivalent access to status, errors, and controlled actions. |
| `NEED-DEV-UI-001` | Developer | Change one web workflow without editing unrelated workflows or duplicating backend policy in JavaScript. |

## Requirements Delta

This change adds `AAC-UI-FR-004` through `AAC-UI-FR-010` in
`requirements_baseline.md` and `ACC-UI-005` through `ACC-UI-010` in
`mvp_acceptance_criteria.md`.

No lifecycle, authorization, release, validation, import, or persistence rule is
changed. The web application remains an API client. Hidden and disabled controls
remain usability aids; the server remains authoritative.

Feasibility review found that the existing `user_roles(project_id=None)` helper
mixed memberships from every project into the value named `global_roles`.
This contradicted the authorization matrix and would have made workspace
capabilities project-unsafe. The implementation corrects the helper so global
roles come only from the user record and selected-project calls union only that
project's memberships.

## Architecture Delta

- Decompose `F-WEB-01` into shell, routing/context, versioned API client,
  workspace projection, schema-form rendering, reusable components, and
  independently loaded feature controllers.
- Add `F-WORKSPACE-01` as a read-only API projection over existing project data
  and authorization policy.
- Extend `ISchemaRegistry` with optional presentation metadata that does not
  change payload validation.
- Serve static ES modules and CSS from the existing `/app` mount without a
  production build tool.

## Risks And Mitigations

| Risk | Mitigation |
|---|---|
| Frontend action logic diverges from authorization | Server returns effective roles, capabilities, and resource `allowed_actions`; mutation endpoints still authorize independently. |
| Field metadata becomes another schema authority | Metadata is stored beside canonical field definitions and contract-tested against enabled and mandatory fields. |
| Large browser rewrite regresses workflows | Browser acceptance scenarios cover every workflow required by `AAC-UI-FR-001`. |
| Accessibility regressions | WCAG 2.2 AA automated checks plus keyboard and focus-management scenarios. |
| Static-module cache incompatibility | Use stable module paths during version 1 and preserve backward-compatible API response fields. |

## Verification

The implementation is accepted only when backend contract tests, JavaScript
unit tests, browser end-to-end tests, and applicable repository checks pass.
