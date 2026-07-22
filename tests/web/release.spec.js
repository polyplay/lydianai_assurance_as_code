import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("baseline approval and repository publication remain separate controlled actions", async ({ page }) => {
  const mock = await installMockApi(page);
  await signIn(page);
  await page.getByRole("link", { name: "Release", exact: true }).click();

  const candidateRow = page.getByRole("row").filter({ hasText: "Release candidate 1" });
  await candidateRow.getByRole("button", { name: "Open" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Approve baseline" }).click();
  await expect(page.getByText("Baseline approved.")).toBeVisible();

  const releasedRow = page.getByRole("row").filter({ hasText: "Released baseline" });
  await releasedRow.getByRole("button", { name: "Open" }).click();
  page.once("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Publish repository approval" }).click();
  await expect(page.getByText("Repository approval published.")).toBeVisible();

  expect(
    mock.requests.some(
      (request) =>
        request.method === "POST" &&
        request.path === "/projects/PROJ_1/baselines/BASE_1/approve",
    ),
  ).toBeTruthy();
  expect(
    mock.requests.some(
      (request) =>
        request.method === "POST" &&
        request.path === "/projects/PROJ_1/baselines/BASE_2/repository-approvals",
    ),
  ).toBeTruthy();
});
