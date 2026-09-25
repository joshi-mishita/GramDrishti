import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test } from "@playwright/test";

/** Routes to capture. Edit this list to add screens. */
const ROUTES: { name: string; path: string; langs: ("en" | "hi" | "pa")[] }[] = [
  { name: "map", path: "/map?date=2024-09-09&var=rain", langs: ["en", "hi", "pa"] },
  { name: "map-selected", path: "/map?date=2024-09-09&var=rain&pid=MP0103", langs: ["en"] },
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

const VIEWPORTS = [
  { name: "desktop", width: 1366, height: 768 },
  { name: "phone", width: 360, height: 740 },
];

const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });

for (const route of ROUTES) {
  for (const lang of route.langs) {
    for (const vp of VIEWPORTS) {
      test(`${route.name} ${lang} ${vp.name}`, async ({ page }) => {
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await page.addInitScript((l) => localStorage.setItem("gramdrishti.lang", l), lang);
        await page.goto(route.path);
        // The ribbon is on every screen in mock mode; its presence means /meta has loaded.
        await expect(page.locator(".ribbon")).toBeVisible();
        await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
        await page.evaluate(() => document.fonts.ready);
        await page.screenshot({
          path: `${OUT}/${route.name}-${lang}-${vp.name}.png`,
          fullPage: true,
        });
      });
    }
  }
}
