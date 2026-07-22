import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("ordinary user sees server-allowed actions but no administrative controls", async ({ page }) => {
  await installMockApi(page, { role: "user" });
  await signIn(page);

  await page.getByRole("link", { name: "Release", exact: true }).click();
  await expect(page.getByRole("button", { name: "Create snapshot" })).toHaveCount(0);
  await page.getByRole("link", { name: "Administration" }).click();
  await expect(page.getByText("Add GitHub connector")).toHaveCount(0);
  await expect(page.getByRole("button", { name: "Save project defaults" })).toHaveCount(0);
});
