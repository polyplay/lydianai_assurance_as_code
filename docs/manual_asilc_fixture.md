# Manual ASIL-C Test Fixture

This fixture is intended for manual testing of the app with:

- ASIL-C project classification
- all project roles assigned
- `UNECE R155 = not applicable`
- `UNECE R156 = applicable`

The app does not have a dedicated `StRS` artefact type. Use `ProjectScope` as the stakeholder-level proxy.

## 1. Create the project

Create a project with this configuration:

```json
{
  "project_key": "BATMGR_ASILC_TEST",
  "name": "Battery Thermal Supervisor ASIL-C Test",
  "description": "Small ASIL-C manual test project for traceability, validation, and release workflow checks.",
  "assurance_configuration": {
    "project_type": "software_system",
    "asil_level": "ASIL_C",
    "aspice_model": "ASPICE_PAM_4_0",
    "aspice_default_capability_level": 2,
    "aspice_scoped_processes": [
      "MAN.3",
      "SWE.1",
      "SWE.2",
      "SWE.3",
      "SWE.4",
      "SWE.5",
      "SWE.6",
      "SUP.8",
      "SUP.9",
      "SUP.10",
      "VAL.1"
    ],
    "aspice_process_overrides": {},
    "r155_applicable": false,
    "r156_applicable": true,
    "has_cybersecurity_relevance": false,
    "has_software_update_relevance": true,
    "test_scope": ["unit", "integration", "software_qualification", "acceptance"],
    "visibility_policy": "relevant_first"
  }
}
```

When entering this through the UI, set **ASPICE target capability** to `2`, then
use **ASPICE process scope and expected capability** to keep only `MAN.3`,
`SWE.1`, `SWE.2`, `SWE.3`, `SWE.4`, `SWE.5`, `SWE.6`, `SUP.8`, `SUP.9`,
`SUP.10`, and `VAL.1` in scope. Keep each selected process at `CL2`.

If you change the process scope or any process capability after project creation,
the tool requires an ASPICE tailoring rationale and at least one evidence
reference before saving the project defaults.

Assign all applicable roles to the project:

- `admin`
- `project_lead`
- `quality_engineer`
- `user`

## 2. Requirement set

Enter the requirement chain in this order.

### Stakeholder proxy

| ID | Artefact type | Title | Key payload |
|---|---|---|---|
| `PRJ-001` | `ProjectScope` | `Battery thermal supervisor scope` | `scope_statement`: keep the battery pack within safe temperature limits while preserving drivability after a single sensor fault |

### System level

| ID | Artefact type | Title | Key payload |
|---|---|---|---|
| `SG-001` | `SafetyGoal` | `Prevent battery overtemperature` | `statement`: prevent battery overtemperature and thermal runaway |
| `FSR-001` | `FunctionalSafetyRequirement` | `Protective cooling request` | `statement`: request protective cooling within 100 ms of validated overtemperature |
| `TSR-001` | `TechnicalSafetyRequirement` | `Sensor sampling and invalid-data handling` | `statement`: sample temperature every 10 ms and treat missing or implausible values as invalid |

### Software level

| ID | Artefact type | Title | Key payload |
|---|---|---|---|
| `SSR-001` | `SoftwareSafetyRequirement` | `Detect sensor timeout and enter safe fallback` | `statement`: detect sensor timeout within 20 ms, command maximum cooling, and latch the fault until recovery is verified |
| `SR-001` | `SoftwareRequirement` | `Control fan from validated inputs` | `requirement_type=functional`, `statement`: compute fan command from validated temperature and operating mode |
| `SR-002` | `SoftwareRequirement` | `Control interface contract` | `requirement_type=interface`, `statement`: expose one temperature input and one fan-command output with explicit units and valid ranges |
| `SR-003` | `SoftwareRequirement` | `Control cycle timing` | `requirement_type=timing`, `statement`: complete the control cycle within 20 ms of each sample |
| `SR-004` | `SoftwareRequirement` | `Diagnostic logging` | `requirement_type=diagnostic`, `statement`: record a diagnostic event and freeze-frame data on sensor timeout |
| `SR-005` | `SoftwareRequirement` | `Fallback mode handling` | `requirement_type=fault_handling`, `statement`: enter fallback mode on invalid sensor data and exit only after three consecutive valid samples |
| `SR-006` | `SoftwareRequirement` | `Update package integrity` | `requirement_type=update`, `statement`: reject unsigned or hash-mismatched update packages before activation |
| `DSR-001` | `DerivedSoftwareRequirement` | `Fallback safe fan clamp` | `statement`: clamp fan command to a safe fixed minimum while fallback mode is active |

### Supporting artefacts

| ID | Artefact type | Title | Purpose |
|---|---|---|---|
| `SWC-001` | `SoftwareComponent` | `BatteryThermalController` | allocation target for safety requirement |
| `SWU-001` | `SoftwareUnit` | `ThermalSupervisorUnit` | implementation unit for the main control logic |
| `IFC-001` | `InterfaceContract` | `TempSensor_IF` | explicit sensor and fan-command interface |
| `TSP-001` | `TestSpecification` | `Thermal supervisor verification spec` | verifies timeout, fallback, and timing behavior |
| `TSC-001` | `TestCase` | `Sensor timeout causes safe fallback` | linked to the main safety requirement |
| `TR-001` | `TestResult` | `Timeout test passes` | pass result for the timeout scenario |
| `BLD-001` | `BuildConfiguration` | `Manual build config` | identifies build and toolchain context |

## 3. Dependency graph

Create these relationships:

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

## 4. Optional R156 evidence set

Because `R156` is applicable in the fixture configuration, add these if you want the profile-driven validation path to be cleaner:

- `SoftwareUpdateManagementEvidence`
- `SoftwareVersionRecord`
- `UpdateCampaign`
- `UpdateIntegrityEvidence`
- `SoftwareBillOfMaterials`

Keep `R155` out of the project configuration and confirm any R155-related artefact classes remain `not_applicable`.
