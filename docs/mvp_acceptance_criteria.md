# MVP Acceptance Criteria

## 1. Purpose

This document resolves blocker B7 identified in the implementation readiness assessment: the absence of measurable acceptance criteria for the MVP.

It defines pass/fail criteria for each major workflow and system characteristic. The MVP shall not be considered complete until all criteria in this document pass.

---

## 2. Criterion Classification

Each criterion is classified as:
- **MUST PASS**: Blocking criterion; MVP is not releasable without this
- **SHOULD PASS**: Strong requirement; failure requires documented waiver before release
- **INFORMATIONAL**: Benchmark or quality target; tracked but not blocking

---

## 3. Functional Acceptance Criteria

### 3.1 Authentication And Authorization

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-AUTH-001 | Admin can create a user account with username/password | MUST PASS | Automated test |
| ACC-AUTH-002 | Admin can assign roles (Admin, Project Lead, Quality Engineer, User) | MUST PASS | Automated test |
| ACC-AUTH-003 | A User with an invalid or expired JWT receives 401 on any protected endpoint | MUST PASS | Automated test |
| ACC-AUTH-004 | A User cannot perform an operation requiring Project Lead role and receives 403 | MUST PASS | Automated test |
| ACC-AUTH-005 | Passwords are stored as bcrypt hashes (not plaintext) | MUST PASS | Code review + DB inspection |
| ACC-AUTH-006 | All role-sensitive operations produce an AuditEvent with actor_id | MUST PASS | Automated test |
| ACC-AUTH-007 | A User cannot edit a released artefact; only Quality Engineer can | MUST PASS | Automated test |

### 3.2 Project And Configuration Management

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-PROJ-001 | Admin can create a project and assign an assurance profile | MUST PASS | Automated test |
| ACC-PROJ-002 | ASIL D default profile is available and cannot be deleted | MUST PASS | Automated test |
| ACC-PROJ-003 | A Project Lead can create a tailoring decision; it requires approval before taking effect | MUST PASS | Automated test |
| ACC-PROJ-004 | An approved not-applicable tailoring decision for a mandatory artefact type suppresses RULE-005 for that type | MUST PASS | Automated test |
| ACC-PROJ-005 | Admin can create a project with ASIL, Automotive SPICE PAM 4.0 capability target, R155/R156 flags, test scope, and visibility policy | MUST PASS | Automated test |
| ACC-PROJ-006 | Profile evaluation returns visible, mandatory, conditional, optional, and not-applicable artefact classes derived from project configuration | MUST PASS | Automated test |
| ACC-PROJ-007 | ASPICE CL3 process targets require PA3.1/PA3.2 evidence artefacts, while CL2 targets do not | MUST PASS | Automated test |

### 3.3 Sphinx Import

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-IMP-001 | A Sphinx-Needs JSON export from a conformant document is accepted and all artefacts created | MUST PASS | Integration test with sample Sphinx-Needs export |
| ACC-IMP-002 | Unchanged re-import of the same document creates no new revisions | MUST PASS | Automated test |
| ACC-IMP-003 | Modified re-import creates new revisions for changed artefacts only | MUST PASS | Automated test |
| ACC-IMP-004 | In `ask_user` mode, a changed import pauses and returns `requires_user_decision` status | MUST PASS | Automated test |
| ACC-IMP-005 | Accepting the decision in `ask_user` mode creates a new revision | MUST PASS | Automated test |
| ACC-IMP-006 | Rejecting the decision in `ask_user` mode leaves the stored revision unchanged | MUST PASS | Automated test |
| ACC-IMP-007 | An artefact absent from a re-import of its source document is soft-deleted | MUST PASS | Automated test |
| ACC-IMP-008 | A type mismatch in an import creates an ImportRunItem with classification=type_mismatch and does not update the stored artefact | MUST PASS | Automated test |
| ACC-IMP-009 | Import of 500 artefacts completes within 120 seconds on the performance test dataset | SHOULD PASS | Performance test |
| ACC-IMP-010 | A failed import transaction (simulated DB error mid-batch) does not leave partial state | MUST PASS | Automated test with DB fault injection |
| ACC-IMP-011 | Post-import, a validation run is automatically enqueued | MUST PASS | Automated test |

