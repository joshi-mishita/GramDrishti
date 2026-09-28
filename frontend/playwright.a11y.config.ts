import { defineConfig, devices } from "@playwright/test";

/**
 * `npm run a11y`: a keyboard-only walkthrough, and axe-core on every screen in English, Hindi and Punjabi at 1366 px and 360 px,
 * on the demo files (no API needed). Fails on any serious or critical violation and writes
 * every finding, whatever its impact, to test-results/a11y/axe-summary.json.
 */
const channel = process.env.SHOTS_BROWSER_CHANNEL || undefined;

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["a11y.spec.ts", "keyboard.spec.ts"],
  outputDir: "./test-results/a11y",
  fullyParallel: true,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:4176",
    colorScheme: "light",
    channel,
  },
  webServer: {
    command: "npm run build && npx vite preview --port 4176 --strictPort",
    url: "http://localhost:4176",
    reuseExistingServer: false,
    timeout: 180_000,
    env: { VITE_REAL_ENDPOINTS: "", VITE_SNAPSHOT: "" },
  },
});
