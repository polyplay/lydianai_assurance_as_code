import { readSchemaPayload, renderSchemaFields } from "../components/schema-form.js";
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

let selectedArtefactId = "";
let currentSchema = null;

export async function renderEvidence(ctx) {
  setPage({
    eyebrow: "Evidence",
    title: "Artefacts and relationships",
    description: "Create, revise, review, and connect canonical assurance evidence.",
  });
  const projectId = ctx.state.projectId;
  const [schemasResponse, artefactsResponse, relationshipsResponse] = await Promise.all([
    ctx.api.schemas(projectId),
    ctx.api.artefacts(projectId),
    ctx.api.relationships(projectId),
  ]);
  const schemas = schemasResponse.data.schemas || [];
  const artefacts = artefactsResponse.data || [];
  const relationships = relationshipsResponse.data || [];
  if (selectedArtefactId && !artefacts.some((item) => item.artefact_id === selectedArtefactId)) {
    selectedArtefactId = "";
  }

  ctx.root.innerHTML = `
    <section class="record-workspace">
      <article id="evidence-catalogue" class="card">
        <div class="card-header">
          <div><h2>Evidence catalogue</h2>
          <p class="muted">${escapeHtml(artefacts.length)} current artefacts</p></div>
          <label>Filter
            <input id="artefact-filter" type="search" placeholder="Title, type, status">
          </label>
        </div>
        <div id="artefact-table">${renderArtefactTable(artefacts)}</div>
      </article>
      <aside id="artefact-detail" class="card record-detail" tabindex="-1">
        ${selectedArtefactId ? "Loading selected artefact..." : emptyState("Select an artefact", "Open a catalogue item to review or revise it.")}
      </aside>
    </section>
    <section id="create-artefact-panel" class="card section-gap">
      <h2>Create artefact</h2>
      <form id="create-artefact-form" class="stack content-form">
        <label class="field-required">Artefact type
          <select id="artefact-type" name="artefact_type" required>
            <option value="">Select a type...</option>
            ${schemas
              .map(
                (schema) =>
                  `<option value="${escapeHtml(schema.artefact_type)}">${escapeHtml(
                    splitName(schema.artefact_type),
                  )}</option>`,
              )
              .join("")}
          </select>
        </label>
        <label class="field-required">Title
          <input name="title" required>
        </label>
        <label>Description
          <textarea name="description" rows="3"></textarea>
        </label>
        <label class="field-required">Source object ID
          <div class="cluster">
            <input name="source_object_id" required>
            <button id="generate-source-id" class="button secondary" type="button">Generate</button>
          </div>
        </label>
        <label>Source document
          <input name="source_document" placeholder="manual-entry">
        </label>
        <div id="schema-fields" class="form-grid"></div>
        <details class="advanced">
          <summary>Advanced JSON override</summary>
          <label>Payload JSON
            <textarea id="advanced-payload" rows="10" placeholder="Optional: replaces guided field values"></textarea>
          </label>
        </details>
        <button class="button primary" type="submit">Create artefact</button>
      </form>
    </section>
    <section id="relationships-panel" class="card section-gap">
      <div class="card-header">
        <div><h2>Relationships</h2>
        <p class="muted">Connect evidence through explicit traceability.</p></div>
      </div>
      ${renderRelationshipForm(artefacts)}
      <div id="relationship-table" style="margin-top: 1rem">
        ${renderRelationshipTable(relationships, artefacts)}
      </div>
    </section>
  `;

  bindCreateForm(ctx);
  bindCatalogue(ctx, artefacts);
  bindRelationshipForm(ctx);
  bindRelationshipTable(ctx, relationships);
  if (selectedArtefactId) {
    await renderArtefactDetail(ctx, selectedArtefactId);
  }
}

