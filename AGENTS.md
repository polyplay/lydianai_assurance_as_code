# Project Change Rules

These rules apply to every change in this repository. Evaluate work in this
order:

1. Requirements
2. Software architecture
3. Implementation and verification

Applicable gates shall proceed in this order. An unaffected gate may be closed
by a documented impact assessment instead of an artifact rewrite. If a request
conflicts with these rules, stop at the earliest affected gate and resolve the
conflict before changing production code.

## Change Classification

### GOV-CLASS-001: Assign A Change Class

Classify every change before production modification:

| Class | Definition | Minimum Process |
|---|---|---|
| `A` | Editorial, formatting, test-only, fixture, or build-support change with no product behavioral impact | Record no behavioral impact; change and run relevant verification |
| `B` | Implementation or refactoring fully covered by approved requirements and architecture with no externally observable contract change | Reference existing requirement, acceptance, and architecture IDs; implement and verify |
| `C` | Externally observable behavior or contract change without a material architecture change | Update and approve requirements; assess architecture impact; update architecture only if affected; implement and verify |
| `D` | Architecture, persistence, security behavior/control/boundary, interoperability, public integration, deployment, or other high-impact system change | Update and approve requirements and architecture; implement and verify |

Classification is based on actual impact, not filename, apparent size, or change
type. An accessibility-label change, for example, is Class B when it implements
an approved accessibility requirement and Class C when it introduces new
externally observable behavior.

### GOV-CLASS-002: Escalate Classification

When classification is uncertain, use the higher plausible class and record the
reason. Reclassify immediately if investigation reveals broader behavioral,
security, persistence, interoperability, deployment, or architecture impact.

## Gate Operation And Approval

### GOV-GATE-001: Sequential Gates

Applicable requirements, software architecture, and implementation gates shall
not overlap for the same controlled decision. Independent analysis, review,
feasibility, and verification tasks may run in parallel within the active gate
when they do not depend on an unapproved later-gate decision.

### GOV-GATE-002: Controlled Phase Artifacts

At the end of each applicable changed gate, produce a proportionate structured
artifact or an explicit delta to an existing controlled artifact:

- Class A: no-behavioral-impact statement and relevant verification result.
- Class B: references to approved requirements, acceptance criteria,
  architecture, code, and verification.
- Requirements gate for Class C/D: stakeholder needs, requirements, acceptance
  criteria, and affected traceability.
- Architecture gate: architecture description or delta, including functions,
  interfaces, views, dependency maps, decisions, and risks affected.
- Implementation gate: code, migrations, tests, verification evidence, and
  traceability updates.

The artifact shall reference the controlling artifacts from preceding gates.

### GOV-GATE-003: Proportional Approval

Request explicit approval before advancing from:

- requirements to architecture when product scope or externally observable
  behavior is added, removed, or materially changed;
- architecture to implementation when responsibilities, interfaces, dependency
  direction, data ownership, state machines, technology, or deployment are
  materially changed.

Routine implementation already covered by approved requirements and architecture
does not require another approval unless the user or project policy requests it.
An explicit user request to implement such Class B work counts as approval to
proceed.

### GOV-GATE-004: Formal Return To An Earlier Gate

If a later gate reveals a gap, conflict, or infeasible assumption in an earlier
artifact, stop the later-gate work, return to the affected gate, update its
controlled artifact, obtain approval when `GOV-GATE-003` applies, and then
resume sequentially. Do not silently rewrite an earlier decision from a later
gate.

### GOV-GATE-005: Investigation And Disposable Spikes

Read-only investigation and isolated disposable technical spikes may occur
before gate approval to establish feasibility or discover impact, provided:

- no spike code is merged, shipped, or treated as production implementation;
- the spike does not modify canonical production data or production migrations;
- the spike does not become the architecture implicitly;
- assumptions, findings, risks, and discarded approaches are returned to the
  appropriate controlled gate;
- any discovered increase in impact triggers reclassification under
  `GOV-CLASS-002`.

## Gate 1: Requirements First

### GOV-REQ-001: Establish Requirement Traceability

Before any implementation change:

- Identify the requirement IDs and acceptance criteria affected by the change.
- If no requirement covers the requested behavior, add or update the requirements first.
- Identify every requirements, API, data, state-machine, authorization, security,
  deployment, and acceptance document affected by the change.
- Record whether the change adds, modifies, supersedes, or removes behavior.
- Do not implement behavior that has no controlling requirement.

Class A changes may state that they have no behavioral requirement impact and
that requirement IDs are not applicable, but this determination must still be
made explicitly.

### GOV-REQ-002: Requirement Quality

