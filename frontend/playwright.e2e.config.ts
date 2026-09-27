import { resolve } from "node:path";
import { defineConfig, devices } from "@playwright/test";

/**
 * `npm run e2e`: end-to-end flows against a real API with a throwaway database.
 *
 * Starts the backend on port 8010 with GRAMDRISHTI_DB pointing at a fresh file under
 * test-results/, so reviews made by the tests never touch backend/artifacts/gramdrishti.sqlite.
 * The API writes drafts into that database on first use. Needs the backend venv and the
 * forecast snapshots (see CLAUDE.md: train, then run_daily --all-demo-dates); not part of CI.
 *
 * The app is built and served with `vite preview` on port 4174, with risk, priority and
 * advisories (and the map groups) served by that API. Screens are saved to ../docs/screens/.
 */
const channel = process.env.SHOTS_BROWSER_CHANNEL || undefined;
const DB = resolve(import.meta.dirname, "test-results/e2e.sqlite");
const BACKEND = resolve(import.meta.dirname, "../backend");
const API_PORT = 8010;

export default defineConfig({
  testDir: "./e2e",
  testMatch: "flow-*.spec.ts",
  outputDir: "./test-results/e2e",
  // One worker: the tests share the database and run in order.
  workers: 1,
  fullyParallel: false,
  reporter: "list",
  use: {
    ...devices["Desktop Chrome"],
    baseURL: "http://localhost:4174",
    colorScheme: "light",
    channel,
  },
  webServer: [
    {
      command: `rm -f "${DB}" && mkdir -p "${resolve(DB, "..")}" && GRAMDRISHTI_DB="${DB}" "${BACKEND}/.venv/bin/uvicorn" --app-dir "${BACKEND}" gramdrishti.api.main:app --port ${API_PORT}`,
      url: `http://localhost:${API_PORT}/api/v1/health`,
      reuseExistingServer: false,
      timeout: 60_000,
    },
    {
      command: "npm run build && npx vite preview --port 4174 --strictPort",
      url: "http://localhost:4174",
      reuseExistingServer: false,
      timeout: 120_000,
      env: {
        VITE_REAL_ENDPOINTS: "meta,geo,forecast,observed,explain,risk,priority,advisories",
        VITE_SNAPSHOT: "",
        API_PROXY_TARGET: `http://localhost:${API_PORT}`,
      },
    },
  ],
});