function renderArtefactTable(artefacts) {
  const rows = artefacts.map((artefact) => [
    `<strong>${escapeHtml(artefact.title)}</strong><br><span class="muted">${escapeHtml(
      artefact.artefact_id,
    )}</span>`,
    escapeHtml(splitName(artefact.artefact_type)),
    statusBadge(artefact.status),
    `<div class="row-actions">${actionButton("open-artefact", "Open", {
      id: artefact.artefact_id,
    })}</div>`,
  ]);
  return table(["Artefact", "Type", "Status", "Actions"], rows, {
    emptyTitle: "No artefacts yet",
    emptyDetail: "Create the first evidence record using the guided form.",
  });
}

function renderRelationshipForm(artefacts) {
  if (artefacts.length < 2) {
    return '<p class="notice">Create at least two artefacts before adding a relationship.</p>';
  }
  const options = artefacts
    .map(
      (artefact) =>
        `<option value="${escapeHtml(artefact.artefact_id)}">${escapeHtml(
          artefact.title,
        )} (${escapeHtml(splitName(artefact.artefact_type))})</option>`,
    )
    .join("");
  return `<form id="relationship-form" class="form-grid">
    <label class="field-required">Source<select name="source_artefact_id" required>
      <option value="">Select source...</option>${options}</select></label>
    <label class="field-required">Target<select name="target_artefact_id" required>
      <option value="">Select target...</option>${options}</select></label>
    <label class="field-required">Relationship type
      <input name="relationship_type" required placeholder="satisfies">
    </label>
    <label>Rationale
      <input name="rationale" placeholder="Why these records are connected">
    </label>
    <div class="full"><button class="button primary" type="submit">Create relationship</button></div>
  </form>`;
}

function renderRelationshipTable(relationships, artefacts) {
  const titles = Object.fromEntries(artefacts.map((item) => [item.artefact_id, item.title]));
  const rows = relationships.map((relationship) => [
    escapeHtml(titles[relationship.source_artefact_id] || relationship.source_artefact_id),
    escapeHtml(relationship.relationship_type),
    escapeHtml(titles[relationship.target_artefact_id] || relationship.target_artefact_id),
    `<div class="row-actions">
      ${
        relationship.allowed_actions?.includes("edit")
          ? actionButton("edit-relationship", "Edit", { id: relationship.relationship_id })
          : ""
      }
      ${
        relationship.allowed_actions?.includes("delete")
          ? actionButton("delete-relationship", "Delete", {
              id: relationship.relationship_id,
              variant: "danger",
            })
          : ""
      }
    </div>`,
  ]);
  return table(["Source", "Relationship", "Target", "Actions"], rows, {
    emptyTitle: "No relationships",
    emptyDetail: "Add an explicit link between two artefacts.",
  });
}

