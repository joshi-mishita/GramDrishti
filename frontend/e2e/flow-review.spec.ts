import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { expect, test, type Page } from "@playwright/test";

/**
 * S9 flows on the real API (`npm run e2e`, see playwright.e2e.config.ts): review an
 * advisory and check it survives a reload, then capture the priority, review and risk
 * layer screens. Any console error or warning fails the test.
 */
const OUT = resolve(import.meta.dirname, "../../docs/screens");
mkdirSync(OUT, { recursive: true });

const VIEWPORTS = [
  { name: "desktop", width: 1366, height: 768 },
  { name: "phone", width: 360, height: 740 },
];

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
  await expect(page.locator(".ribbon")).toBeVisible();
  await expect(page.locator(".skeleton")).toHaveCount(0, { timeout: 15_000 });
  await page.evaluate(() => document.fonts.ready);
}

test.describe.configure({ mode: "serial" });

test("edit the English text, approve, and it stays approved after a reload", async ({ page }) => {
  const errors = watchConsole(page);
  await setup(page);
  await page.goto("/review?date=2024-09-09");
  const list = page.getByRole("listbox", { name: /Waiting for review \(\d+\)/ });
  await expect(list).toBeVisible({ timeout: 15_000 });
  const before = Number(/\((\d+)\)/.exec((await list.getAttribute("aria-label")) ?? "")?.[1]);

  await list.getByRole("option").first().click();
  const editor = page.getByRole("article");
  await expect(editor.getByText("Waiting for review")).toBeVisible();
  const id = new URL(page.url()).searchParams.get("adv");
  expect(id).toMatch(/^ADV-2024-09-09-/);

  const text = "Irrigate bajra in the next two days and mulch to keep moisture in the soil.";
  const action = editor.getByRole("textbox", { name: /^Action/ });
  await action.fill(text);
  await expect(editor.getByRole("tab", { name: /English.*changed/ })).toBeVisible();
  await expect(editor.getByRole("button", { name: "Approve", exact: true })).toBeDisabled();
  await editor.getByRole("button", { name: "Save edit and approve" }).click();

  await expect(page.getByText(/^Edited and approved: /)).toBeVisible();
  await expect(editor.locator(".status-chip")).toHaveText("Edited and approved");
  await expect(
    page.getByRole("listbox", { name: `Waiting for review (${before - 1})` }),
  ).toBeVisible();

  // The review is stored: after a reload the advisory is fetched on its own (it has left
  // the draft list) and shows the edited text, the new status and the history entry.
  await page.reload();
  await settled(page);
  const again = page.getByRole("article");
  await expect(again.locator(".status-chip")).toHaveText("Edited and approved");
  await expect(again.getByRole("textbox", { name: /^Action/ })).toHaveValue(text);
  await expect(again.getByText("by Playwright officer")).toBeVisible();
  await expect(again.getByText(/Text changed: Action \(English\)/)).toBeVisible();

  // It is listed under Edited and approved.
  await page.getByRole("combobox", { name: "Status" }).selectOption("edited");
  const edited = page.getByRole("listbox", { name: /Edited and approved \(\d+\)/ });
  await expect(edited.getByRole("option", { selected: true })).toBeVisible();
  expect(errors, "console errors or warnings").toEqual([]);
});

test("approve with the keyboard: arrows, Enter, Ctrl+Enter", async ({ page }) => {
  const errors = watchConsole(page);
  await setup(page);
  await page.goto("/review?date=2024-09-09");
  const list = page.getByRole("listbox", { name: /Waiting for review/ });
  await expect(list).toBeVisible({ timeout: 15_000 });
  await list.focus();
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("ArrowDown");
  await page.keyboard.press("Enter");
  const editor = page.getByRole("article");
  await expect(editor.locator(".status-chip")).toHaveText("Waiting for review");
  await page.keyboard.press("Control+Enter");
  await expect(page.getByText(/^Approved: /)).toBeVisible();
  await expect(editor.locator(".status-chip")).toHaveText("Approved");
  await expect(editor.getByText("by Playwright officer")).toBeVisible();
  // A second Ctrl+Enter must not approve again.
  await page.keyboard.press("Control+Enter");
  await expect(editor.getByRole("listitem")).toHaveCount(2);
  expect(errors, "console errors or warnings").toEqual([]);
});

const SCREENS = [
  { name: "priority", path: "/priority?date=2024-09-09", langs: ["en", "hi"] },
  { name: "priority-dec", path: "/priority?date=2024-12-24&horizon=3", langs: ["en"] },
  { name: "review", path: "/review?date=2024-09-09", langs: ["en", "pa"], open: true },
  {
    name: "map-risk-heavy-rain",
    path: "/map?date=2024-09-09&var=rain&risk=heavy_rain",
    langs: ["en"],
  },
  { name: "map-risk-frost", path: "/map?date=2024-12-24&var=tmin&risk=frost", langs: ["en"] },
  {
    name: "map-risk-selected",
    path: "/map?date=2024-09-09&var=rain&risk=waterlogging&day=2&pid=MP0307",
    langs: ["en"],
  },
];

for (const s of SCREENS) {
  for (const lang of s.langs) {
    for (const vp of VIEWPORTS) {
      test(`screen ${s.name} ${lang} ${vp.name}`, async ({ page }) => {
        const errors = watchConsole(page);
        await page.setViewportSize({ width: vp.width, height: vp.height });
        await setup(page, lang);
        await page.goto(s.path);
        await settled(page);
        if (s.open) {
          await page.getByRole("listbox").getByRole("option").nth(2).click();
          await expect(page.getByRole("article")).toBeVisible();
          await settled(page);
        }
        if (s.path.startsWith("/map")) {
          await expect(page.locator('.map-canvas[data-painted="true"]')).toHaveCount(1, {
            timeout: 15_000,
          });
        }
        await page.screenshot({
          path: `${OUT}/s9-${s.name}-${lang}-${vp.name}.png`,
          fullPage: true,
        });
        expect(errors, "console errors or warnings").toEqual([]);
      });
    }
  }
}

test("priority list prints as a plain table with the filters as text", async ({ page }) => {
  const errors = watchConsole(page);
  await setup(page);
  await page.goto("/priority?date=2024-09-09&type=heavy_rain");
  await settled(page);
  await page.emulateMedia({ media: "print" });
  await expect(page.getByText("Next 2 days. Risk: Heavy rain. Block: All blocks.")).toBeVisible();
  await expect(page.getByRole("button", { name: "Print list" })).toBeHidden();
  await expect(page.getByRole("columnheader", { name: /Level/ })).toContainText("Level");
  await page.screenshot({ path: `${OUT}/s9-priority-print.png`, fullPage: true });
  expect(errors, "console errors or warnings").toEqual([]);
});