### 3.4 Artefact Lifecycle

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-ART-001 | All 50+ canonical artefact types can be created via direct API | MUST PASS | Automated test (one per type) |
| ACC-ART-002 | Artefact lifecycle transitions (draft → under_review → reviewed → approved → released) enforce role requirements | MUST PASS | Automated test per transition |
| ACC-ART-003 | Every content change creates a new ArtefactRevision with previous_revision_id set | MUST PASS | Automated test |
| ACC-ART-004 | Soft-deleted artefact does not appear in active artefact queries | MUST PASS | Automated test |
| ACC-ART-005 | Soft-deleted artefact revision history is preserved and queryable | MUST PASS | Automated test |
| ACC-ART-006 | AuditEvent is created for every create, revise, status_change, and delete operation | MUST PASS | Automated test |

### 3.5 Relationship And Traceability

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-REL-001 | All 15 canonical relationship types can be created between permitted artefact type pairs | MUST PASS | Automated test |
| ACC-REL-002 | RULE-002 rejects a relationship of a type not permitted between the source and target artefact types | MUST PASS | Automated test |
| ACC-REL-003 | Forward trace query (SafetyGoal → SSR → SoftwareComponent → SoftwareUnit → TestCase → TestResult) returns the full chain | MUST PASS | Integration test with seeded dataset |
| ACC-REL-004 | Backward trace query from TestResult returns the full upstream chain | MUST PASS | Integration test |
| ACC-REL-005 | Traceability matrix generation completes within 5 seconds for a 10,000-relationship dataset | SHOULD PASS | Performance test |
| ACC-REL-006 | Deleting a relationship emits relationship.deleted event and triggers validation re-evaluation | MUST PASS | Automated test |

### 3.6 Validation Rule Engine

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-RULE-001 | All configured catalog rules can be loaded from the rule catalog without error | MUST PASS | Automated test |
| ACC-RULE-002 | Each rule with severity=critical produces a ValidationIssue with blocking_contexts set | MUST PASS | Automated test per rule |
| ACC-RULE-003 | RULE-025 fires when an InterfaceContract crosses QM→ASIL and lacks failure behavior | MUST PASS | Automated test |
| ACC-RULE-004 | RULE-013 fires for a released requirement with no passing TestResult | MUST PASS | Automated test |
| ACC-RULE-005 | RULE-005 fires when a mandatory artefact type has no instances and no tailoring decision | MUST PASS | Automated test |
| ACC-RULE-006 | A suppressed validation issue does not block baseline creation | MUST PASS | Automated test |
| ACC-RULE-007 | Validation run completes within 30 seconds for the performance test dataset | SHOULD PASS | Performance test |
| ACC-RULE-008 | Rules with `disabled` severity for a profile produce no issues for that profile | MUST PASS | Automated test |
| ACC-RULE-009 | RULE-070 fires only when `project.has_cybersecurity_relevance=True` AND artefact is security_relevant | MUST PASS | Automated test |
| ACC-RULE-010 | RULE-071 fires only when `project.has_software_update_relevance=True` | MUST PASS | Automated test |

### 3.7 Suspect Propagation And Impact Analysis

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-SUSP-001 | Changing a released SSR creates SuspectState records for downstream SoftwareComponents, ImplementationItems, and TestResults | MUST PASS | Integration test |
| ACC-SUSP-002 | Propagation does not exceed MAX_PROPAGATION_DEPTH (default 10) | MUST PASS | Automated test with deep chain |
| ACC-SUSP-003 | Clearing a suspect state with a valid clearing method and evidence ref succeeds | MUST PASS | Automated test |
| ACC-SUSP-004 | An artefact with open suspect state cannot be included in a releasable baseline (RULE-081) | MUST PASS | Integration test |
| ACC-SUSP-005 | Impact analysis returns affected artefact list consistent with propagation graph | MUST PASS | Automated test |
| ACC-SUSP-006 | Propagation along non-eligible relationship types (e.g., `references`) does NOT create suspect states | MUST PASS | Automated test |

