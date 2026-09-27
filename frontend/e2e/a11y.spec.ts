import { appendFileSync, mkdirSync } from "node:fs";
import { resolve } from "node:path";
import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";

/** Every screen, with the states an officer or farmer actually reaches (panel open, table view). */
const ROUTES: { name: string; path: string; setup?: "table" }[] = [
  { name: "map", path: "/map?date=2024-09-09&var=rain" },
  { name: "map-selected", path: "/map?date=2024-09-09&var=rain&pid=MP0305" },
  { name: "map-table", path: "/map?date=2024-09-09&var=rain", setup: "table" },
  { name: "map-risk", path: "/map?date=2024-09-09&var=rain&risk=heavy_rain" },
  { name: "priority", path: "/priority?date=2024-09-09" },
  { name: "review", path: "/review?date=2024-09-09" },
  { name: "review-open", path: "/review?date=2024-09-09&adv=ADV-2024-09-09-MP0301-cotton-spray" },
  { name: "verification", path: "/verification?date=2024-09-09" },
  { name: "impact", path: "/impact?date=2024-09-09" },
  { name: "farmer-today", path: "/farmer?date=2024-09-09" },
  { name: "farmer-forecast", path: "/farmer/forecast?date=2024-09-09" },
  { name: "farmer-farm", path: "/farmer/farm?date=2024-09-09" },
  { name: "bulletin", path: "/bulletin/MP0103?date=2024-09-09" },
  { name: "not-found", path: "/nowhere" },
];
const LANGS = ["en", "hi", "pa"] as const;
const VIEWPORTS = [
  { name: "desktop", width: 1366, height: 768 },
  { name: "phone", width: 360, height: 740 },
];

const OUT = resolve(import.meta.dirname, "../test-results/a11y");
mkdirSync(OUT, { recursive: true });
const SUMMARY = `${OUT}/axe-summary.jsonl`;

for (const route of ROUTES) {
  for (const lang of LANGS) {
    for (const vp of VIEWPORTS) {
      test(`axe ${route.name} ${lang} ${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.addInitScript((l) => localStorage.setItem("gramdrishti.lang", l), lang);
        await page.goto(route.path);
        await expect(page.locator(".ribbon")).toBeVisible();
        await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
        if (route.setup === "table") {
          await page.locator(".map-table-toggle").click();
          await expect(page.locator(".map-table-toggle")).toHaveAttribute("aria-pressed", "true");
        }
        await page.evaluate(() => document.fonts.ready);
        const result = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "best-practice"])
          .analyze();
        const found = result.violations.map((v) => ({
          id: v.id,
          impact: v.impact,
          help: v.help,
          nodes: v.nodes.length,
          targets: v.nodes.slice(0, 5).map((n) => n.target.join(" ")),
        }));
        appendFileSync(
          SUMMARY,
          JSON.stringify({ route: route.name, lang, viewport: vp.name, violations: found }) + "\n",
        );
        const blocking = found.filter((v) => v.impact === "serious" || v.impact === "critical");
        expect(blocking, "serious or critical axe violations").toEqual([]);
      });
    }
  }
}
