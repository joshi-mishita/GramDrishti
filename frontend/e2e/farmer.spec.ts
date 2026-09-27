import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

/**
 * Farmer app journey on a 360 px phone in all three languages, offline reload, and the
 * bulletin's print layout. Runs on the demo files (see playwright.farmer.config.ts).
 */
const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });
const PHONE = { width: 360, height: 740 };
const DATE = "2024-09-09";

const WORDS = {
  en: { forecast: "Forecast", farm: "My farm", yes: "Yes", light: "Light", notSent: "not sent" },
  hi: {
    forecast: "पूर्वानुमान",
    farm: "मेरा खेत",
    yes: "हाँ",
    light: "हल्की",
    notSent: "नहीं भेजा",
  },
  pa: { forecast: "ਭਵਿੱਖਬਾਣੀ", farm: "ਮੇਰਾ ਖੇਤ", yes: "ਹਾਂ", light: "ਹਲਕਾ", notSent: "ਨਹੀਂ ਭੇਜਿਆ" },
} as const;

function watchConsole(page: Page): string[] {
  const errors: string[] = [];
  page.on("console", (m) => {
    if (m.type() === "error") errors.push(m.text());
  });
  page.on("pageerror", (e) => errors.push(e.message));
  return errors;
}

/** Nothing sticks out sideways: no page scroll, and no button text wider than its button. */
async function expectFits(page: Page) {
  const sideways = await page.evaluate(() => document.documentElement.scrollWidth);
  expect(sideways, "page scrolls sideways").toBeLessThanOrEqual(PHONE.width);
  const clipped = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".btn, .seg-face, .farmer-nav-link")]
      .filter((b) => b.offsetParent !== null && b.scrollWidth > b.clientWidth + 1)
      .map((b) => b.textContent),
  );
  expect(clipped, "buttons whose text does not fit").toEqual([]);
  const small = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".farmer-main .btn, .farmer-nav-link")]
      .filter((b) => b.offsetParent !== null && b.getBoundingClientRect().height < 44)
      .map((b) => b.textContent),
  );
  expect(small, "touch targets under 44 px").toEqual([]);
}

async function settle(page: Page) {
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
  await page.evaluate(() => document.fonts.ready);
}

for (const lang of ["en", "hi", "pa"] as const) {
  test(`farmer journey at 360 px in ${lang}`, async ({ page }) => {
    const errors = watchConsole(page);
    const w = WORDS[lang];
    await page.setViewportSize(PHONE);
    await page.addInitScript((l) => localStorage.setItem("gramdrishti.lang", l), lang);

    // Today
    await page.goto(`/farmer?date=${DATE}`);
    await expect(page.locator(".ribbon")).toBeVisible();
    await settle(page);
    expect(await page.evaluate(() => document.documentElement.lang)).toBe(lang);
    const hero = page.locator(".advice-hero");
    await expect(hero).toBeVisible();
    await expect(hero.locator(".advice-action")).toHaveAttribute("lang", lang);
    await expect(page.locator(".advice-item")).toHaveCount(2);
    await expectFits(page);
    await page.screenshot({ path: `${OUT}/farmer-today-${lang}-phone.png`, fullPage: true });

    // Forecast
    await page.getByRole("link", { name: w.forecast }).click();
    await settle(page);
    await expect(page.locator(".fc-day")).toHaveCount(5);
    await expect(page.locator(".spray svg").first()).toBeVisible();
    await expectFits(page);
    await page.screenshot({ path: `${OUT}/farmer-forecast-${lang}-phone.png`, fullPage: true });

    // My farm, with the rain question (the demo files cannot store it, and it says so)
    await page.getByRole("link", { name: w.farm }).click();
    await settle(page);
    await page.getByRole("button", { name: w.yes, exact: true }).click();
    await page.getByRole("button", { name: w.light, exact: true }).click();
    await expect(page.locator(".feedback-result")).toContainText(w.notSent);
    await expectFits(page);
    await page.screenshot({ path: `${OUT}/farmer-farm-${lang}-phone.png`, fullPage: true });

    // Bulletin, in the same language
    await page.goto(`/farmer?date=${DATE}`);
    await settle(page);
    await page.locator(`a[href^="/bulletin/"]`).click();
    await settle(page);
    await expect(page.locator(".bulletin")).toHaveAttribute("lang", lang);
    await expect(page.locator(".bulletin-actions > li")).toHaveCount(3);
    await page.screenshot({ path: `${OUT}/bulletin-${lang}-phone.png`, fullPage: true });

    expect(errors, "console errors").toEqual([]);
  });
}