### 3.8 Baseline And Release Gate

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-BASE-001 | Project Lead can request baseline creation; job completes with snapshot | MUST PASS | Integration test |
| ACC-BASE-002 | Baseline snapshot contains exact revision IDs for all active artefacts | MUST PASS | Automated test |
| ACC-BASE-003 | Project update lock blocks artefact writes during baseline creation | MUST PASS | Concurrent operation test |
| ACC-BASE-004 | Update lock is released when baseline creation completes or fails | MUST PASS | Automated test |
| ACC-BASE-005 | Release gate evaluation by Quality Engineer returns pass when no blocking issues exist | MUST PASS | Integration test (happy path) |
| ACC-BASE-006 | Release gate evaluation returns fail when any critical issue exists | MUST PASS | Integration test |
| ACC-BASE-007 | Baseline cannot be approved unless latest gate result = passed | MUST PASS | Automated test |
| ACC-BASE-008 | Baseline can be re-evaluated after resolving blocking issues | MUST PASS | Integration test |
| ACC-BASE-009 | Released baseline cannot be modified | MUST PASS | Automated test |
| ACC-BASE-010 | Baseline creation completes within 60 seconds for the performance test dataset | SHOULD PASS | Performance test |
| ACC-BASE-011 | Baseline comparison correctly identifies artefacts added/removed/changed between two baselines | MUST PASS | Automated test |

### 3.9 Async Jobs

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-JOB-001 | All async job types (import, validation, baseline, impact, report, release_gate) can be queued and complete | MUST PASS | Integration test per job type |
| ACC-JOB-002 | A queued job can be polled for status via GET /api/v1/jobs/{job_id} | MUST PASS | Automated test |
| ACC-JOB-003 | A job in `waiting_for_user` state remains paused until decision is submitted | MUST PASS | Automated test |
| ACC-JOB-004 | A cancelled job's partial effects are rolled back or clearly flagged | MUST PASS | Automated test |
| ACC-JOB-005 | A failed job records an error message retrievable via the job status endpoint | MUST PASS | Automated test |

### 3.10 Reports

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-REP-001 | Traceability matrix report can be generated for a project and retrieved as JSON | MUST PASS | Integration test |
| ACC-REP-002 | Baseline comparison report can be generated for two baselines | MUST PASS | Integration test |
| ACC-REP-003 | Validation summary report lists all open issues grouped by severity | MUST PASS | Integration test |

---

## 4. Non-Functional Acceptance Criteria

### 4.1 API Correctness

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-API-001 | All GET endpoints return correct data for the seeded test dataset | MUST PASS | Automated test |
| ACC-API-002 | All POST/PUT endpoints validate required fields and return 422 for missing/invalid fields | MUST PASS | Automated test |
| ACC-API-003 | All endpoints return the standard response envelope (status, request_id, data) | MUST PASS | Automated test |
| ACC-API-004 | Error responses do not include stack traces or database details | MUST PASS | Code review + test |
| ACC-API-005 | OpenAPI schema is published at /api/v1/openapi.json | MUST PASS | Automated test |

### 4.2 Security

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-SEC-001 | All parameterized queries; no raw string interpolation in SQL | MUST PASS | Code review + SAST scan |
| ACC-SEC-002 | Unauthenticated requests to protected endpoints return 401 | MUST PASS | Automated test |
| ACC-SEC-003 | HTTPS enforced in production Docker Compose configuration | MUST PASS | Deployment configuration review |
| ACC-SEC-004 | File upload (import) rejects files > 50 MB | MUST PASS | Automated test |
| ACC-SEC-005 | Audit trail records cannot be deleted via any API endpoint | MUST PASS | Automated test + code review |

### 4.3 Data Integrity

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-DATA-001 | All foreign key constraints are enforced in the database | MUST PASS | Schema review + integration test |
| ACC-DATA-002 | Concurrent creation of artefacts with the same source_object_id returns 409 for the second request | MUST PASS | Concurrent operation test |
| ACC-DATA-003 | Alembic migration scripts run cleanly on a fresh database | MUST PASS | CI pipeline test |
| ACC-DATA-004 | Database can be backed up and restored; restored instance passes all functional tests | MUST PASS | Manual acceptance test |

### 4.4 Deployment

| ID | Criterion | Classification | Verification Method |
|----|-----------|----------------|---------------------|
| ACC-DEPLOY-001 | `docker compose up` starts all services and back-end passes health check within 60 seconds | MUST PASS | CI deployment test |
| ACC-DEPLOY-002 | Alembic migrations run automatically on `api` container startup | MUST PASS | Automated test |
| ACC-DEPLOY-003 | ARQ worker connects to Redis and processes a test job within 5 seconds of startup | MUST PASS | Integration test |

### 4.5 Performance (Benchmarks Per DEC-PERF-001)

