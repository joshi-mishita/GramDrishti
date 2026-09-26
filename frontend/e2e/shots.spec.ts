import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

/** Routes to capture. Edit this list to add screens. */
const ROUTES: { name: string; path: string; langs: ("en" | "hi" | "pa")[] }[] = [
  // Heavy-rain demo date in each view mode (S4 definition of done).
  { name: "map", path: "/map?date=2024-09-09&var=rain", langs: ["en", "hi", "pa"] },
  { name: "map-block", path: "/map?date=2024-09-09&var=rain&view=block", langs: ["en"] },
  { name: "map-delta", path: "/map?date=2024-09-09&var=rain&view=delta", langs: ["en"] },
  { name: "map-tmax-delta", path: "/map?date=2024-09-09&var=tmax&view=delta", langs: ["en"] },
  { name: "map-selected", path: "/map?date=2024-09-09&var=rain&pid=MP0103", langs: ["en"] },
  { name: "map-selected-wet", path: "/map?date=2024-09-09&var=rain&pid=MP0305", langs: ["en"] },
  { name: "map-no-demo-file", path: "/map?date=2024-01-12&var=tmin", langs: ["en"] },
  { name: "priority", path: "/priority?date=2024-09-09", langs: ["en", "hi"] },
  { name: "review", path: "/review?date=2024-09-09", langs: ["en"] },
  { name: "verification", path: "/verification?date=2024-09-09", langs: ["en"] },
  { name: "impact", path: "/impact?date=2024-09-09", langs: ["en", "pa"] },
  { name: "farmer-today", path: "/farmer?date=2024-09-09", langs: ["en", "hi", "pa"] },
  { name: "farmer-farm", path: "/farmer/farm?date=2024-09-09", langs: ["en", "hi"] },
  { name: "bulletin", path: "/bulletin/MP0103?date=2024-09-09", langs: ["en"] },
  { name: "not-found", path: "/nowhere", langs: ["en"] },
];

/**
 * Detail panel on the real API (SHOTS_REAL=1): three Panchayats with different observation
 * sources on a patchy-rain and a heavy-rain date, both in TEST. MP0305 has a weather station,
 * MP0412 a rain gauge only (no observed temperature), MP0302 no station (synthetic truth).
 */
const PANEL_ROUTES = ["2024-07-31", "2024-09-09"].flatMap((date) =>
  ["MP0305", "MP0412", "MP0302"].map((pid) => ({
    name: `panel-${date}-${pid}`,
    path: `/map?date=${date}&var=rain&pid=${pid}`,
  })),
);
const REAL = process.env.SHOTS_REAL === "1";

const VIEWPORTS = [
  { name: "desktop", width: 1366, height: 768 },
  { name: "phone", width: 360, height: 740 },
];

const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });

if (REAL) {
  for (const route of PANEL_ROUTES) {
    for (const vp of VIEWPORTS) {
      test(`${route.name} ${vp.name}`, async ({ page }) => {
        const errors: string[] = [];
        page.on("console", (m) => {
          if (m.type() === "error" || m.type() === "warning") errors.push(m.text());
        });
        page.on("pageerror", (e) => errors.push(e.message));
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.addInitScript(() => localStorage.setItem("gramdrishti.lang", "en"));
        await page.goto(route.path);
        await expect(page.locator(".ribbon")).toBeVisible();
        await page.getByRole("checkbox", { name: "Show what happened" }).check();
        await expect(page.getByText(/^Source: /)).toBeVisible({ timeout: 10_000 });
        await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
        await expect(page.locator(".detail-panel .error")).toHaveCount(0);
        await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
          timeout: 15_000,
        });
        await page.evaluate(() => document.fonts.ready);
        // What an officer sees first, then the whole panel with its scrolling switched off.
        await page.screenshot({ path: `${OUT}/${route.name}-${vp.name}.png` });
        await page.addStyleTag({
          content: ".detail-panel { overflow: visible !important; height: auto !important; }",
        });
        await page
          .locator(".detail-panel")
          .screenshot({ path: `${OUT}/${route.name}-${vp.name}-full.png` });
        expect(errors, "console errors or warnings").toEqual([]);
      });
    }
  }
}

for (const route of REAL ? [] : ROUTES) {
  for (const lang of route.langs) {
    for (const vp of VIEWPORTS) {
      test(`${route.name} ${lang} ${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.addInitScript((l) => localStorage.setItem("gramdrishti.lang", l), lang);
        await page.goto(route.path);
        // The ribbon is on every screen in mock mode; its presence means /meta has loaded.
        await expect(page.locator(".ribbon")).toBeVisible();
        await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
        if (route.path.startsWith("/map")) {
          // MapView sets data-painted once the current colours are drawn.
          await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
            timeout: 15_000,
          });
        }
        await page.evaluate(() => document.fonts.ready);
        await page.screenshot({
          path: `${OUT}/${route.name}-${lang}-${vp.name}.png`,
          fullPage: true,
        });
      });
    }
  }
}
