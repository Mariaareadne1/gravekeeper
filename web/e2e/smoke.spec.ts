import { expect, test } from "@playwright/test";

// Requires the FastAPI backend on :8000 for the /registry read.
// See playwright.config.ts for setup instructions.

test("landing page loads with the hero heading", async ({ page }) => {
  await page.goto("/");
  await expect(
    page.getByRole("heading", { name: /the agents nobody turned off are still running/i })
  ).toBeVisible();
});

test("scan page shows all four connector tabs", async ({ page }) => {
  await page.goto("/scan");
  for (const connector of ["AWS", "GitHub", "GCP", "Azure"]) {
    await expect(page.getByRole("button", { name: connector, exact: true })).toBeVisible();
  }
});

test("registry page loads its heading", async ({ page }) => {
  await page.goto("/registry");
  // Backend up + empty registry shows "The registry is empty"; with entries it
  // shows "Lifecycle registry". Accept either durable heading.
  await expect(
    page.getByRole("heading", { name: /lifecycle registry|registry is empty/i })
  ).toBeVisible();
});

test("about and threat-model pages render", async ({ page }) => {
  await page.goto("/about");
  await expect(
    page.getByRole("heading", { name: /zombie agents, orphan ai agents, and agent sprawl/i })
  ).toBeVisible();

  await page.goto("/docs/threat-model");
  await expect(page.getByRole("heading", { name: /threat model/i })).toBeVisible();
});
