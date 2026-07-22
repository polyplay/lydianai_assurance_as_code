import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("conflict response is shown as an actionable error without a local workaround", async ({ page }) => {
  await installMockApi(page, { createArtefactError: true });
  await signIn(page);
  await page.getByRole("link", { name: "Artefacts & Relationships" }).click();
  await page.getByLabel("Artefact type").selectOption("SoftwareRequirement");
  await page.getByLabel("Title").fill("Duplicate");
  await page.getByLabel("Source object ID").fill("SWR-001");
  await page.getByLabel("Statement").fill("Duplicate statement.");
  await page.getByLabel("Verification Intent").fill("Test.");
  await page.getByRole("button", { name: "Create artefact" }).click();

  await expect(page.getByText(/source identity already exists/)).toBeVisible();
});
