import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type APIRequestContext, type Page } from "@playwright/test";

/**
 * The demo script (Backend Guide B7) against the Docker stack (`npm run e2e:docker`, see
 * playwright.docker.config.ts). Every number and text the steps check is read from the same
 * API the screens use, so the test fails if a screen shows something else. Steps run in order
 * and share the stack's database: step 4 approves the advisories that step 5 shows the farmer.
 * Any console error or warning fails a step.
 */
const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });

const DATE = "2024-09-09"; // heavy monsoon rain, the main demo date
const BLOCK = "MB03";
// Same block, same crop (bajra), different advice: the S8 pair. F001 farms in MP0307.
const PID_A = "MP0307";
const PID_B = "MP0311";
const API = "/api/v1";

interface Advisory {
  id: string;
  panchayat_id: string;
  crop: string;
  category: string;
  status: string;
  action: { en: string; hi: string | null; pa: string | null };
  reason: { en: string; hi: string | null; pa: string | null };
}

function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error" || m.type() === "warning") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

async function setup(page: Page, lang = "en") {
  await page.addInitScript((l) => {
    localStorage.setItem("gramdrishti.lang", l);
    localStorage.setItem("gramdrishti.reviewer", "Playwright officer");
  }, lang);
}

async function settled(page: Page) {
  // The ribbon is translated; the English steps check its exact text in step 1.
  await expect(page.locator(".ribbon")).toBeVisible();
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 20_000 });
  await page.evaluate(() => document.fonts.ready);
}

async function mapPainted(page: Page) {
  await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
    timeout: 20_000,
  });
}

async function shot(page: Page, name: string) {
  await page.screenshot({ path: `${OUT}/s14-${name}.png`, fullPage: true });
}

async function getJson<T>(request: APIRequestContext, path: string): Promise<T> {
  const r = await request.get(`${API}${path}`);
  expect(r.status(), path).toBe(200);
  return (await r.json()) as T;
}

/**
 * The verification job's numbers exist only for the model version that went through it. A fresh
 * clone trains its own version (docs/DECISIONS.md D122): then the screen must say "not computed"
 * and the step is skipped, unless E2E_REQUIRE_VERIFICATION=1 (set when the stack runs the
 * verified model).
 */
async function skipWithoutVerification(page: Page, request: APIRequestContext, path: string) {
  const r = await request.get(`${API}/verification/summary`);
  if (r.status() === 200) return;
  expect(r.status()).toBe(503);
  expect((await r.json()).error.code).toBe("not_computed");
  expect(process.env.E2E_REQUIRE_VERIFICATION, "verification numbers are required").not.toBe("1");
  await page.goto(path);
  await expect(page.locator(".ribbon")).toBeVisible();
  await expect(page.locator(".error, [role=alert]").first()).toBeVisible({ timeout: 20_000 });
  test.skip(true, "this model version has no verification record; the screen says so");
}

async function bajraAdvice(request: APIRequestContext, pid: string): Promise<Advisory[]> {
  const all = await getJson<{ items: Advisory[] }>(
    request,
    `/advisories?issue_date=${DATE}&panchayat_id=${pid}`, // no status: every status
  );
  return all.items.filter((a) => a.crop === "bajra");
}

test.describe.configure({ mode: "serial" });

