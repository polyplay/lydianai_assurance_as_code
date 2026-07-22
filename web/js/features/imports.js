import {
  actionButton,
  emptyState,
  escapeHtml,
  jsonView,
  readJson,
  requireConfirmation,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

let selectedImportId = "";
let pollTimer = null;

export async function renderImports(ctx) {
  window.clearTimeout(pollTimer);
  setPage({
    eyebrow: "Evidence",
    title: "Sphinx-Needs imports",
    description: "Submit exported evidence, monitor processing, and resolve detected conflicts.",
  });
  const response = await ctx.api.imports(ctx.state.projectId);
  const imports = response.data || [];
  if (selectedImportId && !imports.some((item) => item.import_run_id === selectedImportId)) {
    selectedImportId = "";
  }
  const canStart = ctx.state.workspace.capabilities["import.start"];

  ctx.root.innerHTML = `
    <section class="record-workspace">
      <article id="import-history" class="card">
        <div class="card-header">
          <div><h2>Import history</h2>
          <p class="muted">Runs refresh automatically while work is active.</p></div>
        </div>
        <div id="imports-table">${renderImportsTable(imports)}</div>
      </article>
      <article id="import-detail" class="card record-detail" tabindex="-1">
        ${
          selectedImportId
            ? "Loading import details..."
            : emptyState("Select an import", "Open a run to review diagnostics and decisions.")
        }
      </article>
    </section>
    <section id="start-import-panel" class="card section-gap">
      <h2>Start import</h2>
      ${
        canStart
          ? `<form id="import-form" class="stack content-form">
            <label class="field-required">Source root
              <input name="source_root" required placeholder="docs/">
            </label>
            <label>Conflict behavior
              <select name="version_update_mode">
                <option value="ask_user">Ask for decisions</option>
                <option value="automatic_new_version">Create revisions automatically</option>
              </select>
            </label>
            <label class="field-required">Sphinx-Needs JSON file
              <input id="import-file" type="file" accept=".json,application/json">
            </label>
            <details class="advanced">
              <summary>Paste JSON instead</summary>
              <label>Export JSON
                <textarea id="import-json" rows="14" placeholder='{"versions": {...}}'></textarea>
              </label>
            </details>
            <button class="button primary" type="submit">Start import</button>
          </form>`
          : '<p class="notice">Your current role cannot start an import.</p>'
      }
    </section>
  `;

  bindImportList(ctx, imports);
  if (canStart) {
    bindImportForm(ctx);
  }
  if (selectedImportId) {
    await renderImportDetail(ctx, selectedImportId);
  }
  if (imports.some((item) => isActive(item.state)) && ctx.isCurrentRoute("imports")) {
    pollTimer = window.setTimeout(() => ctx.refresh(), 4000);
  }
}

function renderImportsTable(imports) {
  const rows = [...imports].reverse().map((run) => [
    `<strong>${escapeHtml(run.import_run_id)}</strong><br>
      <span class="muted">${escapeHtml(run.version_update_mode)}</span>`,
    statusBadge(run.state),
    escapeHtml(run.summary?.changed ?? run.summary?.created ?? ""),
    `<div class="row-actions">
      ${actionButton("open-import", "Open", { id: run.import_run_id })}
      ${
        run.allowed_actions?.includes("cancel")
          ? actionButton("cancel-import", "Cancel", {
              id: run.import_run_id,
              variant: "danger",
            })
          : ""
      }
    </div>`,
  ]);
  return table(["Import run", "State", "Changes", "Actions"], rows, {
    emptyTitle: "No imports yet",
    emptyDetail: "Submit a Sphinx-Needs JSON export to begin.",
  });
}

function bindImportList(ctx, imports) {
  document.querySelector("#imports-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const run = imports.find((item) => item.import_run_id === button.dataset.id);
    if (!run) {
      return;
    }
    if (button.dataset.action === "open-import") {
      selectedImportId = run.import_run_id;
      await renderImportDetail(ctx, selectedImportId, { reveal: true });
      return;
    }
    if (
      button.dataset.action === "cancel-import" &&
      requireConfirmation("Request cancellation for this import?")
    ) {
      try {
        await runAction(
          button,
          () => ctx.api.cancelImport(ctx.state.projectId, run.import_run_id),
          "Import cancellation requested.",
        );
        await ctx.refreshWorkspace();
        await ctx.refresh();
      } catch (error) {
        ctx.notify(error.message, "error");
      }
    }
  });
}

function bindImportForm(ctx) {
  const form = document.querySelector("#import-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      const json = await readImportJson();
      const needs = normalizeNeeds(json);
      if (!needs.length) {
        throw new Error("The export does not contain any Sphinx-Needs records.");
      }
      const result = await runAction(
        button,
        () =>
          ctx.api.startImport(ctx.state.projectId, {
            source_root: form.elements.source_root.value.trim(),
            version_update_mode: form.elements.version_update_mode.value,
            sphinx_needs: needs,
          }),
        "Import submitted.",
      );
      selectedImportId = result.data.import_run.import_run_id;
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

async function readImportJson() {
  const file = document.querySelector("#import-file").files[0];
  if (file) {
    return readJson(await file.text(), "Sphinx-Needs file");
  }
  const pasted = document.querySelector("#import-json").value.trim();
  if (!pasted) {
    throw new Error("Choose a JSON file or paste an export.");
  }
  return readJson(pasted, "Sphinx-Needs JSON");
}

function normalizeNeeds(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload.sphinx_needs)) {
    return payload.sphinx_needs;
  }
  if (Array.isArray(payload.needs)) {
    return payload.needs;
  }
  if (payload.needs && typeof payload.needs === "object") {
    return Object.values(payload.needs);
  }
  if (payload.versions && typeof payload.versions === "object") {
    const version =
      payload.versions[payload.current_version] ||
      payload.versions[Object.keys(payload.versions).at(-1)];
    if (Array.isArray(version?.needs)) {
      return version.needs;
    }
    if (version?.needs && typeof version.needs === "object") {
      return Object.values(version.needs);
    }
  }
  return [];
}

