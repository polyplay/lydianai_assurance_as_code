import {
  actionButton,
  emptyState,
  escapeHtml,
  jsonView,
  requireConfirmation,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

let selectedBaselineId = "";

export async function renderRelease(ctx) {
  setPage({
    eyebrow: "Assurance",
    title: "Release workspace",
    description: "Create snapshots, evaluate gates, approve, release, and publish repository evidence.",
  });
  const [baselinesResponse, reportsResponse] = await Promise.all([
    ctx.api.baselines(ctx.state.projectId),
    ctx.api.reports(ctx.state.projectId),
  ]);
  const baselines = baselinesResponse.data || [];
  const reports = reportsResponse.data || [];
  if (
    selectedBaselineId &&
    !baselines.some((baseline) => baseline.baseline_id === selectedBaselineId)
  ) {
    selectedBaselineId = "";
  }
  const canCreate = ctx.state.workspace.capabilities["baseline.create"];

  ctx.root.innerHTML = `
    <section class="record-workspace">
      <article id="baseline-list" class="card">
        <div class="card-header">
          <div><h2>Baselines</h2><p class="muted">Immutable evidence snapshots and controlled state.</p></div>
        </div>
        <div id="baseline-table">${renderBaselines(baselines)}</div>
      </article>
      <article id="baseline-detail" class="card record-detail" tabindex="-1">
        ${
          selectedBaselineId
            ? "Loading baseline details..."
            : emptyState("Select a baseline", "Open a baseline to review its gate and controlled actions.")
        }
      </article>
    </section>
    <section id="create-baseline-panel" class="card section-gap">
      <h2>Create baseline</h2>
      ${
        canCreate
          ? `<form id="baseline-form" class="stack content-form">
            <label class="field-required">Name<input name="name" required></label>
            <label>Description<textarea name="description" rows="3"></textarea></label>
            <button class="button primary" type="submit">Create snapshot</button>
          </form>`
          : '<p class="notice">A project lead or administrator creates baselines.</p>'
      }
    </section>
    <section class="grid two section-gap">
      <article class="card">
        <h2>Generate report</h2>
        <form id="report-form" class="stack">
          <label>Report type
            <select name="report_type">
              <option value="evidence_bundle">Evidence bundle</option>
              <option value="traceability_matrix">Traceability matrix</option>
              <option value="validation_summary">Validation summary</option>
              <option value="baseline_comparison">Baseline comparison</option>
              <option value="release_gate">Release gate</option>
            </select>
          </label>
          <label>Baseline
            <select name="baseline_id"><option value="">Current project</option>
              ${baselines
                .map(
                  (baseline) =>
                    `<option value="${escapeHtml(baseline.baseline_id)}">${escapeHtml(
                      baseline.name,
                    )}</option>`,
                )
                .join("")}
            </select>
          </label>
          <div id="comparison-fields" class="stack" hidden>
            <label class="field-required">Earlier baseline
              <select name="left_baseline_id">
                <option value="">Select earlier baseline...</option>
                ${baselineOptions(baselines)}
              </select>
            </label>
            <label class="field-required">Later baseline
              <select name="right_baseline_id">
                <option value="">Select later baseline...</option>
                ${baselineOptions(baselines)}
              </select>
            </label>
          </div>
          <button class="button primary" type="submit">Generate JSON report</button>
        </form>
      </article>
      <article class="card">
        <h2>Generated reports</h2>
        <div id="reports-table">${renderReports(
          reports,
          ctx.state.workspace.capabilities["report.delete"],
        )}</div>
        <div id="report-detail"></div>
      </article>
    </section>
  `;

  bindBaselineList(ctx, baselines);
  if (canCreate) {
    bindBaselineForm(ctx);
  }
  bindReports(ctx, reports);
  if (selectedBaselineId) {
    await renderBaselineDetail(ctx, baselines, selectedBaselineId);
  }
}

function renderBaselines(baselines) {
  return table(
    ["Baseline", "State", "Release gate", "Actions"],
    [...baselines].reverse().map((baseline) => [
      `<strong>${escapeHtml(baseline.name)}</strong><br><span class="muted">${escapeHtml(
        baseline.baseline_id,
      )}</span>`,
      statusBadge(baseline.state),
      statusBadge(baseline.release_gate_status),
      `<div class="row-actions">${actionButton("open-baseline", "Open", {
        id: baseline.baseline_id,
      })}</div>`,
    ]),
    {
      emptyTitle: "No baselines",
      emptyDetail: "Resolve release blockers and create a controlled snapshot.",
    },
  );
}

function baselineOptions(baselines) {
  return baselines
    .map(
      (baseline) =>
        `<option value="${escapeHtml(baseline.baseline_id)}">${escapeHtml(
          baseline.name,
        )}</option>`,
    )
    .join("");
}

function bindBaselineList(ctx, baselines) {
  document.querySelector("#baseline-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action=open-baseline]");
    if (!button) {
      return;
    }
    selectedBaselineId = button.dataset.id;
    await renderBaselineDetail(ctx, baselines, selectedBaselineId, { reveal: true });
  });
}

