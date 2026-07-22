import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("phone layout preserves overview and navigation access", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installMockApi(page);
  await signIn(page);

  await expect(page.getByRole("heading", { name: /Welcome/ })).toBeVisible();
  await page.getByRole("button", { name: "Open navigation" }).click();
  const validationLink = page.locator('.nav-link[data-route="validation"]');
  await expect(validationLink).toBeVisible();
  await validationLink.click();
  await expect(page.getByRole("heading", { name: "Validation", exact: true })).toBeVisible();
});
