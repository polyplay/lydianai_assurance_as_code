import { expect, test } from "@playwright/test";

import { installMockApi, signIn } from "./mock-api.js";


test("guided canonical form creates an artefact through the shared API", async ({ page }) => {
  const mock = await installMockApi(page);
  await signIn(page);
  await page.getByRole("link", { name: "Artefacts & Relationships" }).click();

  await page.getByLabel("Artefact type").selectOption("SoftwareRequirement");
  await page.getByLabel("Title").fill("Wheel speed requirement");
  await page.getByLabel("Source object ID").fill("SWR-002");
  await page.getByLabel("Statement").fill("The software shall monitor wheel speed.");
  await page.getByLabel("Verification Intent").fill("Automated integration test.");
  await page.getByRole("button", { name: "Create artefact" }).click();

  await expect(page.getByText("Artefact created.")).toBeVisible();
  expect(
    mock.requests.some(
      (request) =>
        request.method === "POST" &&
        request.path === "/projects/PROJ_1/artefacts" &&
        request.body.payload.statement.includes("wheel speed"),
    ),
  ).toBeTruthy();
});