Every new or changed requirement shall be:

- **Necessary**: represents a stakeholder or system need that justifies its cost.
- **Unambiguous**: uses one testable interpretation, controlled terminology, and
  explicit actors.
- **Correct**: represents the intended system behavior and applicable constraints.
- **Complete**: defines relevant inputs, outputs, preconditions, postconditions,
  state changes, failure behavior, authorization, data integrity, security,
  performance, and audit behavior.
- **Consistent**: does not contradict another active requirement, decision,
  schema, state machine, API contract, or acceptance criterion.
- **Singular/Atomic**: expresses one independently verifiable obligation where
  practical.
- **Feasible**: can be implemented and operated within known technical, schedule,
  security, and regulatory constraints.
- **Verifiable/Testable**: has objective pass/fail acceptance criteria.
- **Traceable**: has a stable requirement ID and links to architecture,
  implementation, and tests.

### GOV-REQ-003: Contradiction Check

Before requirements are accepted:

- Search the full controlled document set for overlapping rules and terminology.
- Resolve differences in roles, states, enum values, endpoint behavior, payloads,
  error codes, security rules, and lifecycle transitions.
- Define which document is authoritative when several documents cover the same concern.
- Mark superseded requirements as obsolete or superseded; do not silently delete
  or reuse their IDs.
- Do not proceed while known contradictions or unresolved decisions remain.

### GOV-REQ-004: Acceptance Criteria

Each behavioral requirement shall have acceptance criteria that define:

- Given state and preconditions.
- Action or triggering event.
- Expected output and persisted state.
- Expected errors and prohibited outcomes.
- Required audit events and asynchronous jobs.
- Relevant performance or security limits.
- Verification method and test level.

### GOV-REQ-005: Stakeholder Needs And Requirement Levels

For a new application or substantial Class C/D capability:

- Identify stakeholders and document their needs before writing normative
  requirements.
- Derive and distinguish stakeholder requirements (`StRS`), system requirements
  (`SyRS`), and software requirements (`SRS`).
- Preserve derivation links from stakeholder need to system and software
  requirements.

For Class C/D maintenance work, reference the affected stakeholder needs and add
missing needs when requirements are changed. Class A/B work does not require new
stakeholder-level derivation when approved requirements already control it.

Classify each requirement by level (`StRS`, `SyRS`, or `SRS`) and by type:
functional, performance, interface, security, or constraint. This applies to
new or materially changed requirements, not to Class A/B work that creates no
requirement. Separate documents are not mandatory when a single controlled
document preserves explicit IDs, levels, types, and derivation links.

### GOV-REQ-006: Requirements Phase Boundary

Requirements shall define required externally observable behavior and
constraints, not internal implementation mechanisms.

Interface, security, performance, regulatory, interoperability, and deployment
constraints may be specified during requirements work when they are externally
observable or necessary to define acceptance. Internal module structure,
framework selection, algorithms, and persistence mechanisms belong to the
architecture gate.

Technical feasibility analysis may occur during requirements work to test
coherence, identify constraints, and compare candidate approaches. It shall not
silently select the controlled architecture; architecture decisions remain in
Gate 2.

## Gate 2: Software Architecture Before Code

### GOV-ARCH-001: Requirement Allocation

Every affected requirement shall be allocated to one or more explicitly named
software functions or components. The architecture shall show:

- Function or component identifier and responsibility.
- Inputs, outputs, and owned data.
- Public interfaces and calling direction.
- Preconditions, postconditions, and invariants.
- State transitions and failure behavior.
- Authorization, audit, security, and performance responsibilities.
- Requirement IDs implemented by the function.

### GOV-ARCH-002: Interface Contracts

Every public, cross-module, persistent, external, security-relevant, or otherwise
behaviorally significant interface shall define:

- Caller and provider.
- Request, response, event, or job schema.
- Required and optional fields, types, and enum values.
- Validation rules.
- Error and retry behavior.
- Transaction and consistency boundary.
- Versioning and compatibility policy.
- Authentication and authorization expectations.
- Side effects, emitted events, and audit records.

Private implementation boundaries require detailed contracts only when their
complexity or risk warrants it. Code shall not rely on undocumented
cross-module behavior.

### GOV-ARCH-003: Visible Dependency Maps

The architecture documentation shall contain a dependency map for each changed
functionality. The map shall make direct and transitive dependencies visible,
including:

- API or user entry point.
- Application/service function.
- Domain functions and rules.
- Repository and persistence dependencies.
- External systems.
- Events, jobs, and downstream consumers.

Use a maintained diagram, preferably Mermaid, plus a dependency table where
additional detail is needed. New dependency cycles are prohibited unless a
documented architecture decision explains and approves them.

