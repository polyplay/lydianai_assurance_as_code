import {
  actionButton,
  escapeHtml,
  requireConfirmation,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

export async function renderValidation(ctx) {
  setPage({
    eyebrow: "Assurance",
    title: "Validation",
    description: "Review evidence completeness and resolve issues before baselining or release.",
    actions: ctx.state.workspace.capabilities["validation.run"]
      ? '<button id="run-validation" class="button primary" type="button">Run validation</button>'
      : "",
  });
  const [statusResponse, issuesResponse] = await Promise.all([
    ctx.api.validationStatus(ctx.state.projectId),
    ctx.api.validationIssues(ctx.state.projectId),
  ]);
  const status = statusResponse.data;
  const issues = issuesResponse.data || [];

  ctx.root.innerHTML = `
    <section class="grid three">
      <div class="card metric"><strong>${escapeHtml(status.open_issue_count)}</strong><span>Open issues</span></div>
      <div class="card metric"><strong>${escapeHtml(
        status.critical_open_issue_count,
      )}</strong><span>Critical open issues</span></div>
      <div class="card metric"><strong>${escapeHtml(
        status.issue_count,
      )}</strong><span>Total issue records</span></div>
    </section>
    <section class="card" style="margin-top: 1rem">
      <div class="card-header">
        <div><h2>Validation issues</h2><p class="muted">Server-evaluated findings and remediation guidance.</p></div>
        <label>Filter
          <select id="issue-filter">
            <option value="open">Open</option>
            <option value="all">All</option>
            <option value="critical">Critical</option>
            <option value="suppressed">Suppressed</option>
          </select>
        </label>
      </div>
      <div id="issues-table">${renderIssueTable(issues.filter((item) => item.status === "open"))}</div>
    </section>
  `;

  document.querySelector("#issue-filter").addEventListener("change", (event) => {
    const value = event.target.value;
    const filtered = issues.filter((issue) => {
      if (value === "all") return true;
      if (value === "critical") return issue.severity === "critical" && issue.status === "open";
      return issue.status === value;
    });
    document.querySelector("#issues-table").innerHTML = renderIssueTable(filtered);
  });
  document.querySelector("#issues-table").addEventListener("click", (event) =>
    handleIssueAction(ctx, event, issues),
  );
  document.querySelector("#run-validation")?.addEventListener("click", async (event) => {
    try {
      await runAction(
        event.currentTarget,
        () => ctx.api.runValidation(ctx.state.projectId),
        "Validation started.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function renderIssueTable(issues) {
  return table(
    ["Severity", "Finding", "Affected evidence", "Status", "Actions"],
    issues.map((issue) => [
      statusBadge(issue.severity),
      `<strong>${escapeHtml(issue.rule_id)}</strong><br>${escapeHtml(issue.message)}
        ${issue.remediation_hint ? `<p class="help">${escapeHtml(issue.remediation_hint)}</p>` : ""}`,
      escapeHtml([...(issue.affected_artefacts || []), ...(issue.affected_relationships || [])].join(", ")),
      statusBadge(issue.status),
      `<div class="row-actions">
        ${(issue.allowed_actions || [])
          .map((action) =>
            actionButton(`issue-${action}`, action === "suppress" ? "Suppress" : "Reopen", {
              id: issue.validation_issue_id,
              variant: action === "suppress" ? "danger" : "secondary",
            }),
          )
          .join("")}
      </div>`,
    ]),
    {
      emptyTitle: "No issues in this view",
      emptyDetail: "Run validation after changing evidence to refresh findings.",
    },
  );
}

async function handleIssueAction(ctx, event, issues) {
  const button = event.target.closest("[data-action]");
  if (!button) {
    return;
  }
  const issue = issues.find((item) => item.validation_issue_id === button.dataset.id);
  const action = button.dataset.action.replace("issue-", "");
  if (!issue) {
    return;
  }
  let payload = {};
  if (action === "suppress") {
    if (!requireConfirmation("Suppress this issue? This should be supported by an approved waiver.")) {
      return;
    }
    const reason = window.prompt("Suppression reason");
    if (!reason) {
      return;
    }
    payload = { reason };
  }
  try {
    await runAction(
      button,
      () =>
        ctx.api.validationIssueAction(
          ctx.state.projectId,
          issue.validation_issue_id,
          action,
          payload,
        ),
      `Validation issue ${action === "suppress" ? "suppressed" : "reopened"}.`,
    );
    await ctx.refreshWorkspace();
    await ctx.refresh();
  } catch (error) {
    ctx.notify(error.message, "error");
  }
}