| ID | Criterion | Target | Classification | Verification Method |
|----|-----------|--------|----------------|---------------------|
| ACC-PERF-001 | GET single artefact P95 latency | < 100 ms | SHOULD PASS | Load test |
| ACC-PERF-002 | Forward/backward trace (depth ≤ 5) P95 latency | < 500 ms | SHOULD PASS | Load test |
| ACC-PERF-003 | Import 500 artefacts | < 120 seconds | SHOULD PASS | Performance test |
| ACC-PERF-004 | Validation run (project scope) | < 30 seconds | SHOULD PASS | Performance test |
| ACC-PERF-005 | Baseline creation | < 60 seconds | SHOULD PASS | Performance test |

---

## 5. End-To-End Scenario Tests

The following scenarios must each pass as full integration tests against a deployed instance:

### Scenario 1: ASIL D Happy Path

1. Admin creates project with ASIL D profile
2. User imports Sphinx-Needs export containing all mandatory ASIL D artefact types
3. Validation run completes with zero critical issues
4. All artefacts transitioned to `released` by Quality Engineer
5. Project Lead requests baseline creation
6. Baseline creation completes with `eligibility_passed=true`
7. Quality Engineer triggers release gate evaluation
8. Release gate passes (no blocking issues, no open suspects)
9. Project Lead approves baseline
10. Quality Engineer releases baseline

**Pass criterion**: All 10 steps complete without errors; baseline status = released

---

### Scenario 2: Traceability Chain

1. SafetyGoal created with ASIL D
2. FSR created, linked `derives_from` SafetyGoal
3. TSR created, linked `derives_from` FSR
4. SSR created, linked `derives_from` TSR
5. SoftwareComponent created, SSR `allocates_to` component
6. SoftwareUnit created, `implements` SSR
7. TestCase created, `verifies` SSR
8. TestResult created (verdict=pass), `produces_result_for` TestCase
9. Forward trace from SafetyGoal returns: FSR → TSR → SSR → SoftwareComponent + SoftwareUnit + TestResult
10. Backward trace from TestResult returns: TestCase → SSR → TSR → FSR → SafetyGoal

**Pass criterion**: Both traces return the exact expected chain

---

### Scenario 3: Suspect Propagation

1. All artefacts from Scenario 2 in `released` state
2. Admin updates the SSR content (creates new revision)
3. Back-end automatically creates SuspectState for: SoftwareComponent, SoftwareUnit, TestCase, TestResult
4. Release gate evaluation fails with RULE-081 blocking issues
5. User clears suspect state on SoftwareUnit with `clearing_method=re_verified` and evidence_ref
6. Remaining suspects cleared by Project Lead with `clearing_method=reviewed_and_accepted`
7. Release gate evaluation passes after all suspects cleared

**Pass criterion**: Suspects created, block gate, and are clearable; gate passes after clearing

---

### Scenario 4: Tailoring Decision

1. Project with ASIL D profile
2. RULE-005 fires because no `HardwareSoftwareInterface` artefact exists
3. User creates TailoringDecision marking `HardwareSoftwareInterface` as not_applicable with rationale and evidence_ref
4. Project Lead approves tailoring decision
5. RULE-005 no longer fires for HardwareSoftwareInterface type
6. Baseline creation succeeds
7. Tailoring decision is recorded in the baseline snapshot

**Pass criterion**: Tailoring suppresses the rule and is recorded in the baseline

---

### Scenario 5: Import Conflict In Ask-User Mode

1. Project configured with `version_update_mode=ask_user`
2. SSR_001 imported and in `released` state
3. SSR_001 modified in Sphinx; re-import submitted
4. Import job transitions to `waiting_for_user`; decision_required response returned
5. User accepts new version
6. Import job resumes and completes; new revision created for SSR_001
7. AuditEvent records: conflict_detected, decision_accepted, artefact_revised

**Pass criterion**: All 7 steps execute correctly with correct audit trail

---

## 6. Test Dataset Specification

The performance acceptance test dataset shall contain:

| Artefact Type | Count |
|---|---|
| SoftwareSafetyRequirement | 100 |
| SoftwareRequirement | 400 |
| SoftwareComponent | 100 |
| SoftwareUnit | 200 |
| InterfaceContract | 150 |
| TestSpecification | 50 |
| TestCase | 500 |
| TestResult | 5000 |
| Relationships (all types) | 10,000 |
| Baselines | 5 |
| AuditEvents | ~50,000 |

This dataset shall be generated by a seed script in `ops/seed_performance_dataset.py` and shall be reproducible from a fixed random seed.
