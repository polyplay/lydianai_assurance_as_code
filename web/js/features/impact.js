import {
  actionButton,
  escapeHtml,
  jsonView,
  runAction,
  setPage,
  statusBadge,
  table,
} from "../components/ui.js";

export async function renderImpact(ctx) {
  setPage({
    eyebrow: "Assurance",
    title: "Impact and suspect states",
    description: "Assess downstream consequences and clear suspect evidence with a recorded basis.",
  });
  const [artefactsResponse, suspectsResponse] = await Promise.all([
    ctx.api.artefacts(ctx.state.projectId),
    ctx.api.suspects(ctx.state.projectId),
  ]);
  const artefacts = artefactsResponse.data || [];
  const suspects = suspectsResponse.data || [];
  const titles = Object.fromEntries(artefacts.map((item) => [item.artefact_id, item.title]));

  ctx.root.innerHTML = `
    <section class="card">
      <h2>Run impact analysis</h2>
      <form id="impact-form" class="form-grid">
        <label class="field-required">Changed artefact
          <select name="artefact_id" required>
            <option value="">Select an artefact...</option>
            ${artefacts
              .map(
                (item) =>
                  `<option value="${escapeHtml(item.artefact_id)}">${escapeHtml(
                    item.title,
                  )} · ${escapeHtml(item.artefact_type)}</option>`,
              )
              .join("")}
          </select>
        </label>
        <div class="full"><button class="button primary" type="submit">Analyze impact</button></div>
      </form>
      <div id="impact-result"></div>
    </section>
    <section class="card" style="margin-top: 1rem">
      <div class="card-header"><div><h2>Suspect states</h2>
      <p class="muted">Evidence requiring review after an upstream change.</p></div></div>
      <div id="suspect-table">${renderSuspects(suspects, titles)}</div>
    </section>
  `;

  document.querySelector("#impact-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const target = document.querySelector("#impact-result");
    try {
      const response = await runAction(
        button,
        () => ctx.api.runImpact(ctx.state.projectId, form.elements.artefact_id.value),
        "Impact analysis started.",
      );
      target.innerHTML = `<h3>Analysis submitted</h3>${jsonView(response.data)}`;
      await ctx.refreshWorkspace();
    } catch (error) {
      target.innerHTML = `<p class="form-error" role="alert">${escapeHtml(error.message)}</p>`;
    }
  });
  document.querySelector("#suspect-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action=clear-suspect]");
    if (!button) {
      return;
    }
    const reason = window.prompt("Why is this suspect state safe to clear?");
    if (!reason) {
      return;
    }
    try {
      await runAction(
        button,
        () =>
          ctx.api.clearSuspect(ctx.state.projectId, button.dataset.id, {
            clearing_method: "manual_review",
            reason,
            evidence_refs: [],
          }),
        "Suspect state cleared.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function renderSuspects(suspects, titles) {
  return table(
    ["Affected evidence", "Trigger", "Depth", "Status", "Actions"],
    suspects.map((suspect) => [
      escapeHtml(titles[suspect.artefact_id] || suspect.artefact_id),
      escapeHtml(titles[suspect.trigger_artefact_id] || suspect.trigger_artefact_id),
      escapeHtml(suspect.propagation_depth),
      statusBadge(suspect.status),
      `<div class="row-actions">${
        suspect.allowed_actions?.includes("clear")
          ? actionButton("clear-suspect", "Clear", { id: suspect.suspect_state_id })
          : ""
      }</div>`,
    ]),
    {
      emptyTitle: "No suspect states",
      emptyDetail: "No downstream evidence currently requires suspect review.",
    },
  );
}
