import { expect, test } from "@playwright/test";

// Requires the FastAPI backend on :8000 — the demo page runs a live synthetic
// scan against it on mount. See playwright.config.ts for setup instructions.
test("demo runs a synthetic scan and surfaces zombie candidates", async ({ page }) => {
  await page.goto("/demo");

  // The synthetic scan is asynchronous; wait for the results summary headline.
  await expect(page.getByRole("heading", { name: /look abandoned/i })).toBeVisible({
    timeout: 30_000,
  });

  // The findings table renders.
  await expect(page.getByRole("table")).toBeVisible();

  // The default filter is "zombies", so every visible row is a zombie candidate.
  const zombieRows = page.getByRole("button", { name: /view details for/i });
  await expect(zombieRows.first()).toBeVisible();
  expect(await zombieRows.count()).toBeGreaterThan(0);
});
