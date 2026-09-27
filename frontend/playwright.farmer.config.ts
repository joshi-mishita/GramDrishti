import { defineConfig, devices } from "@playwright/test";

/**
 * `npm run e2e:farmer`: the farmer app at 360 px in English, Hindi and Punjabi, the offline
 * reload test and the bulletin's print layout. Builds the app and serves it with
 * `vite preview` on the demo files (no API needed), because the service worker exists only
 * in a production build. Screenshots go to ../docs/screens/.
 */
const channel = process.env.SHOTS_BROWSER_CHANNEL || undefined;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "farmer.spec.ts",
  outputDir: "./test-results/farmer",
  fullyParallel: true,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:4175",
    colorScheme: "light",
    channel,
  },
  webServer: {
    command: "npm run build && npx vite preview --port 4175 --strictPort",
    url: "http://localhost:4175",
    reuseExistingServer: false,
    timeout: 180_000,
    env: { VITE_REAL_ENDPOINTS: "", VITE_SNAPSHOT: "" },
  },
});
