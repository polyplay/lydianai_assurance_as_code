export function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

export function statusBadge(value) {
  const text = String(value || "unknown");
  const normalized = text.toLowerCase().replaceAll(" ", "_");
  return `<span class="status ${escapeHtml(normalized)}">${escapeHtml(
    text.replaceAll("_", " "),
  )}</span>`;
}

export function metric(value, label) {
  return `<div class="card metric"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(
    label,
  )}</span></div>`;
}

export function emptyState(title, detail = "") {
  return `<div class="empty"><strong>${escapeHtml(title)}</strong>${
    detail ? `<p>${escapeHtml(detail)}</p>` : ""
  }</div>`;
}

export function jsonView(value) {
  return `<pre class="json-view">${escapeHtml(JSON.stringify(value, null, 2))}</pre>`;
}

export function table(headers, rows, options = {}) {
  if (!rows.length) {
    return emptyState(options.emptyTitle || "Nothing to show", options.emptyDetail || "");
  }
  const head = headers.map((header) => `<th scope="col">${escapeHtml(header)}</th>`).join("");
  const body = rows
    .map(
      (row) =>
        `<tr>${row.map((cell) => `<td>${cell === null || cell === undefined ? "" : cell}</td>`).join("")}</tr>`,
    )
    .join("");
  return `<div class="table-wrap"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
}

export function actionButton(action, label, options = {}) {
  const variant = options.variant || "secondary";
  return `<button type="button" class="button ${escapeHtml(variant)}"
    data-action="${escapeHtml(action)}"
    ${options.id ? `data-id="${escapeHtml(options.id)}"` : ""}
    ${options.disabled ? "disabled" : ""}>${escapeHtml(label)}</button>`;
}

export function formatError(error) {
  const details = [];
  if (error.requestId) {
    details.push(`<dt>Request ID</dt><dd>${escapeHtml(error.requestId)}</dd>`);
  }
  if (error.correlationId) {
    details.push(`<dt>Correlation ID</dt><dd>${escapeHtml(error.correlationId)}</dd>`);
  }
  return `<div class="notice danger" role="alert"><strong>${escapeHtml(
    error.message || "The operation failed.",
  )}</strong>${
    details.length
      ? `<details class="advanced"><summary>Technical details</summary><dl class="details-list">${details.join(
          "",
        )}</dl></details>`
      : ""
  }</div>`;
}

export function setPage({ eyebrow, title, description, actions = "" }) {
  document.querySelector("#page-eyebrow").textContent = eyebrow || "";
  document.querySelector("#page-title").textContent = title || "";
  document.querySelector("#page-description").textContent = description || "";
  document.querySelector("#page-actions").innerHTML = actions;
  document.title = `${title || "Workspace"} | LydianAI`;
}

export function setRouteStatus(message) {
  document.querySelector("#route-status").textContent = message || "";
}

export function toast(message, type = "info") {
  const region = document.querySelector("#toast-region");
  const item = document.createElement("div");
  item.className = `toast ${type}`;
  item.textContent = message;
  region.append(item);
  window.setTimeout(() => item.remove(), 5000);
}

export async function runAction(button, operation, successMessage) {
  const original = button?.textContent;
  if (button) {
    button.disabled = true;
    button.textContent = "Working...";
  }
  try {
    const result = await operation();
    if (successMessage) {
      toast(successMessage, "success");
    }
    return result;
  } finally {
    if (button) {
      button.disabled = false;
      button.textContent = original;
    }
  }
}

export function requireConfirmation(message) {
  return window.confirm(message);
}

export function readJson(text, label = "JSON") {
  try {
    const value = JSON.parse(text);
    if (value === null || typeof value !== "object") {
      throw new Error(`${label} must contain an object or array.`);
    }
    return value;
  } catch (error) {
    throw new Error(`${label} is invalid: ${error.message}`);
  }
}
