import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("active jobs expose progress, detail, and server-authorized cancellation", async ({ page }) => {
  const mock = await installMockApi(page);
  await signIn(page);
  await page.getByRole("link", { name: /^Jobs/ }).click();

  await expect(page.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "45");
  await page.getByRole("button", { name: "View", exact: true }).click();
  await expect(page.getByText("Job detail")).toBeVisible();
  page.on("dialog", (dialog) => dialog.accept());
  await page.getByRole("button", { name: "Cancel" }).click();
  await expect(page.getByText("Job cancellation requested.")).toBeVisible();
  expect(
    mock.requests.some(
      (request) => request.method === "POST" && request.path === "/jobs/JOB_1/cancel",
    ),
  ).toBeTruthy();
});