function bindCreateForm(ctx) {
  const form = document.querySelector("#create-artefact-form");
  document.querySelector("#generate-source-id").addEventListener("click", () => {
    const type = form.elements.artefact_type.value || "EVIDENCE";
    form.elements.source_object_id.value = `${type.toUpperCase()}-${crypto.randomUUID()
      .slice(0, 8)
      .toUpperCase()}`;
  });
  document.querySelector("#artefact-type").addEventListener("change", async (event) => {
    const container = document.querySelector("#schema-fields");
    currentSchema = null;
    container.innerHTML = event.target.value ? "Loading canonical fields..." : "";
    if (!event.target.value) {
      return;
    }
    try {
      const response = await ctx.api.schema(ctx.state.projectId, event.target.value);
      currentSchema = response.data;
      container.innerHTML = renderSchemaFields(currentSchema);
    } catch (error) {
      container.innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`;
    }
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      let payload = currentSchema ? readSchemaPayload(form, currentSchema) : {};
      const raw = document.querySelector("#advanced-payload").value.trim();
      if (raw) {
        payload = readJson(raw, "Payload JSON");
      }
      await runAction(
        button,
        () =>
          ctx.api.createArtefact(ctx.state.projectId, {
            artefact_type: form.elements.artefact_type.value,
            title: form.elements.title.value.trim(),
            description: form.elements.description.value.trim(),
            source: {
              source_kind: "api",
              source_object_id: form.elements.source_object_id.value.trim(),
              source_document: form.elements.source_document.value.trim() || "manual-entry",
            },
            payload,
          }),
        "Artefact created.",
      );
      currentSchema = null;
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function bindCatalogue(ctx, artefacts) {
  document.querySelector("#artefact-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action=open-artefact]");
    if (!button) {
      return;
    }
    selectedArtefactId = button.dataset.id;
    await renderArtefactDetail(ctx, selectedArtefactId, { reveal: true });
  });
  document.querySelector("#artefact-filter").addEventListener("input", (event) => {
    const query = event.target.value.toLowerCase();
    const filtered = artefacts.filter((artefact) =>
      [artefact.title, artefact.artefact_type, artefact.status, artefact.artefact_id]
        .join(" ")
        .toLowerCase()
        .includes(query),
    );
    document.querySelector("#artefact-table").innerHTML = renderArtefactTable(filtered);
  });
}

function bindRelationshipForm(ctx) {
  const form = document.querySelector("#relationship-form");
  if (!form) {
    return;
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const button = form.querySelector("button[type=submit]");
    try {
      await runAction(
        button,
        () =>
          ctx.api.createRelationship(ctx.state.projectId, {
            source_artefact_id: form.elements.source_artefact_id.value,
            target_artefact_id: form.elements.target_artefact_id.value,
            relationship_type: form.elements.relationship_type.value.trim(),
            payload: form.elements.rationale.value.trim()
              ? { rationale: form.elements.rationale.value.trim() }
              : {},
          }),
        "Relationship created.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

function bindRelationshipTable(ctx, relationships) {
  document.querySelector("#relationship-table").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const relationship = relationships.find(
      (item) => item.relationship_id === button.dataset.id,
    );
    if (!relationship) {
      return;
    }
    try {
      if (button.dataset.action === "delete-relationship") {
        if (!requireConfirmation("Delete this relationship and create an obsolete revision?")) {
          return;
        }
        await runAction(
          button,
          () =>
            ctx.api.deleteRelationship(ctx.state.projectId, relationship.relationship_id, {
              base_revision_id: relationship.current_revision_id,
            }),
          "Relationship deleted.",
        );
      } else if (button.dataset.action === "edit-relationship") {
        const nextType = window.prompt("Relationship type", relationship.relationship_type);
        if (!nextType) {
          return;
        }
        await runAction(
          button,
          () =>
            ctx.api.updateRelationship(ctx.state.projectId, relationship.relationship_id, {
              relationship_type: nextType.trim(),
              payload: relationship.payload_json || {},
              base_revision_id: relationship.current_revision_id,
            }),
          "Relationship revised.",
        );
      }
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
}

async function renderArtefactDetail(ctx, artefactId, { reveal = false } = {}) {
  const container = document.querySelector("#artefact-detail");
  container.innerHTML = "Loading artefact details...";
  try {
    const artefactResponse = await ctx.api.artefact(ctx.state.projectId, artefactId);
    const artefact = artefactResponse.data;
    const schemaResponse = await ctx.api.schema(ctx.state.projectId, artefact.artefact_type);
    const schema = schemaResponse.data;
    container.innerHTML = `
      <div class="card-header">
        <div><p class="eyebrow">${escapeHtml(splitName(artefact.artefact_type))}</p>
        <h2>${escapeHtml(artefact.title)}</h2></div>
        ${statusBadge(artefact.status)}
      </div>
      <form id="edit-artefact-form" class="stack">
        <label class="field-required">Title<input name="title" value="${escapeHtml(
          artefact.title,
        )}" required></label>
        <label>Description<textarea name="description" rows="3">${escapeHtml(
          artefact.description || "",
        )}</textarea></label>
        <div class="form-grid">${renderSchemaFields(schema, artefact.payload_json || {})}</div>
        <label>Change reason<input name="change_reason" value="web revision"></label>
        ${
          artefact.allowed_actions?.includes("edit")
            ? '<button class="button primary" type="submit">Save revision</button>'
            : '<p class="notice">You cannot revise this artefact in its current state.</p>'
        }
      </form>
      <div class="cluster" id="lifecycle-actions" style="margin-top: 1rem">
        ${renderLifecycleActions(artefact)}
      </div>
      <details class="advanced">
        <summary>Revision history and technical details</summary>
        <button class="button secondary" type="button" data-action="load-revisions">Load revisions</button>
        <div id="revision-history"></div>
        ${jsonView(artefact)}
      </details>
    `;
    bindArtefactDetail(ctx, artefact, schema);
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

function renderLifecycleActions(artefact) {
  const labels = {
    submit_for_review: "Submit for review",
    mark_reviewed: "Mark reviewed",
    reject: "Return to draft",
    approve: "Approve",
    release: "Release",
    delete: "Delete",
  };
  return (artefact.allowed_actions || [])
    .filter((action) => action !== "edit")
    .map((action) =>
      actionButton(`artefact-${action}`, labels[action] || action, {
        id: artefact.artefact_id,
        variant: action === "delete" ? "danger" : "secondary",
      }),
    )
    .join("");
}

function bindArtefactDetail(ctx, artefact, schema) {
  const form = document.querySelector("#edit-artefact-form");
  if (artefact.allowed_actions?.includes("edit")) {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("button[type=submit]");
      try {
        await runAction(
          button,
          () =>
            ctx.api.updateArtefact(ctx.state.projectId, artefact.artefact_id, {
              title: form.elements.title.value.trim(),
              description: form.elements.description.value.trim(),
              payload: readSchemaPayload(form, schema),
              base_revision_id: artefact.current_revision_id,
              change_reason: form.elements.change_reason.value.trim() || "web revision",
            }),
          "Artefact revision saved.",
        );
        await ctx.refreshWorkspace();
        await ctx.refresh();
      } catch (error) {
        ctx.notify(error.message, "error");
      }
    });
  }
  document.querySelector("#lifecycle-actions").addEventListener("click", async (event) => {
    const button = event.target.closest("[data-action]");
    if (!button) {
      return;
    }
    const action = button.dataset.action.replace("artefact-", "");
    if (
      ["delete", "release"].includes(action) &&
      !requireConfirmation(`${action === "delete" ? "Delete" : "Release"} this artefact?`)
    ) {
      return;
    }
    const endpointActions = {
      submit_for_review: "submit-for-review",
      mark_reviewed: "mark-reviewed",
      reject: "reject",
      approve: "approve",
      release: "release",
    };
    try {
      await runAction(
        button,
        () =>
          action === "delete"
            ? ctx.api.deleteArtefact(ctx.state.projectId, artefact.artefact_id, {
                base_revision_id: artefact.current_revision_id,
              })
            : ctx.api.artefactAction(
                ctx.state.projectId,
                artefact.artefact_id,
                endpointActions[action],
                { base_revision_id: artefact.current_revision_id },
              ),
        "Artefact lifecycle updated.",
      );
      await ctx.refreshWorkspace();
      await ctx.refresh();
    } catch (error) {
      ctx.notify(error.message, "error");
    }
  });
  document.querySelector("[data-action=load-revisions]").addEventListener("click", async () => {
    const target = document.querySelector("#revision-history");
    target.innerHTML = "Loading revisions...";
    try {
      const response = await ctx.api.artefactRevisions(
        ctx.state.projectId,
        artefact.artefact_id,
      );
      target.innerHTML = table(
        ["Revision", "Changed", "Fingerprint"],
        response.data.map((revision) => [
          escapeHtml(revision.revision_number),
          escapeHtml(revision.changed_at || ""),
          escapeHtml(revision.content_fingerprint || ""),
        ]),
        { emptyTitle: "No revisions found" },
      );
    } catch (error) {
      target.innerHTML = `<p class="form-error">${escapeHtml(error.message)}</p>`;
    }
  });
}

function splitName(value) {
  return String(value || "").replace(/([a-z0-9])([A-Z])/g, "$1 $2");
}
