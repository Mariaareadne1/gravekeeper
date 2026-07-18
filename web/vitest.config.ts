import { resolve } from "node:path";
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Unit / component tests only. The Playwright e2e suite lives in `e2e/` and is
// explicitly excluded here so the two runners never try to execute each other's
// specs (Playwright's `test`/`expect` are incompatible with Vitest's).
export default defineConfig({
  plugins: [react()],
  resolve: {
    // Mirror the Next.js "@/*" path alias from tsconfig.json.
    alias: {
      "@": resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    include: ["**/*.{test,spec}.{ts,tsx}"],
    exclude: ["node_modules/**", ".next/**", "e2e/**"],
  },
});
