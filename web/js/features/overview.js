import { escapeHtml, metric, setPage, statusBadge, table } from "../components/ui.js";

export async function renderOverview(ctx) {
  const workspace = ctx.state.workspace;
  setPage({
    eyebrow: workspace.project.project_key,
    title: `Welcome, ${workspace.actor.display_name}`,
    description: "Current assurance work and release readiness for the selected project.",
  });

  const summary = workspace.summary;
  const work = workspace.actionable_work
    .map(
      (item) => `<li><a class="work-item" href="${escapeHtml(item.route)}">
        <span class="count">${escapeHtml(item.count)}</span>
        <span><strong>${escapeHtml(item.label)}</strong><br>
        <span class="muted">${escapeHtml(item.severity)}</span></span>
      </a></li>`,
    )
    .join("");
  const latest = summary.baselines.latest;
  const baselineRows = latest
    ? [
        [
          escapeHtml(latest.name),
          statusBadge(latest.state),
          statusBadge(latest.release_gate_status),
          escapeHtml((latest.allowed_actions || []).join(", ") || "No action available"),
        ],
      ]
    : [];

  ctx.root.innerHTML = `
    <section class="grid four" aria-label="Project metrics">
      ${metric(summary.artefacts.total, "Artefacts")}
      ${metric(summary.validation.open, "Open validation issues")}
      ${metric(summary.suspects.open, "Open suspect states")}
      ${metric(summary.jobs.active, "Active jobs")}
    </section>
    <section class="grid two" style="margin-top: 1rem">
      <article class="card">
        <div class="card-header">
          <div>
            <h2>My work</h2>
            <p class="muted">Items requiring review or monitoring.</p>
          </div>
        </div>
        <ul class="work-list">${work}</ul>
      </article>
      <article class="card">
        <h2>Release readiness</h2>
        <p>${statusBadge(workspace.release_readiness.state)}</p>
        ${
          workspace.release_readiness.blockers.length
            ? `<ul>${workspace.release_readiness.blockers
                .map(
                  (blocker) =>
                    `<li>${escapeHtml(blocker.count)} ${escapeHtml(
                      blocker.kind.replaceAll("_", " "),
                    )}</li>`,
                )
                .join("")}</ul>`
            : '<p class="notice success">No current validation, suspect-state, or project-lock blocker is reported.</p>'
        }
        <a class="button secondary" href="#/release">Open release workspace</a>
      </article>
    </section>
    <section class="card" style="margin-top: 1rem">
      <div class="card-header">
        <div>
          <h2>Latest baseline</h2>
          <p class="muted">The latest server-reported release candidate.</p>
        </div>
      </div>
      ${table(["Baseline", "State", "Gate", "Available actions"], baselineRows, {
        emptyTitle: "No baseline exists",
        emptyDetail: "Create one from the Release workspace after resolving evidence blockers.",
      })}
    </section>
  `;
}
