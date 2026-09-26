import { defineConfig, devices } from "@playwright/test";

/**
 * Used by `npm run shots` only: builds the app, serves it with `vite preview` on mock data
 * and saves screenshots to ../docs/screens/. Not part of `npm test`.
 *
 * Browser: Playwright's own Chromium (`npx playwright install chromium`). Where that download
 * is blocked, set SHOTS_BROWSER_CHANNEL=chrome to use the installed Google Chrome instead.
 */
const channel = process.env.SHOTS_BROWSER_CHANNEL || undefined;

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  fullyParallel: true,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:4173",
    colorScheme: "light",
    channel,
  },
  webServer: {
    command: "npm run build && npx vite preview --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: false,
    timeout: 120_000,
    env: { VITE_REAL_ENDPOINTS: "", VITE_SNAPSHOT: "" },
  },
});
