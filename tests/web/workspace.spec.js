import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("role-aware workspace loads actionable work without manual load controls", async ({ page }) => {
  await installMockApi(page);
  await signIn(page);

  await expect(page.locator("#login-view")).toBeHidden();
  await expect(page.locator("#app-view")).toBeVisible();
  expect(await page.locator("#app-view").evaluate((element) => element.getBoundingClientRect().top)).toBe(0);
  await expect(page.getByRole("heading", { name: "My work" })).toBeVisible();
  await expect(page.getByText("Import decisions", { exact: true })).toBeVisible();
  await expect(page.getByText("Release-blocking validation issues", { exact: true })).toBeVisible();
  await expect(page.getByText("blocked", { exact: true }).first()).toBeVisible();
  await expect(page.getByRole("link", { name: "Artefacts & Relationships" })).toBeVisible();
});
