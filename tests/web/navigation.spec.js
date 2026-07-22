import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";

const routes = [
  ["jobs", "Background jobs"],
  ["evidence", "Artefacts and relationships"],
  ["imports", "Sphinx-Needs imports"],
  ["trace", "Traceability"],
  ["validation", "Validation"],
  ["impact", "Impact and suspect states"],
  ["release", "Release workspace"],
  ["administration", "Project administration"],
  ["overview", /Welcome, Alex Engineer/],
  ["work", /Welcome, Alex Engineer/],
];

test("every primary navigation route opens at the top of its page", async ({ page }) => {
  await installMockApi(page);
  await signIn(page);

  for (const [route, heading] of routes) {
    await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
    await page.locator(`.nav-link[data-route="${route}"]`).click();
    await expect(page.getByRole("heading", { name: heading, exact: typeof heading === "string" })).toBeVisible();
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

    const titleTop = await page.locator("#page-title").evaluate(
      (element) => element.getBoundingClientRect().top,
    );
    expect(titleTop).toBeGreaterThanOrEqual(0);
    expect(titleTop).toBeLessThan(240);
  }
});

test("selected records open beside their lists before secondary creation workflows", async ({
  page,
}) => {
  await installMockApi(page);
  await signIn(page);

  await page.locator('.nav-link[data-route="evidence"]').click();
  await page.locator("#evidence-catalogue").getByRole("button", { name: "Open" }).first().click();
  await expect(page.locator("#artefact-detail").getByRole("heading", { level: 2 })).toBeVisible();
  await expectAlignedBefore(page, "#evidence-catalogue", "#artefact-detail", "#create-artefact-panel");

  await page.locator('.nav-link[data-route="imports"]').click();
  await page.locator("#import-history").getByRole("button", { name: "Open" }).click();
  await expect(page.locator("#import-detail").getByRole("heading", { name: "Import details" })).toBeVisible();
  await expectAlignedBefore(page, "#import-history", "#import-detail", "#start-import-panel");

  await page.locator('.nav-link[data-route="release"]').click();
  await page.locator("#baseline-list").getByRole("button", { name: "Open" }).first().click();
  await expect(page.locator("#baseline-detail").getByRole("heading", { level: 2 })).toBeVisible();
  await expectAlignedBefore(page, "#baseline-list", "#baseline-detail", "#create-baseline-panel");
});

async function expectAlignedBefore(page, listSelector, detailSelector, secondarySelector) {
  const positions = await page.evaluate(
    ([list, detail, secondary]) => ({
      listTop: document.querySelector(list).getBoundingClientRect().top,
      detailTop: document.querySelector(detail).getBoundingClientRect().top,
      secondaryTop: document.querySelector(secondary).getBoundingClientRect().top,
    }),
    [listSelector, detailSelector, secondarySelector],
  );

  expect(Math.abs(positions.listTop - positions.detailTop)).toBeLessThanOrEqual(2);
  expect(positions.secondaryTop).toBeGreaterThan(positions.detailTop);
}