function bindBaselineForm(ctx) {
  const form = document.querySelector("#baseline-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      const response = await runAction(
        button,
        () =>
          ctx.api.createBaseline(ctx.state.projectId, {
            name: form.elements.name.value.trim(),
            description: form.elements.description.value.trim(),
            scope: {},
          }),
        "Baseline creation started.",
      );
      selectedBaselineId = response.data.baseline?.baseline_id || "";
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

async function renderBaselineDetail(ctx, baselines, baselineId, { reveal = false } = {}) {
  const container = document.querySelector("#baseline-detail");
  const baseline = baselines.find((item) => item.baseline_id === baselineId);
  if (!baseline) {
    container.innerHTML = emptyState("Baseline not found");
    if (reveal) {
      container.scrollIntoView({ block: "start", behavior: "auto" });
      container.focus({ preventScroll: true });
    }
    return;
  }
  let latestGate = null;
  if (baseline.release_gate_status !== "not_evaluated") {
    try {
      latestGate = (await ctx.api.latestGate(ctx.state.projectId, baselineId)).data;
    } catch {
      latestGate = null;
    }
  }
  container.innerHTML = `
    <div class="card-header">
      <div><p class="eyebrow">Release candidate</p><h2>${escapeHtml(baseline.name)}</h2>
      <p class="muted">${escapeHtml(baseline.baseline_id)}</p></div>
      <div class="cluster">${statusBadge(baseline.state)} ${statusBadge(
        baseline.release_gate_status,
      )}</div>
    </div>
    <div class="cluster" id="baseline-actions">${renderBaselineActions(baseline)}</div>
    ${
      latestGate
        ? `<div style="margin-top: 1rem">
          <h3>Latest release gate</h3>
          <div class="grid three">
            <div class="metric"><strong>${escapeHtml(
              latestGate.passed_rules_count,
            )}</strong><span>Passed rules</span></div>
            <div class="metric"><strong>${escapeHtml(
              latestGate.blocking_issues?.length || 0,
            )}</strong><span>Blocking issues</span></div>
            <div class="metric"><strong>${escapeHtml(
              latestGate.open_suspect_states?.length || 0,
            )}</strong><span>Open suspects</span></div>
          </div>
          <details class="advanced"><summary>Gate evidence</summary>${jsonView(latestGate)}</details>
        </div>`
        : '<p class="notice" style="margin-top: 1rem">No release-gate result is available for this baseline.</p>'
    }
    <details class="advanced"><summary>Snapshot summary</summary>${jsonView(baseline)}</details>
  `;
  bindBaselineActions(ctx, baseline);
  if (reveal) {
    container.scrollIntoView({ block: "start", behavior: "auto" });
    container.focus({ preventScroll: true });
  }
}

function renderBaselineActions(baseline) {
  const labels = {
    run_release_gate: "Run release gate",
    approve: "Approve baseline",
    release: "Release baseline",
    publish_repository_approval: "Publish repository approval",
    cancel: "Cancel creation",
    obsolete: "Mark obsolete",
  };
  return (baseline.allowed_actions || [])
    .map((action) =>
      actionButton(`baseline-${action}`, labels[action] || action, {
        id: baseline.baseline_id,
        variant: ["cancel", "obsolete"].includes(action) ? "danger" : "secondary",
      }),
    )
    .join("");
}

function bindBaselineActions(ctx, baseline) {
  document.querySelector("#baseline-actions").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const action = button.dataset.action.replace("baseline-", "");
    if (
      ["approve", "release", "publish_repository_approval", "cancel", "obsolete"].includes(
        action,
      ) &&
      !requireConfirmation(
        action === "publish_repository_approval"
          ? "Publish repository approval for the exact released revisions?"
          : `${action.replaceAll("_", " ")} this baseline?`,
      )
    ) {
      return;
    }
    try {
      await runAction(
        button,
        () => executeBaselineAction(ctx, baseline, action),
        baselineSuccessMessage(action),
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function executeBaselineAction(ctx, baseline, action) {
  if (action === "run_release_gate") {
    return ctx.api.runReleaseGate(ctx.state.projectId, baseline.baseline_id);
  }
  if (action === "publish_repository_approval") {
    return ctx.api.publishRepositoryApproval(
      ctx.state.projectId,
      baseline.baseline_id,
      window.location.href,
    );
  }
  return ctx.api.baselineAction(
    ctx.state.projectId,
    baseline.baseline_id,
    action,
    {},
  );
}

function baselineSuccessMessage(action) {
  const messages = {
    run_release_gate: "Release-gate evaluation started.",
    approve: "Baseline approved.",
    release: "Baseline released.",
    publish_repository_approval: "Repository approval published.",
    cancel: "Baseline creation cancelled.",
    obsolete: "Baseline marked obsolete.",
  };
  return messages[action] || "Baseline updated.";
}

function renderReports(reports, canDelete) {
  return table(
    ["Report", "State", "Actions"],
    reports.map((report) => [
      escapeHtml(report.report_type),
      statusBadge(report.state),
      `<div class="row-actions">
        ${actionButton("view-report", "View", { id: report.report_id })}
        ${
          canDelete
            ? actionButton("delete-report", "Obsolete", {
                id: report.report_id,
                variant: "danger",
              })
            : ""
        }
      </div>`,
    ]),
    { emptyTitle: "No reports generated" },
  );
}

function bindReports(ctx, reports) {
  const form = document.querySelector("#report-form");
  const comparisonFields = document.querySelector("#comparison-fields");
  const updateReportFields = () => {
    const comparison = form.elements.report_type.value === "baseline_comparison";
    comparisonFields.hidden = !comparison;
    form.elements.baseline_id.closest("label").hidden = comparison;
    form.elements.left_baseline_id.required = comparison;
    form.elements.right_baseline_id.required = comparison;
  };
  form.elements.report_type.addEventListener("change", updateReportFields);
  updateReportFields();
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      const reportType = form.elements.report_type.value;
      const payload = {
        report_type: reportType,
        format: "json",
        baseline_id: form.elements.baseline_id.value || null,
      };
      if (reportType === "baseline_comparison") {
        payload.left_baseline_id = form.elements.left_baseline_id.value;
        payload.right_baseline_id = form.elements.right_baseline_id.value;
        if (payload.left_baseline_id === payload.right_baseline_id) {
          throw new Error("Choose two different baselines to compare.");
        }
        delete payload.baseline_id;
      }
      await runAction(
        button,
        () => ctx.api.generateReport(ctx.state.projectId, payload),
        "Report generation started.",
      );
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  document.querySelector("#reports-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const report = reports.find((item) => item.report_id === button.dataset.id);
    if (!report) {
      return;
    }
    const target = document.querySelector("#report-detail");
    try {
      if (button.dataset.action === "delete-report") {
        if (!requireConfirmation("Mark this report obsolete?")) {
          return;
        }
        await runAction(
          button,
          () => ctx.api.deleteReport(ctx.state.projectId, report.report_id),
          "Report marked obsolete.",
        );
        await ctx.refresh();
        return;
      }
      target.innerHTML = "Loading report...";
      const response = await ctx.api.report(ctx.state.projectId, report.report_id);
      target.innerHTML = `<details class="advanced" open><summary>Report content</summary>${jsonView(
        response.data,
      )}</details>`;
    } catch (error) {
      target.innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`;
    }
  });
}
