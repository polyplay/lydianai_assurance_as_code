export async function installMockApi(page, options = {}) {
  const role = options.role || "admin";
  const requests = [];
  const artefacts = [
    {
      artefact_id: "ART_1",
      project_id: "PROJ_1",
      artefact_type: "SoftwareRequirement",
      title: "Brake monitoring requirement",
      description: "Monitor braking state.",
      status: "draft",
      current_revision_id: "AREV_1",
      source_kind: "api",
      source_tool: null,
      source_object_id: "SWR-001",
      source_document: "requirements",
      standards_refs_json: [],
      payload_json: {
        statement: "The software shall monitor brake pressure.",
        verification_intent: "Test",
      },
      allowed_actions: role === "admin" ? ["edit", "submit_for_review", "delete"] : ["edit", "submit_for_review"],
    },
    {
      artefact_id: "ART_2",
      project_id: "PROJ_1",
      artefact_type: "TestCase",
      title: "Brake pressure monitoring test",
      description: "",
      status: "reviewed",
      current_revision_id: "AREV_2",
      source_kind: "api",
      source_tool: null,
      source_object_id: "TC-001",
      source_document: "tests",
      standards_refs_json: [],
      payload_json: {
        test_specification: "TS-001",
        expected_results: "Alarm raised",
        pass_fail_criteria: "Alarm within 100 ms",
      },
      allowed_actions: role === "admin" ? ["edit", "reject", "approve", "delete"] : ["edit"],
    },
  ];
  const relationships = [
    {
      relationship_id: "REL_1",
      project_id: "PROJ_1",
      relationship_type: "verified_by",
      source_artefact_id: "ART_1",
      target_artefact_id: "ART_2",
      status: "active",
      current_revision_id: "RREV_1",
      payload_json: {},
      allowed_actions: role === "admin" ? ["edit", "delete"] : ["edit"],
    },
  ];
  const capabilities = capabilitiesFor(role);

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace("/api/v1", "");
    const method = request.method();
    let body = null;
    try {
      body = request.postDataJSON();
    } catch {
      body = request.postData();
    }
    requests.push({ method, path, body });

    if (method === "POST" && path === "/auth/login") {
      return envelope(route, { access_token: "mock-token", expires_in_seconds: 3600 });
    }
    if (method === "GET" && path === "/users/me") {
      return envelope(route, {
        user: {
          user_id: "USER_1",
          username: "alex",
          display_name: "Alex Engineer",
          email: "alex@example.test",
          status: "active",
        },
        roles: role === "admin" ? ["admin"] : [],
      });
    }
    if (method === "GET" && path === "/projects") {
      return envelope(route, [
        {
          project_id: "PROJ_1",
          project_key: "BRAKE",
          name: "Brake Controller",
          description: "Demo",
          active_profile_id: "PROF_1",
          status: "active",
        },
      ]);
    }
    if (method === "GET" && path === "/projects/PROJ_1/workspace") {
      return envelope(route, workspace(role, capabilities));
    }
    if (method === "GET" && path === "/projects/PROJ_1/schemas") {
      return envelope(route, { project_id: "PROJ_1", schemas: [schema()] });
    }
    if (
      method === "GET" &&
      path === "/projects/PROJ_1/schemas/SoftwareRequirement"
    ) {
      return envelope(route, { project_id: "PROJ_1", ...schema() });
    }
    if (method === "GET" && path === "/projects/PROJ_1/artefacts") {
      return envelope(route, artefacts);
    }
    if (method === "GET" && path.startsWith("/projects/PROJ_1/artefacts/")) {
      if (path.endsWith("/revisions")) {
        return envelope(route, [
          {
            artefact_revision_id: "AREV_1",
            revision_number: 1,
            changed_at: "2026-06-13T10:00:00Z",
            content_fingerprint: "abc",
          },
        ]);
      }
      return envelope(route, artefacts.find((item) => path.includes(item.artefact_id)));
    }
    if (method === "POST" && path === "/projects/PROJ_1/artefacts") {
      if (options.createArtefactError) {
        return error(route, 409, "source identity already exists");
      }
      return envelope(route, { ...artefacts[0], artefact_id: "ART_NEW", title: body.title });
    }
    if (method === "GET" && path === "/projects/PROJ_1/relationships") {
      return envelope(route, relationships);
    }
    if (method === "GET" && path === "/projects/PROJ_1/imports") {
      return envelope(route, [
        {
          import_run_id: "IMP_1",
          state: "waiting_for_user",
          version_update_mode: "ask_user",
          summary: { total: 1, processed: 1 },
          diagnostics: [{ level: "warning", classification: "conflict", message: "Revision conflict" }],
          allowed_actions: ["submit_decisions", "cancel"],
        },
      ]);
    }
    if (method === "GET" && path === "/projects/PROJ_1/imports/IMP_1") {
      return envelope(route, {
        import_run_id: "IMP_1",
        state: "waiting_for_user",
        version_update_mode: "ask_user",
        summary: { total: 1, processed: 1 },
        diagnostics: [{ level: "warning", classification: "conflict", message: "Revision conflict" }],
        items: [
          {
            import_run_item_id: "IMPITEM_1",
            source_object_id: "SWR-001",
            artefact_type: "SoftwareRequirement",
            detected_change_type: "conflict",
            decision_status: "pending",
          },
        ],
        allowed_actions: ["submit_decisions", "cancel"],
      });
    }
    if (method === "GET" && path === "/projects/PROJ_1/validation/status") {
      return envelope(route, {
        issue_count: 1,
        open_issue_count: 1,
        critical_open_issue_count: 1,
      });
    }
    if (method === "GET" && path === "/projects/PROJ_1/validation/issues") {
      return envelope(route, [
        {
          validation_issue_id: "VISS_1",
          rule_id: "AAC-RULE-RULE-001",
          severity: "critical",
          status: "open",
          message: "Required evidence is missing.",
          remediation_hint: "Create the required artefact.",
          affected_artefacts: [],
          affected_relationships: [],
          allowed_actions: role === "admin" ? ["suppress"] : [],
        },
      ]);
    }
    if (method === "GET" && path === "/projects/PROJ_1/traceability-matrix") {
      return envelope(route, relationships);
    }
    if (method === "GET" && path.startsWith("/projects/PROJ_1/trace/")) {
      return envelope(route, { artefact_id: "ART_1", forward: ["ART_2"], backward: [] });
    }
    if (method === "GET" && path === "/projects/PROJ_1/suspect-states") {
      return envelope(route, [
        {
          suspect_state_id: "SUSP_1",
          artefact_id: "ART_2",
          trigger_artefact_id: "ART_1",
          propagation_depth: 1,
          status: "open",
          allowed_actions: role === "user" ? [] : ["clear"],
        },
      ]);
    }
    if (method === "GET" && path === "/projects/PROJ_1/baselines") {
      return envelope(route, [
        {
          baseline_id: "BASE_1",
          name: "Release candidate 1",
          state: "created",
          release_gate_status: "passed",
          summary: {},
          eligibility_result: {},
          allowed_actions: role === "admin" ? ["run_release_gate", "approve", "obsolete"] : ["run_release_gate"],
        },
        {
          baseline_id: "BASE_2",
          name: "Released baseline",
          state: "released",
          release_gate_status: "passed",
          summary: {},
          eligibility_result: {},
          allowed_actions: role === "admin" ? ["publish_repository_approval", "obsolete"] : [],
        },
      ]);
    }
    if (method === "GET" && path.includes("/release-gate/results/latest")) {
      return envelope(route, {
        status: "passed",
        result: "pass",
        passed_rules_count: 45,
        blocking_issues: [],
        open_suspect_states: [],
      });
    }
    if (method === "GET" && path === "/projects/PROJ_1/reports") {
      return envelope(route, []);
    }
    if (method === "GET" && path === "/projects/PROJ_1/jobs") {
      return envelope(route, [
        {
          job_id: "JOB_1",
          job_type: "validation_run",
          state: "running",
          progress_percent: 45,
          last_committed_unit: "rule 20",
          allowed_actions: ["cancel"],
        },
      ]);
    }
    if (method === "GET" && path === "/jobs/JOB_1") {
      return envelope(route, {
        job_id: "JOB_1",
        job_type: "validation_run",
        state: "running",
        progress_percent: 45,
        allowed_actions: ["cancel"],
      });
    }
    if (method === "GET" && path === "/projects/PROJ_1/members") {
      return envelope(route, [
        { user_id: "USER_1", username: "alex", role },
      ]);
    }
    if (method === "GET" && path === "/users") {
      return envelope(route, [
        { user_id: "USER_1", username: "alex", display_name: "Alex Engineer" },
      ]);
    }
    if (method === "GET" && path === "/projects/PROJ_1/config") {
      return envelope(route, {
        version_update_mode: "ask_user",
        sphinx_source_root: "docs",
        baseline_policy: {},
        validation_policy: {},
        reporting_policy: {},
        assurance_configuration: { asil_level: "ASIL_D" },
      });
    }
    if (method === "GET" && path === "/projects/PROJ_1/repo-connectors") {
      return envelope(route, []);
    }
    if (method === "GET" && path === "/projects/PROJ_1/audit-events") {
      return envelope(route, []);
    }
    return envelope(route, { accepted: true }, 200, "accepted");
  });
  return { requests, artefacts, relationships };
}

