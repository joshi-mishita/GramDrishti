import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../api/client";
import { useAppStore } from "../state/store";
import { renderWithProviders } from "../test/render";
import ImpactPage from "./ImpactPage";

const EXAMPLES = resolve(__dirname, "../../../contract/examples");

function stubFetch() {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const file = /^\/mock\/(.+)$/.exec(url)?.[1] ?? "";
      try {
        return new Response(readFileSync(resolve(EXAMPLES, file), "utf8"), { status: 200 });
      } catch {
        return new Response("not found", { status: 404 });
      }
    }),
  );
}

beforeEach(() => {
  clearIndexCache();
  stubFetch();
  useAppStore.setState({ issueDate: "2024-09-09", lang: "en" });
});
afterEach(() => vi.unstubAllGlobals());

describe("impact screen", () => {
  it("draws model and block bars for spraying over the whole test period", async () => {
    renderWithProviders(<ImpactPage />);
    // impact_test_2024_spray.json: model 14364 / 217 / 179, B0 14138 / 554 / 68 of 14760.
    const model = await screen.findByRole("img", { name: /^GramDrishti model:/ });
    expect(model).toHaveAccessibleName(
      "GramDrishti model: Correct: 14,364 (97.3%); Wasted wait: 217 (1.5%); Washed off: 179 (1.2%)",
    );
    const block = screen.getByRole("img", { name: /^Block forecast B0:/ });
    expect(block).toHaveAccessibleName(
      "Block forecast B0: Correct: 14,138 (95.8%); Wasted wait: 554 (3.8%); Washed off: 68 (0.5%)",
    );
    // Numbers are written on (or right under) the bars, not only read out.
    const bar = model.closest(".decision-bar") as HTMLElement;
    expect(bar).toHaveTextContent("Correct: 14,364 (97.3%)");
    expect(bar).toHaveTextContent("Washed off: 179 (1.2%)");
  });

  it("explains the rule in plain words and what each mistake means", async () => {
    renderWithProviders(<ImpactPage />);
    expect(
      await screen.findByText(
        "Advise spraying tomorrow when the chance of 2.5 mm rain or more is under 30%.",
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Washed off: spraying went ahead and 2.5 mm or more came/),
    ).toBeInTheDocument();
    expect(screen.getByText("Thresholds pending expert review.")).toBeInTheDocument();
  });

  it("bolds the most correct and the fewest of each mistake, including B0 where it wins", async () => {
    renderWithProviders(<ImpactPage />);
    const table = await screen.findByRole("table", { name: "Counts of each outcome" });
    const b0 = table.querySelector('tr[data-row="b0"]') as HTMLElement;
    const model = table.querySelector('tr[data-row="model"]') as HTMLElement;
    // B0 washes off least (68); the model is most often correct and wastes fewest waits.
    expect(within(b0).getAllByRole("cell")[2]?.querySelector("strong")).toHaveTextContent(
      "68 (0.5%)",
    );
    expect(within(model).getAllByRole("cell")[0]?.querySelector("strong")).not.toBeNull();
    expect(within(model).getAllByRole("cell")[2]?.querySelector("strong")).toBeNull();
    expect(table.querySelector('tr[data-row="b1"]')).toHaveTextContent("14,224");
  });

  it("names heat-alert mistakes as false alarms and missed heat", async () => {
    const user = userEvent.setup();
    renderWithProviders(<ImpactPage />);
    await screen.findByRole("img", { name: /^GramDrishti model:/ });
    await user.click(screen.getByRole("radio", { name: "Heat alert" }));
    await user.click(screen.getByRole("radio", { name: "Monsoon 2024" }));
    // impact_heat_alert.json (monsoon): model 5665 / 1167 / 8.
    expect(
      await screen.findByRole("img", {
        name: "GramDrishti model: Correct: 5,665 (82.8%); False alarm: 1,167 (17.1%); Missed heat: 8 (0.1%)",
      }),
    ).toBeInTheDocument();
    expect(screen.getByText(/The event happened 2,385 times/)).toBeInTheDocument();
  });
});
