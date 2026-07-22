import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("import diagnostics and pending decisions are actionable", async ({ page }) => {
  const mock = await installMockApi(page);
  await signIn(page);
  await page.getByRole("link", { name: /^Imports/ }).click();
  await page.getByRole("button", { name: "Open" }).click();

  await expect(page.getByRole("cell", { name: "Revision conflict", exact: true })).toBeVisible();
  await page.getByLabel(/SWR-001/).selectOption("accept_new_revision");
  await page.getByRole("button", { name: "Submit decisions" }).click();
  await expect(page.getByText("Import decisions submitted.")).toBeVisible();
  expect(
    mock.requests.some(
      (request) =>
        request.method === "POST" &&
        request.path === "/projects/PROJ_1/imports/IMP_1/decisions" &&
        request.body.decisions[0].decision === "accept_new_revision",
    ),
  ).toBeTruthy();
});
