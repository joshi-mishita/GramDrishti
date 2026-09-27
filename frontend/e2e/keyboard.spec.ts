import { expect, test, type Page } from "@playwright/test";

/**
 * Keyboard-only walkthrough of the officer and farmer flows (no mouse anywhere), on the demo
 * files. After every Tab the focused control must show a focus ring: an outline or a box
 * shadow on the element itself, or on the visible face of a styled radio.
 */

/** Describes the focused element and whether its focus is visible. */
async function focused(page: Page) {
  return page.evaluate(() => {
    const el = document.activeElement as HTMLElement | null;
    if (!el || el === document.body) return { name: "body", visible: false, tag: "BODY" };
    const ring = (e: Element) => {
      const s = getComputedStyle(e);
      return (
        (s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== "none"
      );
    };
    // Styled radios hide the input; the ring is drawn on the face next to it.
    const face = el.matches("input[type=radio]") ? el.nextElementSibling : null;
    const label =
      el.getAttribute("aria-label") ||
      (el.closest("label")?.textContent ?? el.textContent ?? "").trim().slice(0, 60);
    return { name: label, visible: ring(el) || (face ? ring(face) : false), tag: el.tagName };
  });
}

/** Presses Tab up to `max` times until the focused element's text matches. */
async function tabTo(page: Page, match: RegExp, max = 60) {
  const seen: string[] = [];
  for (let i = 0; i < max; i++) {
    await page.keyboard.press("Tab");
    const f = await focused(page);
    seen.push(f.name);
    expect(f.visible, `focus ring on ${f.tag} "${f.name}" after ${seen.join(" | ")}`).toBe(true);
    if (match.test(f.name)) {
      // A person does not press the next key 5 ms after focus lands; Chrome can drop a key
      // sent that fast, which made this walkthrough flaky without any fault in the app.
      await page.waitForTimeout(50);
      return;
    }
  }
  throw new Error(`Tab never reached ${match}: ${seen.join(" | ")}`);
}

test.beforeEach(async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem("gramdrishti.lang", "en"));
});

test("officer: skip link, day and variable, table, open a Panchayat, priority row", async ({
  page,
}) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/map?date=2024-09-09&var=rain");
  await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
    timeout: 15_000,
  });

  // The first Tab lands on the skip link, which moves focus to the main area.
  await page.keyboard.press("Tab");
  await expect(page.locator(".skip-link")).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.locator("#main")).toBeFocused();

  // Day strip: arrow keys move between the five days.
  await tabTo(page, /Tue 10 Sep/);
  await page.keyboard.press("ArrowRight");
  await expect(page).toHaveURL(/day=2/);

  // Variable list: arrow down from Rain to Max temperature.
  await expect(page.locator('input[name="lead-day"][value="2"]')).toBeFocused();
  await page.keyboard.press("ArrowLeft");
  await expect(page).not.toHaveURL(/day=2/); // day 1 is the default and leaves the URL
  await tabTo(page, /^Rain/);
  await expect(page.locator('input[name="variable"][value="rain"]')).toBeFocused();
  await page.keyboard.press("ArrowDown");
  await expect(page).toHaveURL(/var=tmax/);
  // Back to rain: the demo files have every Panchayat for rain on day 1.
  await page.keyboard.press("ArrowUp");
  await expect(page).toHaveURL(/var=rain/);

  // Table alternative to the map, then open a Panchayat from it.
  await tabTo(page, /Show as table/);
  await page.keyboard.press("Enter");
  await tabTo(page, /Synthetic Panchayat MP0101/);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/pid=MP0101/);
  await expect(page.getByRole("heading", { name: "Synthetic Panchayat MP0101" })).toBeVisible();

  // Priority: the first row's link opens the map at that Panchayat.
  await page.goto("/priority?date=2024-09-09");
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
  await tabTo(page, /Synthetic Panchayat MP0301/, 80);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/map\?.*pid=MP0301/);
});

test("officer: review queue with arrow keys and Enter", async ({ page }) => {
  await page.setViewportSize({ width: 1366, height: 768 });
  await page.goto("/review?date=2024-09-09");
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });
  // The queue is one Tab stop; arrow keys move inside it.
  await tabTo(page, /Waiting for review \(198\)/, 80);
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/adv=ADV-2024-09-09-MP0101-bajra-dry_spell/);
  await expect(page.getByRole("heading", { level: 2, name: /Dry spell/ })).toBeVisible();
});

test("farmer: language, why and what if, bottom navigation, rain question", async ({ page }) => {
  await page.setViewportSize({ width: 360, height: 740 });
  await page.goto("/farmer?date=2024-09-09");
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 10_000 });

  // Language switch: arrow keys change the language at once.
  await tabTo(page, /^English$/);
  await page.keyboard.press("ArrowRight");
  await expect(page.locator("html")).toHaveAttribute("lang", "hi");
  await page.keyboard.press("ArrowLeft");
  await expect(page.locator("html")).toHaveAttribute("lang", "en");

  // The first card's "Why, and what if" opens with Enter.
  await tabTo(page, /Why, and what if/);
  await page.keyboard.press("Enter");
  await expect(page.locator(".advice-more").first()).toHaveAttribute("open", "");

  // Bottom navigation to Forecast, then the rain question's Yes button.
  await tabTo(page, /^Forecast$/, 80);
  await page.keyboard.press("Enter");
  await expect(page).toHaveURL(/\/farmer\/forecast/);
  // Focus moves to the new screen, so Tab continues into it rather than off the page.
  await expect(page.locator("#main")).toBeFocused();
  await tabTo(page, /^Yes$/, 80);
  await page.keyboard.press("Enter");
  // The pressed button is replaced by the amounts; focus follows to the first one.
  await expect(page.getByRole("button", { name: "Light" })).toBeFocused();
  await page.keyboard.press("Enter");
  await expect(page.getByRole("status").filter({ hasText: /not sent/ })).toBeFocused();
});
