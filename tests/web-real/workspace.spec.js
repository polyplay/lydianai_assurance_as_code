import { expect, test } from "@playwright/test";

test("admin can bootstrap a project, create evidence, and run queued validation", async ({
  page,
}) => {
  await page.goto("./");

  await page.getByLabel("Username").fill("webadmin");
  await page.getByLabel("Password", { exact: true }).fill("WebIntegration-123!");
  await page.getByRole("button", { name: "Sign in" }).click();

  await expect(
    page.getByRole("heading", { name: "Create the first project" }),
  ).toBeVisible();
  await page.getByLabel("Project key").fill("WEBTEST");
  await page.getByLabel("Name", { exact: true }).fill("Web Integration Project");
  await page.getByLabel("Description").fill("Fresh project created by Playwright.");
  await page.getByRole("button", { name: "Create project" }).click();

  await expect(
    page.getByRole("heading", { name: "Welcome, Web Integration Admin" }),
  ).toBeVisible();
  await expect(page.getByLabel("Selected project")).toContainText(
    "WEBTEST · Web Integration Project",
  );

  await page.getByRole("link", { name: "Artefacts & Relationships" }).click();
  await expect(page.getByRole("heading", { name: "Create artefact" })).toBeVisible();
  await page.getByLabel("Artefact type").selectOption("SoftwareRequirement");
  await page.getByLabel("Title", { exact: true }).fill("Web-created requirement");
  await page.getByLabel("Source object ID").fill("SWR-WEB-001");
  await page
    .getByLabel("Statement")
    .fill("The software shall expose a usable assurance workspace.");
  await page.getByLabel("Verification intent").fill("Browser integration test");
  await page.getByRole("button", { name: "Create artefact" }).click();

  await expect(page.getByText("Artefact created.")).toBeVisible();
  await expect(page.getByText("Web-created requirement", { exact: true })).toBeVisible();

  await page.getByRole("link", { name: "Validation" }).click();
  await page.getByRole("button", { name: "Run validation" }).click();
  await expect(page.getByText("Validation started.")).toBeVisible();

  await page.getByRole("link", { name: "Jobs" }).click();
  await page.getByLabel("Filter").selectOption("all");
  await expect(page.getByText("validation run", { exact: true })).toBeVisible();
});