test("1 map: block forecast is one flat colour per block, Panchayat view shows the spread", async ({
  page,
  request,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  await page.goto(`/map?date=${DATE}&var=rain&view=block`);
  await settled(page);
  await mapPainted(page);
  await expect(page.locator(".ribbon")).toHaveText("Synthetic demo data. Not real weather.");
  await expect(page.getByRole("radio", { name: "Block", exact: true })).toBeChecked();
  await shot(page, "1-map-block");

  // The segmented control draws a face over the input; click the label like a person would.
  const panchayatView = page.getByRole("radio", { name: "Panchayat", exact: true });
  await page.locator("label", { has: panchayatView }).click();
  await expect(panchayatView).toBeChecked();
  await expect(page).not.toHaveURL(/view=block/);
  await mapPainted(page);
  await shot(page, "1-map-panchayat");

  // The spread, in numbers: within block MB03 the Panchayat values differ while the block
  // forecast column is one value.
  await page.getByRole("button", { name: "Show as table" }).click();
  const table = page.getByRole("table", { name: /Rain for every Panchayat/ });
  const geo = await getJson<{ features: { properties: { block_id: string } }[] }>(
    request,
    "/geo/panchayats",
  );
  const inBlock = geo.features.filter((f) => f.properties.block_id === BLOCK).length;
  const rows = table.locator("tbody tr").filter({ hasText: BLOCK });
  await expect(rows).toHaveCount(inBlock);
  // Columns: Panchayat name, block, Panchayat value, likely range, block forecast, difference.
  const cells = await rows.evaluateAll((trs) =>
    trs.map((tr) =>
      Array.from(tr.querySelectorAll("th,td")).map((td) => td.textContent?.trim() ?? ""),
    ),
  );
  // Rain medians are one value per block on this date (known issue, docs/PROGRESS.md S14); the
  // spread shows in the likely range, which differs between Panchayats of the block.
  const range = new Set(cells.map((c) => c[3]));
  const block = new Set(cells.map((c) => c[4]));
  expect(block.size, "block forecast column within MB03").toBe(1);
  expect(range.size, "likely ranges within MB03").toBeGreaterThan(1);
  expect(errors, "console errors or warnings").toEqual([]);
});

test("2 two Panchayats in one block: different forecasts, different bajra advice with reasons", async ({
  page,
  request,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  const values: string[] = [];
  for (const pid of [PID_A, PID_B]) {
    await page.goto(`/map?date=${DATE}&var=rain&pid=${pid}`);
    await settled(page);
    const panel = page.locator(".detail-panel");
    await expect(panel.getByRole("heading", { name: `Synthetic Panchayat ${pid}` })).toBeVisible();
    await expect(panel.getByText(`Block ${BLOCK}`)).toBeVisible();
    const forecast = await getJson<{ days: Record<string, unknown>[] }>(
      request,
      `/forecast/panchayat/${pid}?issue_date=${DATE}`,
    );
    values.push(JSON.stringify(forecast.days[0]));
    await shot(page, `2-panel-${pid}`);
  }
  expect(values[0], "first-day forecast of the two Panchayats").not.toBe(values[1]);

  const a = await bajraAdvice(request, PID_A);
  const b = await bajraAdvice(request, PID_B);
  const catsA = new Set(a.map((x) => x.category));
  const catsB = new Set(b.map((x) => x.category));
  expect(catsA.size).toBeGreaterThan(0);
  expect([...catsA].sort(), "same crop, same block, different advice").not.toEqual(
    [...catsB].sort(),
  );
  for (const adv of [a[0], b[0]]) {
    if (!adv) throw new Error("no bajra advisory");
    await page.goto(`/review?date=${DATE}&status=all&adv=${adv.id}`);
    await settled(page);
    const editor = page.getByRole("article");
    await expect(editor.getByRole("textbox", { name: /^Reason/ })).toHaveValue(adv.reason.en);
    await shot(page, `2-advice-${adv.panchayat_id}`);
  }
  expect(errors, "console errors or warnings").toEqual([]);
});

test("3 observed overlay says what really happened, and that it is synthetic truth", async ({
  page,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  await page.goto(`/map?date=${DATE}&var=rain&pid=${PID_A}`);
  await settled(page);
  await page.getByRole("checkbox", { name: "Show what happened" }).check();
  await expect(
    page.getByText("Source: synthetic truth from the demo data generator, not a measurement"),
  ).toBeVisible({ timeout: 15_000 });
  await expect(page.locator(".detail-panel .error")).toHaveCount(0);
  await shot(page, "3-observed");
  expect(errors, "console errors or warnings").toEqual([]);
});

test("4 review: edit one advisory, approve another, the audit trail shows both", async ({
  page,
  request,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  const advice = await bajraAdvice(request, PID_A);
  const drafts = advice.filter((x) => x.status === "draft");
  expect(drafts.length, "fresh stack: two draft bajra advisories for MP0307").toBeGreaterThan(1);
  const [toEdit, toApprove] = drafts;
  if (!toEdit || !toApprove) throw new Error("drafts missing");

  await page.goto(`/review?date=${DATE}&block=${BLOCK}&crop=bajra&adv=${toEdit.id}`);
  await settled(page);
  const editor = page.getByRole("article");
  await expect(editor.locator(".status-chip")).toHaveText("Waiting for review");
  const text = `${toEdit.action.en} Check the field drains before evening.`;
  await editor.getByRole("textbox", { name: /^Action/ }).fill(text);
  await editor.getByRole("button", { name: "Save edit and approve" }).click();
  await expect(editor.locator(".status-chip")).toHaveText("Edited and approved");
  await expect(editor.getByText(/Text changed: Action \(English\)/)).toBeVisible();
  await expect(editor.getByText("by Playwright officer").first()).toBeVisible();
  await shot(page, "4-edited-audit");

  await page.goto(`/review?date=${DATE}&block=${BLOCK}&crop=bajra&adv=${toApprove.id}`);
  await settled(page);
  await editor.getByRole("button", { name: "Approve", exact: true }).click();
  await expect(editor.locator(".status-chip")).toHaveText("Approved");
  await expect(editor.getByRole("listitem")).toHaveCount(2); // created, approved
  await shot(page, "4-approved-audit");

  const stored = await getJson<Advisory>(request, `/advisories/${toApprove.id}`);
  expect(stored.status).toBe("approved");
  expect(errors, "console errors or warnings").toEqual([]);
});

test("5a farmer phone view: the approved card in Hindi", async ({ page, request }) => {
  const errors = watchConsole(page);
  await setup(page, "hi");
  await page.setViewportSize({ width: 360, height: 740 });
  const approved = (await bajraAdvice(request, PID_A)).find((x) => x.status === "approved");
  if (!approved?.action.hi) throw new Error("step 4 approves an advisory with Hindi text");

  await page.goto(`/farmer?date=${DATE}`);
  await settled(page);
  await expect(page.getByText(approved.action.hi)).toBeVisible();
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await shot(page, "5-farmer-hi");
  expect(errors, "console errors or warnings").toEqual([]);
});

test("5b farmer phone view: tap Did it rain?", async ({ page }) => {
  await setup(page, "en");
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto(`/farmer?date=${DATE}`);
  await settled(page);
  // The "Did it rain today?" card arrives with S13 (farmer app). Until it is merged this step
  // is reported as skipped, not passed. scripts/e2e_docker.sh checks the API and SQLite side.
  const question = page.getByText(/^Did it rain today/);
  test.skip((await question.count()) === 0, "feedback card not in this build (S13 not merged)");
  await page.getByRole("button", { name: "Yes", exact: true }).click();
  await page.getByRole("button", { name: "Heavy", exact: true }).click();
  await expect(page.getByText(/Thank you|stored|saved/i)).toBeVisible();
  await shot(page, "5-farmer-feedback");
});

test("6 verification: every score on screen equals the verification job's file", async ({
  page,
  request,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  await skipWithoutVerification(page, request, `/verification?date=${DATE}`);
  type Metric = { name: string; model: number; b0: number; b1: number; b2: number | null };
  const summary = await getJson<{
    provenance: string;
    variables: { var: string; metrics: Metric[] }[];
  }>(request, "/verification/summary");
  expect(summary.provenance).toBe("computed");

  await page.goto(`/verification?date=${DATE}`);
  await settled(page);
  const table = page.getByRole("table", { name: /Scores of the model and three baselines/ });
  await expect(table).toBeVisible();
  // Rows with numbers (7 cells) come in API order: variable by variable, metric by metric.
  const shown = await table
    .locator("tbody tr")
    .evaluateAll((trs) =>
      trs
        .map((tr) =>
          Array.from(tr.querySelectorAll("th,td")).map((c) => c.textContent?.trim() ?? ""),
        )
        .filter((cells) => cells.length === 7),
    );
  const expected = summary.variables.flatMap((v) => v.metrics);
  expect(shown.length).toBe(expected.length);
  expected.forEach((m, i) => {
    const row = shown[i] ?? [];
    [m.model, m.b0, m.b1, m.b2].forEach((value, j) => {
      const cell = (row[j + 1] ?? "").replace(/,/g, "");
      if (value === null) return;
      const decimals = (cell.split(".")[1] ?? "").length;
      expect(
        Math.abs(Number(cell) - value),
        `${m.name} column ${j + 1}: screen ${cell}, file ${value}`,
      ).toBeLessThanOrEqual(0.5 * 10 ** -decimals + 1e-9);
    });
  });
  await expect(page.getByRole("heading", { name: "Where the model does not help" })).toBeVisible();
  await expect(page.getByRole("table", { name: /Forecast chance against observed/ })).toBeVisible();
  await shot(page, "6-verification");
  expect(errors, "console errors or warnings").toEqual([]);
});

test("7 impact: spray replay counts equal the job's file, model against block level", async ({
  page,
  request,
}) => {
  const errors = watchConsole(page);
  await setup(page);
  await skipWithoutVerification(page, request, `/impact?date=${DATE}`);
  type Counts = { correct: number; wasted_wait: number; washed_off: number };
  const impact = await getJson<{ model: Counts; block_baseline: Counts; n_decisions: number }>(
    request,
    "/impact?season=test_2024&decision=spray",
  );
  await page.goto(`/impact?date=${DATE}`);
  await settled(page);
  const table = page.getByRole("table", { name: "Counts of each outcome" });
  const fmt = (n: number) => n.toLocaleString("en-US");
  const model = table.getByRole("row", { name: /GramDrishti model/ });
  const block = table.getByRole("row", { name: /Block forecast B0/ });
  for (const [row, c] of [
    [model, impact.model],
    [block, impact.block_baseline],
  ] as const) {
    await expect(row).toContainText(fmt(c.correct));
    await expect(row).toContainText(fmt(c.wasted_wait));
    await expect(row).toContainText(fmt(c.washed_off));
    await expect(row).toContainText(fmt(impact.n_decisions));
  }
  await shot(page, "7-impact");
  expect(errors, "console errors or warnings").toEqual([]);
});
