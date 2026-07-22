import {
  actionButton,
  escapeHtml,
  jsonView,
  requireConfirmation,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

let pollTimer = null;

export async function renderJobs(ctx) {
  window.clearTimeout(pollTimer);
  setPage({
    eyebrow: "Workspace",
    title: "Background jobs",
    description: "Monitor imports, validation, impact, baselines, reports, and repository scans.",
  });
  const response = await ctx.api.jobs(ctx.state.projectId);
  const jobs = response.data || [];
  ctx.root.innerHTML = `
    <section class="card">
      <div class="card-header">
        <div><h2>Project jobs</h2><p class="muted">Active work refreshes every four seconds.</p></div>
        <label>Filter
          <select id="job-filter">
            <option value="active">Active</option>
            <option value="all">All</option>
            <option value="failed">Failed</option>
            <option value="completed">Completed</option>
          </select>
        </label>
      </div>
      <div id="jobs-table">${renderJobTable(jobs.filter((job) => isActive(job.state)))}</div>
      <div id="job-detail"></div>
    </section>
  `;
  document.querySelector("#job-filter").addEventListener("change", (event) => {
    const value = event.target.value;
    const filtered = jobs.filter((job) => {
      if (value === "all") return true;
      if (value === "active") return isActive(job.state);
      return job.state === value;
    });
    document.querySelector("#jobs-table").innerHTML = renderJobTable(filtered);
  });
  document.querySelector("#jobs-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const job = jobs.find((item) => item.job_id === button.dataset.id);
    if (!job) {
      return;
    }
    if (button.dataset.action === "cancel-job") {
      if (!requireConfirmation("Request cancellation for this job?")) {
        return;
      }
      try {
        await runAction(
          button,
          () => ctx.api.cancelJob(job.job_id),
          "Job cancellation requested.",
        );
        await ctx.refreshWorkspace();
        await ctx.refresh();
      } catch (error) {
        ctx.notify(error.message, "error");
      }
      return;
    }
    const target = document.querySelector("#job-detail");
    target.innerHTML = "Loading job detail...";
    try {
      const detail = await ctx.api.job(job.job_id);
      target.innerHTML = `<details class="advanced" open><summary>Job detail</summary>${jsonView(
        detail.data,
      )}</details>`;
    } catch (error) {
      target.innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`;
    }
  });
  if (jobs.some((job) => isActive(job.state)) && ctx.isCurrentRoute("jobs")) {
    pollTimer = window.setTimeout(() => ctx.refresh(), 4000);
  }
}

function renderJobTable(jobs) {
  return table(
    ["Job", "State", "Progress", "Committed work", "Actions"],
    [...jobs].reverse().map((job) => [
      `<strong>${escapeHtml(job.job_type.replaceAll("_", " "))}</strong><br>
        <span class="muted">${escapeHtml(job.job_id)}</span>`,
      statusBadge(job.state),
      `<div class="progress" role="progressbar" aria-valuemin="0" aria-valuemax="100"
        aria-valuenow="${escapeHtml(job.progress_percent)}">
        <span style="width:${escapeHtml(job.progress_percent)}%"></span>
      </div><span class="help">${escapeHtml(job.progress_percent)}%</span>`,
      escapeHtml(job.last_committed_unit || "None reported"),
      `<div class="row-actions">
        ${actionButton("view-job", "View", { id: job.job_id })}
        ${
          job.allowed_actions?.includes("cancel")
            ? actionButton("cancel-job", "Cancel", { id: job.job_id, variant: "danger" })
            : ""
        }
      </div>`,
    ]),
    {
      emptyTitle: "No jobs in this view",
      emptyDetail: "Long-running operations will appear here.",
    },
  );
}

function isActive(state) {
  return ["queued", "running", "waiting_for_user", "blocked"].includes(state);
}