### GOV-ARCH-004: Independent Changeability

Architecture shall permit different capabilities to be changed and tested
independently. Therefore:

- Each component shall have one clear responsibility and owner.
- Components shall communicate through explicit, stable interfaces.
- Business rules shall not depend directly on API, UI, worker, or database framework details.
- API handlers and workers shall orchestrate; domain services shall own behavior.
- Persistence access shall remain behind repository or unit-of-work boundaries.
- Uncontrolled shared mutable state and hidden coupling are prohibited.
- Cross-component changes shall be minimized and justified.
- Optional integrations shall depend on provider interfaces, not provider-specific
  behavior in the canonical domain model.
- A component shall be replaceable without changing unrelated components when
  its published contract is preserved.

### GOV-ARCH-005: Architecture Change Record

If a change affects component responsibilities, interfaces, dependency direction,
data ownership, state machines, technology, or deployment, update the controlled
architecture documents before code. Record significant tradeoffs and rejected
alternatives in an architecture decision.

### GOV-ARCH-006: Stakeholders, Concerns, Viewpoints, And Views

When the architecture gate is applicable, the architecture description shall
identify the stakeholders and concerns relevant to the changed capability.
Examples include:

- User: correctness, usability, and workflow completion.
- Developer: maintainability, testability, and independent changeability.
- Operator: deployment, observability, availability, backup, and recovery.
- Security or Quality Engineer: authorization, auditability, integrity, and
  compliance evidence.

Select proportionate viewpoints for those concerns and provide one or more views
using diagrams, tables, or structured text. Applicable viewpoints may include
logical, process/runtime, data, deployment, security, integration, and
operational views. A small change may update an existing view rather than create
a separate document.

### GOV-ARCH-007: Architecture Decisions And Risks

Every significant architecture decision shall record:

- requirement and stakeholder concern drivers;
- chosen option and rationale;
- considered alternatives;
- trade-offs and consequences;
- architecture risks;
- mitigation, validation, or contingency strategy.

Use a controlled architecture decision record when the decision affects
technology, deployment, data ownership, public interfaces, dependency direction,
or multiple capabilities.

## Gate 3: Implementation From Requirements And Architecture

### GOV-CODE-001: Implement Only The Approved Design

Implementation shall:

- Follow the approved requirements and architecture.
- Preserve documented module boundaries and dependency direction.
- Keep the change scoped to the allocated functions.
- Avoid unrelated refactoring and speculative functionality.
- Reject or explicitly escalate any requirement or architecture ambiguity found
  during implementation.

Code is not a substitute for missing requirements or architecture.

### GOV-CODE-002: Maintain Traceability

For every changed behavior, maintain a trace from:

`requirement -> acceptance criterion -> architecture function/interface -> code -> test`

Tests should reference the applicable requirement or acceptance ID in their name,
marker, docstring, or traceability manifest.

Requirement IDs are not required in every function, class, or test name when an
authoritative traceability manifest provides the same link.

### GOV-CODE-003: Verification

Verification shall cover, as applicable:

- Requirement acceptance tests.
- Interface contract tests.
- Unit tests for changed domain behavior.
- Integration tests for database, jobs, events, and external boundaries.
- Authorization and negative-path tests.
- Migration and backward-compatibility tests.
- Performance and security criteria.
- Regression tests for corrected defects.

Route existence or static code inspection alone is not evidence that a behavioral
acceptance criterion passes.

### GOV-CODE-004: Required Completion Review

A change is complete only when:

- Requirements are updated when affected or explicitly confirmed unaffected,
  and remain contradiction-free.
- Acceptance criteria are updated when affected or existing criteria are
  referenced and remain traceable.
- Architecture functions, interfaces, ownership, and dependency maps are
  updated when affected or explicitly confirmed unaffected.
- Code conforms to the architecture.
- Tests or other relevant verification demonstrate the acceptance criteria and
  the claimed impact; Class A work may record behavioral acceptance as not
  applicable.
- Documentation, schemas, migrations, examples, and operational files affected
  by the changed surface are updated together.
- Lint, test, compile, migration, deployment, performance, and security checks
  applicable to the changed surface and risk class pass.
- Any unverified criterion or residual risk is explicitly reported.

## Mandatory Change Summary

Every completed change shall report:

- Change class and impact rationale.
- Requirements added or changed.
- Contradictions found and how they were resolved.
- Architecture functions and interfaces changed.
- Dependency-map changes.
- Code and data changes.
- Tests run and acceptance criteria demonstrated.
- Remaining gaps or risks.
