import { escapeHtml } from "./ui.js";

export function renderSchemaFields(schema, values = {}) {
  return (schema?.fields || [])
    .map((field) => renderField(field, values[field.name]))
    .join("");
}

export function readSchemaPayload(form, schema) {
  const payload = {};
  for (const field of schema?.fields || []) {
    const input = form.elements.namedItem(`payload.${field.name}`);
    if (!input || field.readonly) {
      continue;
    }
    const value = readFieldValue(input, field);
    if (value !== "" && value !== null && !(Array.isArray(value) && value.length === 0)) {
      payload[field.name] = value;
    }
  }
  return payload;
}

function renderField(field, value) {
  const id = `payload-${field.name.replaceAll(".", "-")}`;
  const requiredClass = field.required ? "field-required" : "";
  const required = field.required ? "required" : "";
  const readonly = field.readonly ? "disabled" : "";
  const helpId = `${id}-help`;
  const common = `id="${escapeHtml(id)}" name="payload.${escapeHtml(field.name)}"
    aria-describedby="${escapeHtml(helpId)}" ${required} ${readonly}`;
  let control;
  if (field.widget === "select") {
    const options = (field.allowed_values || [])
      .map(
        (option) =>
          `<option value="${escapeHtml(option)}" ${
            String(value ?? "") === option ? "selected" : ""
          }>${escapeHtml(option.replaceAll("_", " "))}</option>`,
      )
      .join("");
    control = `<select ${common}><option value="">Select...</option>${options}</select>`;
  } else if (field.widget === "checkbox") {
    control = `<label class="checkbox-label"><input ${common} type="checkbox" ${
      value ? "checked" : ""
    }> Yes</label>`;
  } else if (field.widget === "textarea" || field.widget === "tag_list") {
    const text = Array.isArray(value) ? value.join("\n") : value ?? "";
    control = `<textarea ${common} rows="${field.widget === "tag_list" ? "4" : "6"}">${escapeHtml(
      text,
    )}</textarea>`;
  } else {
    const type = field.widget === "number" ? "number" : "text";
    control = `<input ${common} type="${type}" value="${escapeHtml(value ?? "")}">`;
  }
  return `<label class="${requiredClass}" for="${escapeHtml(id)}">${escapeHtml(
    field.label,
  )}${control}<span id="${escapeHtml(helpId)}" class="help">${escapeHtml(
    field.help || "",
  )}</span></label>`;
}

function readFieldValue(input, field) {
  if (field.data_type === "boolean") {
    return input.checked;
  }
  if (field.data_type === "number") {
    return input.value === "" ? null : Number(input.value);
  }
  if (field.data_type === "array") {
    return input.value
      .split(/\n|,/)
      .map((item) => item.trim())
      .filter(Boolean);
  }
  return input.value.trim();
}