async function renderImportDetail(ctx, importId, { reveal = false } = {}) {
  const container = document.querySelector("#import-detail");
  container.innerHTML = "Loading import details...";
  try {
    const response = await ctx.api.importRun(ctx.state.projectId, importId);
    const run = response.data;
    const pending = (run.items || []).filter((item) => item.decision_status === "pending");
    container.innerHTML = `
      <div class="card-header">
        <div><h2>Import details</h2><p class="muted">${escapeHtml(run.import_run_id)}</p></div>
        ${statusBadge(run.state)}
      </div>
      ${renderProgress(run)}
      <div class="grid three" style="margin: 1rem 0">
        <div class="metric"><strong>${escapeHtml(run.items?.length || 0)}</strong><span>Items</span></div>
        <div class="metric"><strong>${escapeHtml(pending.length)}</strong><span>Decisions</span></div>
        <div class="metric"><strong>${escapeHtml(run.diagnostics?.length || 0)}</strong><span>Diagnostics</span></div>
      </div>
      ${
        pending.length && run.allowed_actions?.includes("submit_decisions")
          ? renderDecisionForm(pending)
          : ""
      }
      <h3>Items</h3>
      ${renderItems(run.items || [])}
      <h3 style="margin-top: 1rem">Diagnostics</h3>
      ${renderDiagnostics(run.diagnostics || [])}
      <details class="advanced"><summary>Technical run data</summary>${jsonView(run)}</details>
    `;
    bindDecisionForm(ctx, run, pending);
    if (reveal) {
      container.scrollIntoView({ block: "start", behavior: "auto" });
      container.focus({ preventScroll: true });
    }
  } catch (error) {
    container.innerHTML = `<p class="form-error" role="alert">${escapeHtml(error.message)}</p>`;
    if (reveal) {
      container.scrollIntoView({ block: "start", behavior: "auto" });
      container.focus({ preventScroll: true });
    }
  }
}

function renderProgress(run) {
  const completed = !isActive(run.state);
  const total = Number(run.summary?.total || run.items?.length || 0);
  const processed = Number(run.summary?.processed || total);
  const percent = completed ? 100 : total ? Math.min(99, Math.round((processed / total) * 100)) : 10;
  return `<div>
    <div class="cluster"><strong>Progress</strong><span class="muted">${escapeHtml(percent)}%</span></div>
    <div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100"
      aria-valuenow="${escapeHtml(percent)}"><span style="width:${escapeHtml(percent)}%"></span></div>
  </div>`;
}

function renderDecisionForm(pending) {
  return `<form id="decision-form" class="stack">
    <h3>Required decisions</h3>
    ${pending
      .map(
        (item) => `<label>${escapeHtml(item.source_object_id)} · ${escapeHtml(
          item.detected_change_type,
        )}
          <select name="decision.${escapeHtml(item.import_run_item_id)}">
            <option value="reject_keep_current">Keep current revision</option>
            <option value="accept_new_revision">Accept imported revision</option>
          </select>
        </label>`,
      )
      .join("")}
    <button class="button primary" type="submit">Submit decisions</button>
  </form>`;
}

function bindDecisionForm(ctx, run, pending) {
  const form = document.querySelector("#decision-form");
  if (!form) {
    return;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const decisions = pending.map((item) => ({
      decision_id: item.import_run_item_id,
      decision: form.elements.namedItem(`decision.${item.import_run_item_id}`).value,
    }));
    const button = form.querySelector("button[type=submit]");
    try {
      await runAction(
        button,
        () => ctx.api.importDecisions(ctx.state.projectId, run.import_run_id, decisions),
        "Import decisions submitted.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function renderItems(items) {
  return table(
    ["Source", "Type", "Change", "Decision"],
    items.map((item) => [
      escapeHtml(item.source_object_id),
      escapeHtml(item.artefact_type),
      statusBadge(item.detected_change_type),
      statusBadge(item.decision_status),
    ]),
    { emptyTitle: "No import items recorded" },
  );
}

function renderDiagnostics(diagnostics) {
  if (!diagnostics.length) {
    return '<p class="notice success">No diagnostics were reported.</p>';
  }
  return table(
    ["Level", "Classification", "Message"],
    diagnostics.map((item) => [
      statusBadge(item.level || "info"),
      escapeHtml(item.classification || ""),
      escapeHtml(item.message || item.source_object_id || JSON.stringify(item)),
    ]),
  );
}

function isActive(state) {
  return ![
    "completed",
    "completed_with_errors",
    "completed_no_changes_applied",
    "failed",
    "cancelled",
  ].includes(state);
}
