import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

/**
 * Demo insurance (Backend Guide B6) with the API container stopped (`scripts/e2e_docker.sh`
 * sets E2E_API_DOWN=1 after `docker compose stop api`). The offline copy (VITE_SNAPSHOT=1,
 * port 18081) must still show the map, a Panchayat panel, verification and the farmer screen;
 * the live app must answer with its error state, not hang.
 */
const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });
const OFFLINE = process.env.E2E_OFFLINE_URL || "http://localhost:18081";
const DATE = "2024-09-09";

test.skip(
  process.env.E2E_API_DOWN !== "1",
  "runs only with the API stopped (scripts/e2e_docker.sh)",
);
test.describe.configure({ mode: "serial" });

// Chromium's software WebGL (CI has no GPU) logs performance notes such as "GPU stall due to
// ReadPixels" as warnings. They come from the browser, not the app; real GL errors still count.
const GL_PERFORMANCE_NOTE = /^\[\.WebGL-[^\]]*\]GL Driver Message \(OpenGL, Performance,/;

function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() !== "error" && m.type() !== "warning") return;
    if (!GL_PERFORMANCE_NOTE.test(m.text())) errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

async function settled(page: Page) {
  await expect(page.locator(".ribbon")).toHaveText("Synthetic demo data. Not real weather.");
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 20_000 });
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gramdrishti.lang", "en"));
});

test("the API is really down", async ({ request }) => {
  const r = await request.get("/api/v1/health");
  expect(r.status()).toBe(503);
  expect((await r.json()).error.code).toBe("not_available");
});

test("offline copy: map and Panchayat panel without the API", async ({ page }) => {
  const errors = watchConsole(page);
  const api: string[] = [];
  page.on("request", (r) => {
    if (r.url().includes("/api/")) api.push(r.url());
  });
  await page.goto(`${OFFLINE}/map?date=${DATE}&var=rain&pid=MP0307`);
  await settled(page);
  await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
    timeout: 20_000,
  });
  await expect(
    page.locator(".detail-panel").getByRole("heading", { name: "Synthetic Panchayat MP0307" }),
  ).toBeVisible();
  await page.screenshot({ path: `${OUT}/s14-offline-map.png`, fullPage: true });
  expect(api, "snapshot mode never calls the API").toEqual([]);
  expect(errors, "console errors or warnings").toEqual([]);
});

test("offline copy: verification and farmer screens without the API", async ({ page }) => {
  const errors = watchConsole(page);
  await page.goto(`${OFFLINE}/verification?date=${DATE}`);
  await settled(page);
  const scores = page.getByRole("table", { name: /Scores of the model and three baselines/ });
  if (process.env.E2E_REQUIRE_VERIFICATION === "1") {
    await expect(scores).toBeVisible();
  } else {
    // A model version without a verification record exports its "not computed" answer.
    await expect(scores.or(page.locator(".error, [role=alert]").first())).toBeVisible();
  }
  await page.goto(`${OFFLINE}/farmer?date=${DATE}`);
  await settled(page);
  await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
  await page.screenshot({ path: `${OUT}/s14-offline-farmer.png`, fullPage: true });
  expect(errors, "console errors or warnings").toEqual([]);
});

test("live app with the API down shows an error state, not a blank page", async ({ page }) => {
  test.setTimeout(90_000);
  await page.goto(`/map?date=${DATE}&var=rain`);
  // The client retries each request before giving up (about 30 s). No ribbon here: no response
  // has told the app its data mode.
  const error = page.getByText("Could not load the Panchayat boundaries", { exact: false });
  await expect(error).toBeVisible({ timeout: 60_000 });
  await expect(page.getByText(/not_available: The API is not reachable/).first()).toBeVisible();
  await expect(page.getByRole("button", { name: "Try again" }).first()).toBeVisible();
  await page.screenshot({ path: `${OUT}/s14-api-down.png`, fullPage: true });
});
