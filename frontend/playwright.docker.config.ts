import { defineConfig, devices } from "@playwright/test";

/**
 * `npm run e2e:docker`: the demo script (Backend Guide B7) against a running Docker stack.
 *
 * Starts no servers. `scripts/e2e_docker.sh` brings up an isolated compose project on ports
 * 18080 (web), 18081 (offline copy) and 18000 (API) with its own volumes, runs this suite and
 * removes the project, so approvals made here never reach the demo database. E2E_BASE_URL and
 * E2E_OFFLINE_URL point it elsewhere. Screens are saved to ../docs/screens/s14-*.png.
 */
const channel = process.env.SHOTS_BROWSER_CHANNEL || undefined;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "demo-*.spec.ts",
  outputDir: "./test-results/e2e-docker",
  // One worker, in file order: the steps share the stack's database like the live demo does.
  workers: 1,
  fullyParallel: false,
  retries: 0,
  reporter: [["list"], ["json", { outputFile: "test-results/e2e-docker/results.json" }]],
  timeout: 60_000,
  use: {
    ...devices["Desktop Chrome"],
    baseURL: process.env.E2E_BASE_URL || "http://localhost:18080",
    colorScheme: "light",
    viewport: { width: 1366, height: 768 },
    channel,
    // Rehearsal recording: E2E_VIDEO=1 keeps a video per step; E2E_HEADED=1 (scripts/e2e_docker.sh)
    // shows the browser, slowed by E2E_SLOWMO milliseconds per action so a person can follow it.
    video: process.env.E2E_VIDEO === "1" ? "on" : "off",
    launchOptions: { slowMo: Number(process.env.E2E_SLOWMO || 0) },
  },
});