test("works offline after one visit: reload shows the saved copy, the pill and the time", async ({
  page,
  context,
}) => {
  await page.setViewportSize(PHONE);
  await page.addInitScript(() => localStorage.setItem("gramdrishti.lang", "en"));
  await page.goto(`/farmer?date=${DATE}`);
  await settle(page);
  // The first load registers the worker; the next loads go through it and fill its cache.
  await page.evaluate(async () => {
    await navigator.serviceWorker.ready;
  });
  await page.reload();
  await settle(page);
  await expect(page.locator(".advice-hero")).toBeVisible();
  expect(await page.evaluate(() => !!navigator.serviceWorker.controller)).toBe(true);
  await expect(page.locator(".last-updated")).toHaveCount(0);
  await page.getByRole("link", { name: "Forecast" }).click();
  await settle(page);

  await context.setOffline(true);
  await page.goto(`/farmer?date=${DATE}`);
  await settle(page);
  await expect(page.locator(".advice-hero")).toBeVisible();
  await expect(page.getByRole("status", { name: "No internet connection" })).toBeVisible();
  await expect(page.locator(".last-updated")).toContainText(
    /Saved copy\. Last updated \w{3} \d+ \w{3}, \d\d:\d\d/,
  );
  await page.screenshot({ path: `${OUT}/farmer-offline-en-phone.png`, fullPage: true });

  await page.getByRole("link", { name: "Forecast" }).click();
  await settle(page);
  await expect(page.locator(".fc-day")).toHaveCount(5);

  await context.setOffline(false);
});

test("bulletin prints on A4 in black on white with 12 pt text or more", async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gramdrishti.lang", "en"));
  await page.goto(`/bulletin/MP0307?date=${DATE}&lang=hi`);
  await settle(page);
  // A4 minus the 14 mm margins is 182 x 269 mm: 688 x 1017 CSS px.
  await page.setViewportSize({ width: 688, height: 1017 });
  await page.emulateMedia({ media: "print" });
  const height = await page.evaluate(() => document.documentElement.scrollHeight);
  expect(height, "bulletin fits one A4 page").toBeLessThanOrEqual(1017);
  const hidden = await page.evaluate(() =>
    [".topbar", ".ribbon", ".bulletin-toolbar"].map(
      (s) => getComputedStyle(document.querySelector(s) as Element).display,
    ),
  );
  expect(hidden).toEqual(["none", "none", "none"]);
  const tooSmall = await page.evaluate(() =>
    [...document.querySelectorAll<HTMLElement>(".bulletin *")]
      .filter(
        (e) =>
          e.childNodes.length &&
          [...e.childNodes].some((n) => n.nodeType === 3 && n.textContent?.trim()),
      )
      .map((e) => [e.tagName, parseFloat(getComputedStyle(e).fontSize)] as const)
      .filter(([, px]) => px < 16),
  );
  expect(tooSmall, "text under 12 pt (16 px)").toEqual([]);
  const colours = await page.evaluate(() => {
    const out = new Set<string>();
    for (const e of document.querySelectorAll<HTMLElement>(".bulletin, .bulletin *")) {
      const cs = getComputedStyle(e);
      out.add(cs.color);
      if (cs.backgroundColor !== "rgba(0, 0, 0, 0)") out.add(`bg ${cs.backgroundColor}`);
    }
    return [...out];
  });
  expect(colours.filter((c) => !["rgb(0, 0, 0)", "bg rgb(255, 255, 255)"].includes(c))).toEqual([]);
  await expect(page.getByText("कृत्रिम डेमो डेटा। यह असली मौसम नहीं है।")).toBeVisible();
  await page.screenshot({ path: `${OUT}/bulletin-hi-print.png`, fullPage: true });
  await page.pdf({ path: `${OUT}/bulletin-MP0307-hi.pdf`, format: "A4", printBackground: false });
  expect(await page.evaluate(() => document.fonts.status)).toBe("loaded");
});
