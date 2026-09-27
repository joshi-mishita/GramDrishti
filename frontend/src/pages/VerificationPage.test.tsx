import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../api/client";
import type { VerificationSummary } from "../api/types";
import { useAppStore } from "../state/store";
import { renderWithProviders } from "../test/render";
import VerificationPage from "./VerificationPage";

const EXAMPLES = resolve(__dirname, "../../../contract/examples");
const summary = JSON.parse(
  readFileSync(resolve(EXAMPLES, "verification_summary.json"), "utf8"),
) as VerificationSummary;

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

async function comparisonTable() {
  return screen.findByRole("table", { name: /Scores of the model and three baselines/ });
}

/** The row of a metric inside a variable's group (rowgroup bodies follow table order). */
function metricRow(table: HTMLElement, variable: number, metric: string): HTMLElement {
  const body = table.querySelectorAll("tbody")[variable] as HTMLElement;
  return body.querySelector(`tr[data-metric="${metric}"]`) as HTMLElement;
}

function cells(row: HTMLElement): HTMLElement[] {
  return Array.from(row.querySelectorAll("td"));
}

describe("verification screen", () => {
  it("opens with one sentence on data, period and method, and the synthetic notice", async () => {
    renderWithProviders(<VerificationPage />);
    expect(
      await screen.findByText(
        /model s5-lgbm-9b632a7b1b for every issue date from Wed 17 Jul 2024 to Tue 31 Dec 2024/,
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/synthetic Panchayat truth \(mock data generator\) by three checks/),
    ).toBeInTheDocument();
    expect(screen.getByText(/Synthetic demo data, not real weather/)).toBeInTheDocument();
  });

  it("shows the job's numbers with the best value in each row in bold", async () => {
    renderWithProviders(<VerificationPage />);
    const table = await comparisonTable();
    // Rain MAE: model 1.07045, B0 1.23993, B1 1.03107, B2 1.03153. B1 and B2 differ in the
    // third decimal, so the row shows three; B1 is best, the model is not.
    const mae = cells(metricRow(table, 0, "MAE"));
    expect(mae.slice(0, 4).map((c) => c.textContent)).toEqual(["1.070", "1.240", "1.031", "1.032"]);
    expect(mae.map((c) => c.querySelector("strong") !== null).slice(0, 4)).toEqual([
      false,
      false,
      true,
      false,
    ]);
    // Tmax MAE: the model is best, two decimals are enough.
    const tmax = cells(metricRow(table, 1, "MAE"));
    expect(tmax[0]).toHaveTextContent("1.08");
    expect(tmax[0]?.querySelector("strong")).not.toBeNull();
    // Bias: model and B1 are identical (reconciled), both bold.
    const bias = cells(metricRow(table, 0, "bias"));
    expect(bias.slice(0, 4).map((c) => c.querySelector("strong") !== null)).toEqual([
      true,
      false,
      true,
      false,
    ]);
  });

  it("shows a losing row like any other row and says so in words", async () => {
    renderWithProviders(<VerificationPage />);
    const table = await comparisonTable();
    const wet = metricRow(table, 0, "MAE_wet_days_obs_ge_1mm");
    expect(wet).toBeVisible();
    expect(wet.className).toBe("");
    expect(wet).not.toHaveAttribute("aria-hidden");
    expect(within(wet).getByRole("rowheader")).toHaveTextContent(
      "Mean absolute error on wet days (1 mm or more observed)mm",
    );
    const skillB1 = cells(wet)[5] as HTMLElement;
    expect(skillB1).toHaveTextContent("-7.2%");
    expect(skillB1).toHaveTextContent("-12.0% to -0.04%, worse");
    // Rain MAE against B1 is a tie; against B0 a win.
    const mae = cells(metricRow(table, 0, "MAE"));
    expect(mae[4]).toHaveTextContent("+13.7%+4.0% to +27.9%, better");
    expect(mae[5]).toHaveTextContent("-3.8%-8.1% to +0.8%, no clear difference");
  });

  it("switches the table to the other checks", async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerificationPage />);
    await comparisonTable();
    await user.click(screen.getByRole("radio", { name: "Held-out block" }));
    const table = screen.getByRole("table", { name: /Held-out block/ });
    // Leave-one-block-out scores point forecasts only: no quantile loss row.
    expect(table.querySelector('tr[data-metric="quantile_loss"]')).toBeNull();
    const lobo = summary.checks?.find((c) => c.check === "leave_one_block_out");
    expect(table.querySelectorAll("tbody")).toHaveLength(lobo?.variables.length ?? -1);
  });

  it("lists where the model does not help, from the job's notes", async () => {
    renderWithProviders(<VerificationPage />);
    const heading = await screen.findByRole("heading", { name: "Where the model does not help" });
    const list = heading.parentElement?.querySelector("ul") as HTMLElement;
    const items = within(list).getAllByRole("listitem");
    expect(items.length).toBeGreaterThan(5);
    expect(list).toHaveTextContent("Does NOT beat B1 on rain MAE (temporal_holdout)");
    expect(list).toHaveTextContent("rain_ge_35mm: model yes/no CSI 0.141 is below B0 (0.349).");
  });

  it("draws the reliability table for the chosen event", async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerificationPage />);
    const table = await screen.findByRole("table", {
      name: /Forecast chance against observed frequency, Rain 2.5 mm or more/,
    });
    expect(within(table).getAllByRole("row")).toHaveLength(11);
    expect(
      within(table).getByRole("rowheader", { name: "90% to 100%" }).parentElement,
    ).toHaveTextContent("91.4%70.4%761");
    await user.click(screen.getByRole("radio", { name: "35 mm" }));
    expect(await screen.findByRole("table", { name: /Rain 35 mm or more/ })).toBeInTheDocument();
  });

  it("gives coverage per variable with the wet-day rain row and the width", async () => {
    const user = userEvent.setup();
    renderWithProviders(<VerificationPage />);
    const table = await screen.findByRole("table", { name: "Interval coverage per variable" });
    const wet = within(table).getByText("Wet days (1 mm or more observed)").closest("tr");
    expect(wet).toHaveTextContent("80%50.9%28.7 mm4,458");
    await user.click(screen.getByRole("radio", { name: "By lead day" }));
    expect(within(table).getAllByRole("row")).toHaveLength(26); // header + 5 vars x 5 days
  });

  it("lists held-out blocks and stations with model minus B0", async () => {
    renderWithProviders(<VerificationPage />);
    const table = await screen.findByRole("table", { name: /by held-out block and station, Rain/ });
    const mb01 = within(table).getByRole("rowheader", { name: "Block MB01" }).closest("tr");
    // model 0.940999, B0 1.03265, B1 0.863528, B2 0.869707: B1 best. Three decimals for the
    // whole table: B1 0.813 and B2 0.807 at MOCK_AWS_22 would both print 0.81.
    expect(mb01).toHaveTextContent("10,6600.9411.0330.8640.870-0.092");
    expect(mb01?.querySelectorAll("strong")).toHaveLength(1);
    expect(within(table).getByRole("rowheader", { name: "Station MOCK_ARG_03" })).toBeVisible();
  });
});
