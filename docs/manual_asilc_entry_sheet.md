# ASIL-C Manual Entry Sheet

Use this sheet to add a small ASIL-C project manually in the app.

Current UI state: the loaded project is **not** the new fixture. The screenshot shows `UI_FINAL_1776357519`, so leave that project selected and create the fixture separately when you are ready.

## Project

- `project_key`: `BATMGR_ASILC_TEST`
- `name`: `Battery Thermal Supervisor ASIL-C Test`
- `description`: `Small ASIL-C manual test project for traceability, validation, and release workflow checks.`
- `asil_level`: `ASIL_C`
- `aspice_default_capability_level`: `2`
- `aspice_scoped_processes`: `MAN.3`, `SWE.1`, `SWE.2`, `SWE.3`, `SWE.4`, `SWE.5`, `SWE.6`, `SUP.8`, `SUP.9`, `SUP.10`, `VAL.1`
- `r155_applicable`: `false`
- `r156_applicable`: `true`
- `visibility_policy`: `relevant_first`

In **Administration → Project defaults**:

1. Set **ASIL level** to `ASIL C`.
2. Set **ASPICE target capability** to `2`. This is the project default.
3. In **ASPICE process scope and expected capability**, leave these processes in scope: `MAN.3`, `SWE.1`, `SWE.2`, `SWE.3`, `SWE.4`, `SWE.5`, `SWE.6`, `SUP.8`, `SUP.9`, `SUP.10`, `VAL.1`.
4. Clear any other process checkboxes for this manual test project.
5. Keep every in-scope process expected capability at `CL2`.
6. Leave **UNECE R155 applicable** unchecked and **UNECE R156 applicable** checked.

If you change the ASPICE process scope or any expected capability after project
creation, enter an ASPICE tailoring rationale and evidence reference before
saving. For this manual test, use a reference such as `manual-test-scope`.

Assign all roles:

- `admin`
- `project_lead`
- `quality_engineer`
- `user`

## Entry order

Create the artefacts in this order:

1. `PRJ-001` `ProjectScope`
2. `SG-001` `SafetyGoal`
3. `FSR-001` `FunctionalSafetyRequirement`
4. `TSR-001` `TechnicalSafetyRequirement`
5. `SSR-001` `SoftwareSafetyRequirement`
6. `SR-001` `SoftwareRequirement` (`functional`)
7. `SR-002` `SoftwareRequirement` (`interface`)
8. `SR-003` `SoftwareRequirement` (`timing`)
9. `SR-004` `SoftwareRequirement` (`diagnostic`)
10. `SR-005` `SoftwareRequirement` (`fault_handling`)
11. `SR-006` `SoftwareRequirement` (`update`)
12. `DSR-001` `DerivedSoftwareRequirement`
13. `SWC-001` `SoftwareComponent`
14. `SWU-001` `SoftwareUnit`
15. `IFC-001` `InterfaceContract`
16. `TSP-001` `TestSpecification`
17. `TSC-001` `TestCase`
18. `TR-001` `TestResult`
19. `BLD-001` `BuildConfiguration`

## Relationships

Create these links:

- `SG-001 derives_from PRJ-001`
- `FSR-001 derives_from SG-001`
- `TSR-001 derives_from FSR-001`
- `SSR-001 derives_from TSR-001`
- `SR-001 derives_from SSR-001`
- `SR-002 derives_from SR-001`
- `SR-003 derives_from SR-002`
- `SR-004 derives_from SR-001`
- `SR-005 derives_from SR-004`
- `SR-006 derives_from SR-001`
- `DSR-001 derives_from SR-003`
- `DSR-001 derives_from SR-005`
- `SSR-001 allocates_to SWC-001`
- `SWU-001 implements SR-001`
- `SWU-001 implements SR-002`
- `TSC-001 verifies SSR-001`
- `TR-001 produces_result_for TSC-001`
- `TR-001 verifies SSR-001`

## Practical test focus

Use the project to check:

- traceability navigation forward and backward
- validation behavior for ASIL-C
- release-readiness and baseline flows
- role-based access for the four project roles
- R155 not-applicable behavior
- R156-visible behavior
- structured logs and error details for failures
