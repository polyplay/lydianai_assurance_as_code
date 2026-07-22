import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("overview and guided evidence workflow have no detectable WCAG A/AA violations", async ({ page }) => {
  await installMockApi(page);
  await signIn(page);

  let results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations).toEqual([]);

  await page.getByRole("link", { name: "Artefacts & Relationships" }).click();
  results = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  expect(results.violations).toEqual([]);
});
