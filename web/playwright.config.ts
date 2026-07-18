/**
 * Playwright e2e configuration for the GraveKeeper web app.
 *
 * IMPORTANT — these e2e tests require the FastAPI BACKEND running on :8000.
 * The /demo and /scan flows call the scanner API (runScan / getScan / listRegistry).
 * With no backend up, the demo shows the "scanner is asleep" error state and the
 * table assertions in e2e/demo.spec.ts will fail.
 *
 * To run the suite locally:
 *   1. Start the backend (from the repo's `scanner/` folder):
 *        uvicorn gravekeeper.main:app --reload --port 8000
 *   2. Run the e2e tests (the Next.js dev server is started automatically by the
 *      `webServer` block below, or reused if one is already listening on :3000):
 *        npm run e2e
 *
 * The frontend talks to the backend via NEXT_PUBLIC_API_BASE_URL (defaults to
 * http://localhost:8000). Override it if your backend runs elsewhere.
 */
import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  reporter: "list",
  use: {
    baseURL: "http://localhost:3000",
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  webServer: {
    command: "npm run dev",
    url: "http://localhost:3000",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
