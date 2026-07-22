import {
  actionButton,
  escapeHtml,
  jsonView,
  readJson,
  requireConfirmation,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

const ASPICE_PROCESS_OPTIONS = [
  ["MAN.3", "Project Management"],
  ["SPL.2", "Product Release"],
  ["SYS.1", "Requirements Elicitation"],
  ["SYS.2", "System Requirements Analysis"],
  ["SYS.3", "System Architectural Design"],
  ["SWE.1", "Software Requirements Analysis"],
  ["SWE.2", "Software Architectural Design"],
  ["SWE.3", "Software Detailed Design and Unit Construction"],
  ["SWE.4", "Software Unit Verification"],
  ["SWE.5", "Software Integration and Integration Test"],
  ["SWE.6", "Software Qualification Test"],
  ["SUP.1", "Quality Assurance"],
  ["SUP.8", "Configuration Management"],
  ["SUP.9", "Problem Resolution Management"],
  ["SUP.10", "Change Request Management"],
  ["VAL.1", "Validation"],
];

const DEFAULT_ASPICE_SCOPED_PROCESSES = [
  "MAN.3",
  "SWE.1",
  "SWE.2",
  "SWE.3",
  "SWE.4",
  "SWE.5",
  "SWE.6",
  "SUP.1",
  "SUP.8",
  "SUP.9",
  "SUP.10",
  "VAL.1",
];

export async function renderAdministration(ctx) {
  setPage({
    eyebrow: "Management",
    title: "Project administration",
    description: "Manage access, project defaults, repository connections, and audit evidence.",
  });
  const capabilities = ctx.state.workspace.capabilities;
  const requests = [
    ctx.api.members(ctx.state.projectId),
    ctx.api.projectConfig(ctx.state.projectId),
    ctx.api.connectors(ctx.state.projectId),
    ctx.api.schemas(ctx.state.projectId),
  ];
  if (capabilities["audit.read"]) {
    requests.push(ctx.api.auditEvents(ctx.state.projectId));
  }
  const [
    membersResponse,
    configResponse,
    connectorsResponse,
    schemasResponse,
    auditResponse,
  ] =
    await Promise.all(requests);
  let users = [];
  if (ctx.state.workspace.actor.global_roles.includes("admin")) {
    try {
      users = (await ctx.api.users()).data || [];
    } catch {
      users = [];
    }
  }
  const members = membersResponse.data || [];
  const config = configResponse.data;
  const connectors = connectorsResponse.data || [];
  const schemas = schemasResponse.data.schemas || [];
  const auditEvents = auditResponse?.data || [];
  const globalAdmin = ctx.state.workspace.actor.global_roles.includes("admin");

  ctx.root.innerHTML = `
    ${
      globalAdmin
        ? `<section class="grid two" style="margin-bottom: 1rem">
          <article class="card">${renderProjectForm()}</article>
          <article class="card">${renderUserForm(users)}</article>
        </section>`
        : ""
    }
    <section class="grid two">
      <article class="card">
        <div class="card-header"><div><h2>Team access</h2>
        <p class="muted">Project-scoped roles used by server authorization.</p></div></div>
        <div id="members-table">${renderMembers(members, capabilities["team.manage"])}</div>
        ${capabilities["team.manage"] ? renderMemberForm(users) : ""}
      </article>
      <article class="card">
        <h2>Project defaults</h2>
        ${renderConfiguration(config, capabilities["project.configure"])}
      </article>
    </section>
    <section class="card" style="margin-top: 1rem">
      <div class="card-header"><div><h2>Repository connectors</h2>
      <p class="muted">Connect source revisions and publish release evidence separately.</p></div></div>
      <div id="connectors-table">${renderConnectors(connectors, capabilities)}</div>
      ${capabilities["repository.manage"] ? renderConnectorForm() : ""}
    </section>
    ${
      capabilities["schema.manage"]
        ? `<section class="card" style="margin-top: 1rem">${renderSchemaManagement(
            schemas,
          )}</section>`
        : ""
    }
    ${
      capabilities["audit.read"]
        ? `<section class="card" style="margin-top: 1rem">
          <div class="card-header"><div><h2>Recent audit events</h2>
          <p class="muted">Append-only controlled operation records.</p></div></div>
          ${renderAudit(auditEvents)}
        </section>`
        : ""
    }
  `;
  bindMembers(ctx, members);
  bindConfiguration(ctx, config);
  bindConnectors(ctx, connectors);
  bindSchemaManagement(ctx, schemas);
  if (globalAdmin) {
    bindGlobalAdministration(ctx);
  }
}

function renderProjectForm() {
  return `<h2>Create project</h2>
    <form id="create-project-form" class="form-grid">
      <label class="field-required">Project key<input name="project_key" required></label>
      <label class="field-required">Name<input name="name" required></label>
      <label class="full">Description<textarea name="description" rows="3"></textarea></label>
      <label>ASIL level<select name="asil_level">
        <option value="QM">QM</option><option value="ASIL_A">ASIL A</option>
        <option value="ASIL_B">ASIL B</option><option value="ASIL_C">ASIL C</option>
        <option value="ASIL_D" selected>ASIL D</option>
      </select></label>
      <label>ASPICE target capability<input name="aspice_capability" type="number"
        min="1" max="3" value="3"></label>
      <div class="full"><button class="button primary" type="submit">Create project</button></div>
    </form>`;
}

function renderUserForm(users) {
  return `<h2>Create user</h2>
    <p class="muted">${escapeHtml(users.length)} existing global user accounts</p>
    <form id="create-user-form" class="form-grid">
      <label class="field-required">Username<input name="username" required></label>
      <label class="field-required">Display name<input name="display_name" required></label>
      <label class="field-required">Email<input name="email" type="email" required></label>
      <label class="field-required">Temporary password<input name="password" type="password" required></label>
      <label>Global role<select name="global_role">
        <option value="">No global role</option><option value="admin">Administrator</option>
      </select></label>
      <div class="full"><button class="button primary" type="submit">Create user</button></div>
    </form>`;
}

function renderMembers(members, canManage) {
  return table(
    ["User", "Role", "Actions"],
    members.map((member) => [
      `<strong>${escapeHtml(member.username)}</strong><br><span class="muted">${escapeHtml(
        member.user_id,
      )}</span>`,
      statusBadge(member.role),
      canManage
        ? `<div class="row-actions">${actionButton("remove-member", "Remove", {
            id: member.user_id,
            variant: "danger",
          })}</div>`
        : "",
    ]),
    { emptyTitle: "No project members" },
  );
}

function renderMemberForm(users) {
  const userControl = users.length
    ? `<select name="user_id" required><option value="">Select a user...</option>
      ${users
        .map(
          (user) =>
            `<option value="${escapeHtml(user.user_id)}">${escapeHtml(
              user.display_name,
            )} · ${escapeHtml(user.username)}</option>`,
        )
        .join("")}</select>`
    : '<input name="user_id" required placeholder="USER identifier">';
  return `<form id="member-form" class="form-grid" style="margin-top: 1rem">
    <label class="field-required">User${userControl}</label>
    <label class="field-required">Role<select name="role" required>
      <option value="user">User</option>
      <option value="quality_engineer">Quality engineer</option>
      <option value="project_lead">Project lead</option>
      <option value="admin">Administrator</option>
    </select></label>
    <div class="full"><button class="button primary" type="submit">Add member</button></div>
  </form>`;
}

function renderConfiguration(config, canConfigure) {
  if (!canConfigure) {
    return `<dl class="details-list">
      <dt>Import conflicts</dt><dd>${escapeHtml(config.version_update_mode)}</dd>
      <dt>Sphinx root</dt><dd>${escapeHtml(config.sphinx_source_root || "Not set")}</dd>
      <dt>ASIL</dt><dd>${escapeHtml(
        config.assurance_configuration?.asil_level || "Not set",
      )}</dd>
    </dl><details class="advanced"><summary>Configuration detail</summary>${jsonView(
      config,
    )}</details>`;
  }
  const assurance = config.assurance_configuration || {};
  return `<form id="config-form" class="stack">
    <div class="form-grid">
      <label>ASIL level<select name="asil_level">
        ${["QM", "ASIL_A", "ASIL_B", "ASIL_C", "ASIL_D"]
          .map(
            (level) =>
              `<option value="${level}" ${
                assurance.asil_level === level ? "selected" : ""
              }>${level.replace("_", " ")}</option>`,
          )
          .join("")}
      </select></label>
      <label>ASPICE target capability<input name="aspice_capability" type="number"
        min="1" max="3" value="${escapeHtml(
          assurance.aspice_default_capability_level || 3,
        )}"></label>
      <label class="checkbox-label"><input name="r155_applicable" type="checkbox" ${
        assurance.r155_applicable ? "checked" : ""
      }> UNECE R155 applicable</label>
      <label class="checkbox-label"><input name="r156_applicable" type="checkbox" ${
        assurance.r156_applicable ? "checked" : ""
      }> UNECE R156 applicable</label>
      <label>Catalogue visibility<select name="visibility_policy">
        ${["relevant_first", "strict_hide", "show_all_tagged"]
          .map(
            (policy) =>
              `<option value="${policy}" ${
                assurance.visibility_policy === policy ? "selected" : ""
              }>${policy.replaceAll("_", " ")}</option>`,
          )
          .join("")}
      </select></label>
    </div>
    ${renderAspiceTailoring(assurance)}
    <label>Import conflict behavior<select name="version_update_mode">
      <option value="ask_user" ${
        config.version_update_mode === "ask_user" ? "selected" : ""
      }>Ask for decisions</option>
      <option value="automatic_new_version" ${
        config.version_update_mode === "automatic_new_version" ? "selected" : ""
      }>Create revisions automatically</option>
    </select></label>
    <label>Sphinx source root<input name="sphinx_source_root" value="${escapeHtml(
      config.sphinx_source_root || "",
    )}"></label>
    <details class="advanced"><summary>Advanced policy JSON</summary>
      <label>Baseline policy<textarea name="baseline_policy">${escapeHtml(
        JSON.stringify(config.baseline_policy || {}, null, 2),
      )}</textarea></label>
      <label>Validation policy<textarea name="validation_policy">${escapeHtml(
        JSON.stringify(config.validation_policy || {}, null, 2),
      )}</textarea></label>
      <label>Reporting policy<textarea name="reporting_policy">${escapeHtml(
        JSON.stringify(config.reporting_policy || {}, null, 2),
      )}</textarea></label>
    </details>
    <details class="advanced"><summary>ASPICE tailoring approval</summary>
      <p class="muted">Required when changing the ASPICE target capability, process scope, or per-process expected capability.</p>
      <label>Rationale<textarea name="tailoring_rationale" rows="3"
        placeholder="Why this ASPICE process scope or capability target is appropriate"></textarea></label>
      <label>Evidence references<textarea name="tailoring_evidence_refs" rows="3"
        placeholder="One evidence reference per line, or comma-separated"></textarea></label>
    </details>
    <button class="button primary" type="submit">Save project defaults</button>
  </form>`;
}

function renderAspiceTailoring(assurance) {
  const defaultCapability = Number(assurance.aspice_default_capability_level || 3);
  const scoped = new Set(scopedAspiceProcesses(assurance));
  const targets = assurance.aspice_process_capability_targets || {};
  const overrides = assurance.aspice_process_overrides || {};
  const rows = aspiceProcessOptions(assurance).map(([process, label]) => {
    const inScope = scoped.has(process);
    const capability = Number(targets[process] || overrides[process] || defaultCapability);
    return [
      `<label class="checkbox-label"><input type="checkbox" data-aspice-process="${escapeHtml(
        process,
      )}" value="${escapeHtml(process)}" ${inScope ? "checked" : ""}>
        <span><strong>${escapeHtml(process)}</strong><br><span class="muted">${escapeHtml(
          label,
        )}</span></span></label>`,
      `<select data-aspice-capability="${escapeHtml(process)}">
        ${[1, 2, 3]
          .map(
            (level) =>
              `<option value="${level}" ${capability === level ? "selected" : ""}>CL${level}</option>`,
          )
          .join("")}
      </select>`,
    ];
  });
  return `<section class="stack">
    <div>
      <h3>ASPICE process scope and expected capability</h3>
      <p class="muted">The project ASPICE target is the default. In-scope process rows define the expected capability target used for validation and release evidence.</p>
    </div>
    ${table(["Process", "Expected capability"], rows)}
  </section>`;
}

function aspiceProcessOptions(assurance) {
  const options = new Map(ASPICE_PROCESS_OPTIONS);
  for (const process of scopedAspiceProcesses(assurance)) {
    if (!options.has(process)) {
      options.set(process, "Configured process");
    }
  }
  return [...options.entries()].sort(([left], [right]) => left.localeCompare(right));
}

function scopedAspiceProcesses(assurance) {
  return assurance.aspice_scoped_processes?.length
    ? assurance.aspice_scoped_processes
    : DEFAULT_ASPICE_SCOPED_PROCESSES;
}

function renderSchemaManagement(schemas) {
  return `<h2>Canonical form tailoring</h2>
    <p class="muted">Disable optional fields or change mandatory fields without creating a second schema authority.</p>
    <form id="schema-form" class="stack">
      <label>Artefact type<select name="artefact_type">
        ${schemas
          .map(
            (schema) =>
              `<option value="${escapeHtml(schema.artefact_type)}">${escapeHtml(
                schema.artefact_type,
              )}</option>`,
          )
          .join("")}
      </select></label>
      <label>Disabled fields, one per line<textarea name="disabled_fields"></textarea></label>
      <label>Mandatory fields, one per line<textarea name="mandatory_fields"></textarea></label>
      <button class="button primary" type="submit">Save schema tailoring</button>
    </form>`;
}

function renderConnectors(connectors, capabilities) {
  return table(
    ["Connector", "Repository", "Branch", "Status", "Actions"],
    connectors.map((connector) => [
      escapeHtml(connector.name || `${connector.owner}/${connector.repository}`),
      escapeHtml(`${connector.owner}/${connector.repository}`),
      escapeHtml(connector.default_branch),
      statusBadge(connector.status),
      `<div class="row-actions">
        ${
          capabilities["repository.scan"]
            ? actionButton("scan-connector", "Scan", {
                id: connector.repository_connector_id,
              })
            : ""
        }
        ${
          capabilities["repository.manage"]
            ? actionButton("test-connector", "Test", {
                id: connector.repository_connector_id,
              }) +
              actionButton("delete-connector", "Delete", {
                id: connector.repository_connector_id,
                variant: "danger",
              })
            : ""
        }
      </div>`,
    ]),
    {
      emptyTitle: "No repository connector",
      emptyDetail: "An administrator can connect a GitHub repository.",
    },
  );
}

function renderConnectorForm() {
  return `<details class="advanced">
    <summary>Add GitHub connector</summary>
    <form id="connector-form" class="form-grid">
      <label>Name<input name="name"></label>
      <label class="field-required">Authentication<select name="auth_mode">
        <option value="access_token">Access token</option>
        <option value="github_app">GitHub App</option>
      </select></label>
      <label class="field-required">Owner<input name="owner" required></label>
      <label class="field-required">Repository<input name="repository" required></label>
      <label>Default branch<input name="default_branch" value="main"></label>
      <label>Access token<input name="access_token" type="password"></label>
      <label>GitHub App ID<input name="app_id"></label>
      <label>Installation ID<input name="installation_id"></label>
      <label class="full">Private key PEM<textarea name="private_key_pem"></textarea></label>
      <div class="full"><button class="button primary" type="submit">Create connector</button></div>
    </form>
  </details>`;
}

function renderAudit(events) {
  return table(
    ["Time", "Event", "Actor", "Affected evidence"],
    [...events]
      .reverse()
      .slice(0, 50)
      .map((event) => [
        escapeHtml(event.created_at || ""),
        escapeHtml(event.event_type),
        escapeHtml(event.actor_user_id || "system"),
        escapeHtml(
          [...(event.affected_artefact_ids || []), ...(event.affected_relationship_ids || [])].join(
            ", ",
          ),
        ),
      ]),
    { emptyTitle: "No audit events" },
  );
}

function bindMembers(ctx, members) {
  const form = document.querySelector("#member-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      await runAction(
        button,
        () =>
          ctx.api.addMember(ctx.state.projectId, {
            user_id: form.elements.user_id.value,
            role: form.elements.role.value,
          }),
        "Project member added.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  document.querySelector("#members-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action=remove-member]");
    if (!button || !requireConfirmation("Remove all project roles for this user?")) {
      return;
    }
    try {
      await runAction(
        button,
        () => ctx.api.removeMember(ctx.state.projectId, button.dataset.id),
        "Project member removed.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function bindConfiguration(ctx, config) {
  const form = document.querySelector("#config-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      const aspiceDefaultCapability = Number(form.elements.aspice_capability.value);
      const aspiceScopedProcesses = selectedAspiceProcesses(form);
      if (!aspiceScopedProcesses.length) {
        throw new Error("Select at least one in-scope ASPICE process.");
      }
      const aspiceProcessOverrides = aspiceOverridesFor(form, aspiceScopedProcesses, aspiceDefaultCapability);
      const assuranceConfiguration = {
        ...(config.assurance_configuration || {}),
        asil_level: form.elements.asil_level.value,
        aspice_default_capability_level: aspiceDefaultCapability,
        aspice_scoped_processes: aspiceScopedProcesses,
        aspice_process_overrides: aspiceProcessOverrides,
        r155_applicable: form.elements.r155_applicable.checked,
        r156_applicable: form.elements.r156_applicable.checked,
        visibility_policy: form.elements.visibility_policy.value,
      };
      const aspiceChanged = aspiceComparisonKey(config.assurance_configuration || {}) !==
        aspiceComparisonKey(assuranceConfiguration);
      const tailoringRationale = form.elements.tailoring_rationale.value.trim();
      const tailoringEvidenceRefs = listValue(form.elements.tailoring_evidence_refs.value);
      if (aspiceChanged && (!tailoringRationale || !tailoringEvidenceRefs.length)) {
        throw new Error(
          "ASPICE process scope or capability changes require rationale and at least one evidence reference.",
        );
      }
      const payload = {
        version_update_mode: form.elements.version_update_mode.value,
        sphinx_source_root: form.elements.sphinx_source_root.value.trim() || null,
        baseline_policy: readJson(form.elements.baseline_policy.value, "Baseline policy"),
        validation_policy: readJson(
          form.elements.validation_policy.value,
          "Validation policy",
        ),
        reporting_policy: readJson(
          form.elements.reporting_policy.value,
          "Reporting policy",
        ),
        assurance_configuration: assuranceConfiguration,
      };
      if (tailoringRationale || tailoringEvidenceRefs.length) {
        payload.tailoring_rationale = tailoringRationale;
        payload.tailoring_evidence_refs = tailoringEvidenceRefs;
      }
      await runAction(
        button,
        () => ctx.api.updateProjectConfig(ctx.state.projectId, payload),
        "Project defaults saved.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  bindAspiceScopeControls(form);
}

function bindAspiceScopeControls(form) {
  const sync = () => {
    const checkboxes = [...form.querySelectorAll("[data-aspice-process]")];
    for (const select of form.querySelectorAll("[data-aspice-capability]")) {
      const checkbox = checkboxes.find(
        (item) => item.dataset.aspiceProcess === select.dataset.aspiceCapability,
      );
      select.disabled = !checkbox?.checked;
    }
  };
  for (const checkbox of form.querySelectorAll("[data-aspice-process]")) {
    checkbox.addEventListener("change", sync);
  }
  sync();
}

function selectedAspiceProcesses(form) {
  return [...form.querySelectorAll("[data-aspice-process]:checked")]
    .map((checkbox) => checkbox.value)
    .sort();
}

function aspiceOverridesFor(form, scopedProcesses, defaultCapability) {
  const scoped = new Set(scopedProcesses);
  const overrides = {};
  for (const select of form.querySelectorAll("[data-aspice-capability]")) {
    const process = select.dataset.aspiceCapability;
    const capability = Number(select.value);
    if (scoped.has(process) && capability !== defaultCapability) {
      overrides[process] = capability;
    }
  }
  return overrides;
}

function aspiceComparisonKey(assurance) {
  const defaultCapability = Number(assurance.aspice_default_capability_level || 3);
  const scopedProcesses = [...new Set(scopedAspiceProcesses(assurance))].sort();
  const targets = assurance.aspice_process_capability_targets || {};
  const overrides = assurance.aspice_process_overrides || {};
  return JSON.stringify({
    defaultCapability,
    scopedProcesses,
    processTargets: Object.fromEntries(
      scopedProcesses.map((process) => [
        process,
        Number(targets[process] || overrides[process] || defaultCapability),
      ]),
    ),
  });
}

function listValue(value) {
  return value
    .split(/\n|,/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function bindSchemaManagement(ctx, schemas) {
  const form = document.querySelector("#schema-form");
  if (!form || !schemas.length) {
    return;
  }
  const populate = () => {
    const schema = schemas.find(
      (item) => item.artefact_type === form.elements.artefact_type.value,
    );
    form.elements.disabled_fields.value = (schema?.disabled_fields || []).join("\n");
    form.elements.mandatory_fields.value = (schema?.mandatory_fields || []).join("\n");
  };
  form.elements.artefact_type.addEventListener("change", populate);
  populate();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const lines = (value) =>
      value
        .split(/\n|,/)
        .map((item) => item.trim())
        .filter(Boolean);
    try {
      await runAction(
        button,
        () =>
          ctx.api.updateSchema(
            ctx.state.projectId,
            form.elements.artefact_type.value,
            {
              disabled_fields: lines(form.elements.disabled_fields.value),
              mandatory_fields: lines(form.elements.mandatory_fields.value),
            },
          ),
        "Schema tailoring saved.",
      );
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function bindConnectors(ctx, connectors) {
  const form = document.querySelector("#connector-form");
  form?.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    const authMode = form.elements.auth_mode.value;
    const payload = {
      provider: "github",
      auth_mode: authMode,
      name: form.elements.name.value.trim() || null,
      owner: form.elements.owner.value.trim(),
      repository: form.elements.repository.value.trim(),
      default_branch: form.elements.default_branch.value.trim() || "main",
    };
    if (authMode === "access_token") {
      payload.access_token = { access_token: form.elements.access_token.value || null };
    } else {
      payload.github_app = {
        app_id: form.elements.app_id.value.trim(),
        installation_id: form.elements.installation_id.value.trim(),
        private_key_pem: form.elements.private_key_pem.value || null,
      };
    }
    try {
      await runAction(
        button,
        () => ctx.api.createConnector(ctx.state.projectId, payload),
        "Repository connector created.",
      );
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  document.querySelector("#connectors-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const connector = connectors.find(
      (item) => item.repository_connector_id === button.dataset.id,
    );
    if (!connector) {
      return;
    }
    const action = button.dataset.action;
    if (
      action === "delete-connector" &&
      !requireConfirmation("Delete this repository connector?")
    ) {
      return;
    }
    try {
      if (action === "delete-connector") {
        await runAction(
          button,
          () => ctx.api.deleteConnector(ctx.state.projectId, connector.repository_connector_id),
          "Repository connector deleted.",
        );
      } else {
        await runAction(
          button,
          () =>
            ctx.api.connectorAction(
              ctx.state.projectId,
              connector.repository_connector_id,
              action === "scan-connector" ? "scan" : "test",
              action === "scan-connector" ? { trigger: "manual" } : {},
            ),
          action === "scan-connector" ? "Repository scan started." : "Connector test completed.",
        );
      }
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function bindGlobalAdministration(ctx) {
  const projectForm = document.querySelector("#create-project-form");
  projectForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = projectForm.querySelector("button[type=submit]");
    try {
      const response = await runAction(
        button,
        () =>
          ctx.api.createProject({
            project_key: projectForm.elements.project_key.value.trim(),
            name: projectForm.elements.name.value.trim(),
            description: projectForm.elements.description.value.trim(),
            assurance_configuration: {
              asil_level: projectForm.elements.asil_level.value,
              aspice_default_capability_level: Number(
                projectForm.elements.aspice_capability.value,
              ),
            },
          }),
        "Project created.",
      );
      localStorage.setItem("aac_project_id", response.data.project_id);
      await ctx.reloadSession();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  const userForm = document.querySelector("#create-user-form");
  userForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = userForm.querySelector("button[type=submit]");
    try {
      await runAction(
        button,
        () =>
          ctx.api.createUser({
            username: userForm.elements.username.value.trim(),
            display_name: userForm.elements.display_name.value.trim(),
            email: userForm.elements.email.value.trim(),
            password: userForm.elements.password.value,
            roles: userForm.elements.global_role.value
              ? [userForm.elements.global_role.value]
              : [],
          }),
        "User account created.",
      );
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}
