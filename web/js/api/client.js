export class ApiError extends Error {
  constructor(message, options = {}) {
    super(message);
    this.name = "ApiError";
    this.status = options.status || 0;
    this.code = options.code || "";
    this.requestId = options.requestId || "";
    this.correlationId = options.correlationId || "";
    this.details = options.details;
  }
}

export class ApiClient {
  constructor({ baseUrl, tokenProvider, onUnauthorized }) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
    this.tokenProvider = tokenProvider;
    this.onUnauthorized = onUnauthorized;
  }

  setBaseUrl(baseUrl) {
    this.baseUrl = normalizeBaseUrl(baseUrl);
  }

  async get(path, options = {}) {
    return this.request("GET", path, undefined, options);
  }

  async post(path, body, options = {}) {
    return this.request("POST", path, body, options);
  }

  async put(path, body, options = {}) {
    return this.request("PUT", path, body, options);
  }

  async delete(path, body, options = {}) {
    return this.request("DELETE", path, body, options);
  }

  async request(method, path, body, options = {}) {
    const headers = new Headers(options.headers || {});
    const token = this.tokenProvider();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
    let payload = body;
    if (body !== undefined && !(body instanceof FormData)) {
      headers.set("Content-Type", "application/json");
      payload = JSON.stringify(body);
    }
    const response = await fetch(`${this.baseUrl}${path}`, {
      method,
      headers,
      body: payload,
      signal: options.signal,
    });
    const responseBody = await parseBody(response);
    const requestId = responseBody?.request_id || response.headers.get("X-Request-ID") || "";
    const correlationId =
      responseBody?.correlation_id || response.headers.get("X-Correlation-ID") || "";
    if (!response.ok) {
      if (response.status === 401 && !options.suppressUnauthorizedCallback) {
        this.onUnauthorized?.();
      }
      const detail =
        responseBody?.error ?? responseBody?.detail ?? responseBody?.data ?? responseBody;
      throw new ApiError(errorMessage(response.status, detail), {
        status: response.status,
        code: responseBody?.error?.code || "",
        requestId,
        correlationId,
        details: detail,
      });
    }
    if (responseBody && Object.hasOwn(responseBody, "data")) {
      return {
        data: responseBody.data,
        status: responseBody.status || "success",
        messages: responseBody.messages || [],
        requestId,
        correlationId,
      };
    }
    return {
      data: responseBody,
      status: "success",
      messages: [],
      requestId,
      correlationId,
    };
  }
}

export function defaultApiBaseUrl() {
  return `${window.location.origin}/api/v1`;
}

function normalizeBaseUrl(value) {
  return String(value || defaultApiBaseUrl()).replace(/\/+$/, "");
}

async function parseBody(response) {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return { detail: text };
  }
}

function errorMessage(status, detail) {
  if (
    status === 401 &&
    (detail === "Invalid username or password" ||
      detail?.message === "Invalid username or password")
  ) {
    return "Invalid username or password.";
  }
  const prefixes = {
    401: "Your session has expired. Sign in again.",
    403: "You do not have permission to perform this action.",
    404: "The requested resource was not found.",
    409: "The action conflicts with the current resource state.",
    423: "The project is temporarily locked by another controlled operation.",
    422: "Some submitted fields are invalid.",
  };
  const detailText =
    typeof detail === "string"
      ? detail
      : detail?.message || detail?.detail || formatValidationDetail(detail);
  return detailText ? `${prefixes[status] || "The request failed"} ${detailText}` : prefixes[status] || `Request failed with HTTP ${status}.`;
}

function formatValidationDetail(detail) {
  if (!Array.isArray(detail)) {
    return "";
  }
  return detail
    .map((item) => {
      const location = Array.isArray(item.loc) ? item.loc.join(".") : "field";
      return `${location}: ${item.msg || "invalid value"}`;
    })
    .join("; ");
}