export async function signIn(page) {
  await page.goto("/");
  await page.waitForFunction(
    () => document.querySelector("#api-base-url")?.value.endsWith("/api/v1"),
  );
  await page.getByLabel("Username").fill("alex");
  await page.getByLabel("Password", { exact: true }).fill("password");
  await page.getByRole("button", { name: "Sign in" }).click();
  await page.getByRole("heading", { name: /Welcome, Alex Engineer/ }).waitFor();
}

function workspace(role, capabilities) {
  return {
    project: {
      project_id: "PROJ_1",
      project_key: "BRAKE",
      name: "Brake Controller",
      description: "Demo",
      status: "active",
      active_profile_id: "PROF_1",
      locked: false,
    },
    actor: {
      user_id: "USER_1",
      username: "alex",
      display_name: "Alex Engineer",
      global_roles: role === "admin" ? ["admin"] : [],
      project_roles: role === "admin" ? [] : [role],
      effective_roles: [role],
    },
    capabilities,
    summary: {
      artefacts: { total: 2, by_status: { draft: 1, reviewed: 1 } },
      relationships: { total: 1 },
      imports: { total: 1, active: 1, waiting_for_user: 1 },
      validation: { open: 1, critical_open: 1, release_blocking: 1 },
      suspects: { open: 1 },
      jobs: { active: 1, mine_active: 1 },
      baselines: {
        total: 1,
        latest: {
          baseline_id: "BASE_1",
          name: "Release candidate 1",
          state: "created",
          release_gate_status: "passed",
          allowed_actions: role === "admin" ? ["run_release_gate", "approve"] : ["run_release_gate"],
        },
      },
    },
    release_readiness: {
      state: "blocked",
      ready: false,
      blockers: [
        { kind: "validation_issue", count: 1 },
        { kind: "suspect_state", count: 1 },
      ],
    },
    actionable_work: [
      { kind: "import_decision", count: 1, label: "Import decisions", route: "#/imports", severity: "warning" },
      { kind: "release_blocker", count: 1, label: "Release-blocking validation issues", route: "#/validation", severity: "critical" },
    ],
  };
}

