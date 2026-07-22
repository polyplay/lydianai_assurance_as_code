import assert from "node:assert/strict";
import test from "node:test";

import { ApiClient, ApiError } from "../../web/js/api/client.js";
import { createResources } from "../../web/js/api/resources.js";
import { renderSchemaFields } from "../../web/js/components/schema-form.js";


test("API client unwraps the standard envelope and sends the bearer token", async () => {
  let captured;
  globalThis.fetch = async (url, options) => {
    captured = { url, options };
    return new Response(
      JSON.stringify({
        status: "success",
        request_id: "REQ_1",
        correlation_id: "CORR_1",
        data: { ok: true },
      }),
      { status: 200, headers: { "Content-Type": "application/json" } },
    );
  };
  const client = new ApiClient({
    baseUrl: "https://example.test/api/v1/",
    tokenProvider: () => "token",
  });

  const result = await client.get("/projects");

  assert.deepEqual(result.data, { ok: true });
  assert.equal(captured.url, "https://example.test/api/v1/projects");
  assert.equal(captured.options.headers.get("Authorization"), "Bearer token");
});


test("API client preserves conflict identifiers and actionable detail", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        request_id: "REQ_409",
        correlation_id: "CORR_409",
        detail: "Stale artefact revision",
      }),
      { status: 409, headers: { "Content-Type": "application/json" } },
    );
  const client = new ApiClient({
    baseUrl: "https://example.test/api/v1",
    tokenProvider: () => "token",
  });

  await assert.rejects(
    () => client.put("/artefacts/ART_1", {}),
    (error) =>
      error instanceof ApiError &&
      error.status === 409 &&
      error.requestId === "REQ_409" &&
      error.message.includes("Stale artefact revision"),
  );
});

test("login failures report invalid credentials without expiring the session", async () => {
  let unauthorizedCalls = 0;
  globalThis.fetch = async () =>
    new Response(JSON.stringify({ detail: "Invalid username or password" }), {
      status: 401,
      headers: { "Content-Type": "application/json" },
    });
  const client = new ApiClient({
    baseUrl: "https://example.test/api/v1",
    tokenProvider: () => "",
    onUnauthorized: () => {
      unauthorizedCalls += 1;
    },
  });

  await assert.rejects(
    () =>
      client.post(
        "/auth/login",
        { username: "demo", password: "wrong" },
        { suppressUnauthorizedCallback: true },
      ),
    (error) =>
      error instanceof ApiError &&
      error.status === 401 &&
      error.message === "Invalid username or password.",
  );
  assert.equal(unauthorizedCalls, 0);
});

test("standard error envelopes preserve error codes and login detail", async () => {
  globalThis.fetch = async () =>
    new Response(
      JSON.stringify({
        status: "error",
        request_id: "REQ_LOGIN",
        correlation_id: "CORR_LOGIN",
        error: {
          code: "authentication_required",
          message: "Invalid username or password",
          details: null,
        },
      }),
      { status: 401, headers: { "Content-Type": "application/json" } },
    );
  const client = new ApiClient({
    baseUrl: "https://example.test/api/v1",
    tokenProvider: () => "",
  });

  await assert.rejects(
    () => client.post("/auth/login", { username: "demo", password: "wrong" }),
    (error) =>
      error instanceof ApiError &&
      error.code === "authentication_required" &&
      error.message === "Invalid username or password.",
  );
});


test("resource client builds project-scoped paths centrally", async () => {
  const calls = [];
  const fakeClient = {
    get: async (...args) => calls.push(["get", ...args]),
    post: async (...args) => calls.push(["post", ...args]),
    put: async (...args) => calls.push(["put", ...args]),
    delete: async (...args) => calls.push(["delete", ...args]),
  };
  const resources = createResources(fakeClient);

  await resources.runReleaseGate("PROJ 1", "BASE/1");
  await resources.publishRepositoryApproval("PROJ 1", "BASE/1", null);

  assert.deepEqual(calls[0], [
    "post",
    "/projects/PROJ%201/release-gate/run",
    { baseline_id: "BASE/1" },
  ]);
  assert.equal(
    calls[1][1],
    "/projects/PROJ%201/baselines/BASE%2F1/repository-approvals",
  );
});


test("schema renderer uses canonical widget and required metadata", () => {
  const html = renderSchemaFields({
    fields: [
      {
        name: "statement",
        label: "Statement",
        data_type: "string",
        widget: "textarea",
        required: true,
        readonly: false,
        help: "Enter statement.",
      },
    ],
  });

  assert.match(html, /textarea/);
  assert.match(html, /required/);
  assert.match(html, /payload\.statement/);
});
