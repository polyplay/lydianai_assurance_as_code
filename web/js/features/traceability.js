import {
  escapeHtml,
  jsonView,
  runAction,
  setPage,
  table,
} from "../components/ui.js";

export async function renderTraceability(ctx) {
  setPage({
    eyebrow: "Evidence",
    title: "Traceability",
    description: "Follow evidence forward to implementation and verification or backward to its basis.",
  });
  const [artefactsResponse, matrixResponse] = await Promise.all([
    ctx.api.artefacts(ctx.state.projectId),
    ctx.api.traceabilityMatrix(ctx.state.projectId),
  ]);
  const artefacts = artefactsResponse.data || [];
  const matrix = matrixResponse.data || [];
  const titles = Object.fromEntries(artefacts.map((item) => [item.artefact_id, item.title]));

  ctx.root.innerHTML = `
    <section class="card">
      <h2>Explore an artefact</h2>
      <form id="trace-form" class="form-grid">
        <label class="field-required">Artefact
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
        <label>Direction
          <select name="direction">
            <option value="">Forward and backward</option>
            <option value="forward">Forward only</option>
            <option value="backward">Backward only</option>
          </select>
        </label>
        <div class="full"><button class="button primary" type="submit">Trace artefact</button></div>
      </form>
      <div id="trace-result" style="margin-top: 1rem"></div>
    </section>
    <section class="card" style="margin-top: 1rem">
      <div class="card-header"><div><h2>Traceability matrix</h2>
      <p class="muted">${escapeHtml(matrix.length)} current relationships</p></div></div>
      ${table(
        ["Source", "Relationship", "Target"],
        matrix.map((item) => [
          escapeHtml(titles[item.source_artefact_id] || item.source_artefact_id),
          escapeHtml(item.relationship_type),
          escapeHtml(titles[item.target_artefact_id] || item.target_artefact_id),
        ]),
        {
          emptyTitle: "No traceability relationships",
          emptyDetail: "Create relationships from the Evidence workspace.",
        },
      )}
    </section>
  `;

  document.querySelector("#trace-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const button = form.querySelector("button[type=submit]");
    const result = document.querySelector("#trace-result");
    result.innerHTML = "Tracing evidence...";
    try {
      const response = await runAction(button, () =>
        ctx.api.trace(
          ctx.state.projectId,
          form.elements.artefact_id.value,
          form.elements.direction.value,
        ),
      );
      result.innerHTML = renderTraceResult(response.data, titles);
    } catch (error) {
      result.innerHTML = `<p class="form-error" role="alert">${escapeHtml(error.message)}</p>`;
    }
  });
}

function renderTraceResult(data, titles) {
  const edges = [];
  for (const direction of ["forward", "backward"]) {
    const values = data?.[direction];
    if (!Array.isArray(values)) {
      continue;
    }
    for (const item of values) {
      if (typeof item === "string") {
        edges.push([direction, titles[item] || item, ""]);
      } else {
        edges.push([
          direction,
          titles[item.artefact_id || item.target_artefact_id || item.source_artefact_id] ||
            item.artefact_id ||
            item.target_artefact_id ||
            item.source_artefact_id ||
            "",
          item.relationship_type || item.path || "",
        ]);
      }
    }
  }
  return `<h3>Trace result</h3>
    ${table(
      ["Direction", "Connected evidence", "Relationship or path"],
      edges.map((row) => row.map(escapeHtml)),
      { emptyTitle: "No connected evidence found" },
    )}
    <details class="advanced"><summary>Raw trace response</summary>${jsonView(data)}</details>`;
}