function capabilitiesFor(role) {
  const admin = role === "admin";
  const lead = role === "project_lead";
  const quality = role === "quality_engineer";
  return {
    "project.read": true,
    "project.configure": admin,
    "team.read": true,
    "team.manage": admin || lead,
    "artefact.read": true,
    "artefact.create": true,
    "relationship.read": true,
    "relationship.create": true,
    "import.read": true,
    "import.start": true,
    "validation.read": true,
    "validation.run": true,
    "validation.manage_issues": admin,
    "trace.read": true,
    "impact.run": true,
    "suspect.clear": admin || lead || quality,
    "baseline.read": true,
    "baseline.create": admin || lead,
    "release_gate.run": true,
    "baseline.approve": admin || lead,
    "baseline.release": admin || quality,
    "report.read": true,
    "report.generate": true,
    "report.delete": admin || quality,
    "job.read": true,
    "repository.read": true,
    "repository.manage": admin,
    "repository.scan": admin || lead,
    "repository.publish_approval": admin || lead || quality,
    "audit.read": admin || lead || quality,
    "schema.manage": admin,
  };
}

function schema() {
  return {
    artefact_type: "SoftwareRequirement",
    schema_version: "1.0",
    enabled_fields: ["statement", "verification_intent"],
    disabled_fields: [],
    mandatory_fields: ["statement", "verification_intent"],
    readonly_fields: [],
    fields: [
      {
        name: "statement",
        label: "Statement",
        data_type: "string",
        widget: "textarea",
        required: true,
        readonly: false,
        allowed_values: [],
        item_type: null,
        help: "Enter requirement statement.",
      },
      {
        name: "verification_intent",
        label: "Verification Intent",
        data_type: "string",
        widget: "textarea",
        required: true,
        readonly: false,
        allowed_values: [],
        item_type: null,
        help: "Describe verification intent.",
      },
    ],
  };
}

async function envelope(route, data, status = 200, envelopeStatus = "success") {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      status: envelopeStatus,
      request_id: "REQ_TEST",
      correlation_id: "CORR_TEST",
      messages: [],
      data,
    }),
  });
}

async function error(route, status, detail) {
  await route.fulfill({
    status,
    contentType: "application/json",
    body: JSON.stringify({
      request_id: `REQ_${status}`,
      correlation_id: `CORR_${status}`,
      detail,
    }),
  });
}
