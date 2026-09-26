import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../../api/client";
import { useAppStore } from "../../state/store";
import { renderWithProviders } from "../../test/render";
import { DetailPanel } from "./DetailPanel";

const EXAMPLES = resolve(__dirname, "../../../../contract/examples");

/** Serves /mock/* from contract/examples; `override` replaces a file's JSON. */
function stubFetch(override: Record<string, (json: unknown) => unknown> = {}) {
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const file = /^\/mock\/(.+)$/.exec(url)?.[1] ?? "";
      try {
        const text = readFileSync(resolve(EXAMPLES, file), "utf8");
        const fix = override[file];
        return new Response(fix ? JSON.stringify(fix(JSON.parse(text))) : text, { status: 200 });
      } catch {
        return new Response("not found", { status: 404 });
      }
    }),
  );
}

function select(pid: string, variable: "rain" | "tmax", lang: "en" | "hi" = "en") {
  useAppStore.setState({
    issueDate: "2024-09-09",
    leadDay: 1,
    variable,
    viewMode: "panchayat",
    selectedPid: pid,
    lang,
  });
}

beforeEach(() => clearIndexCache());
afterEach(async () => {
  vi.unstubAllGlobals();
  const { default: i18n } = await import("i18next");
  await i18n.changeLanguage("en");
});

describe("detail panel", () => {
  it("shows the 5-day numbers, the day's details, reasons and changes", async () => {
    stubFetch();
    select("MP0305", "tmax");
    renderWithProviders(<DetailPanel />);

    // Fan chart: the screen-reader table carries the plotted numbers.
    const chartTable = await screen.findByRole("table", {
      name: "Max temperature (°C) for the next 5 days",
    });
    const firstDay = within(chartTable).getByRole("row", { name: /Tue 10 Sep/ });
    expect(
      within(firstDay)
        .getAllByRole("cell")
        .map((c) => c.textContent),
    ).toEqual(["24.5", "26.1", "27.2", "26.8"]);

    // Rain chances in words and agro values with units, for 10 Sep.
    const chance = async (label: string) =>
      (await screen.findByText(label)).nextElementSibling?.textContent;
    expect(await chance("Rain of 1 mm or more")).toBe("likely, 91%");
    expect(await chance("Rain of 2.5 mm or more")).toBe("likely, 80%");
    expect(await chance("Heavy rain, 35 mm or more")).toBe("likely, 64%");
    expect(screen.getByText("2.3 mm a day")).toBeInTheDocument();
    expect(screen.getByText("73% of capacity")).toBeInTheDocument();
    expect(screen.getByText("50% to 73% depending on rain")).toBeInTheDocument();
    expect(screen.getByText("Thresholds pending expert review.")).toBeInTheDocument();

    // Explain: effect word next to each plain sentence.
    const reasons = await screen.findByRole("region", {
      name: "Why is it different from the block?",
    });
    expect(within(reasons).getAllByText("Cooler")).toHaveLength(2);
    expect(within(reasons).getByText("Warmer")).toBeInTheDocument();
    expect(
      within(reasons).getByText(/Less built-up land than the rest of the block/),
    ).toBeInTheDocument();
    expect(within(reasons).getByText(/-0.2 °C/)).toBeInTheDocument();

    // Changes: 1, 2.5 and 10 mm on 13 Sep collapse into one line.
    const changes = await screen.findByRole("region", { name: "Forecast changed since yesterday" });
    await within(changes).findByText("Fri 13 Sep");
    expect(changes).toHaveTextContent("Yesterday: dry (4%). Now: rain possible (54%).");
    expect(changes).toHaveTextContent(
      "Heavy rain, 35 mm or more. Yesterday: possible (48%). Now: likely (64%).",
    );
    expect(changes).toHaveTextContent("Max temperature: was 28.2 °C, now 26.1 °C");
    expect(changes).not.toHaveTextContent("Rain of 10 mm or more");
  });

  it("adds what happened, with its source, when asked", async () => {
    stubFetch();
    select("MP0305", "tmax");
    const user = userEvent.setup();
    renderWithProviders(<DetailPanel />);

    const toggle = await screen.findByRole("checkbox", { name: "Show what happened" });
    expect(screen.queryByRole("columnheader", { name: "Happened" })).not.toBeInTheDocument();
    await user.click(toggle);

    expect(await screen.findByText("Source: station MOCK_AWS_10")).toBeInTheDocument();
    const chartTable = screen.getByRole("table", {
      name: "Max temperature (°C) for the next 5 days",
    });
    await waitFor(() =>
      expect(
        within(chartTable).getByRole("columnheader", { name: "Happened" }),
      ).toBeInTheDocument(),
    );
    const firstDay = within(chartTable).getByRole("row", { name: /Tue 10 Sep/ });
    expect(within(firstDay).getAllByRole("cell").at(-1)).toHaveTextContent("26.9");
  });

  it("says so when a rain-only station has no reading for the variable", async () => {
    stubFetch({
      "observed_panchayat_MP0305.json": (j) => {
        const o = j as { days: Record<string, unknown>[]; station_id: string };
        return {
          ...o,
          station_id: "MOCK_ARG_15",
          days: o.days.map((d) => ({ ...d, tmax: null, tmin: null, rh: null, wind: null })),
        };
      },
    });
    select("MP0305", "tmax");
    const user = userEvent.setup();
    renderWithProviders(<DetailPanel />);
    await user.click(await screen.findByRole("checkbox", { name: "Show what happened" }));
    expect(
      await screen.findByText("No observed Max temperature for these days."),
    ).toBeInTheDocument();
    expect(screen.queryByRole("columnheader", { name: "Happened" })).not.toBeInTheDocument();
  });

  it("shows plain empty states for no reasons and no earlier forecast", async () => {
    stubFetch({
      "forecast_changes_MP0103.json": (j) => ({
        ...(j as object),
        previous_issue_date: null,
        changes: [],
        event_changes: [],
      }),
    });
    select("MP0103", "rain");
    renderWithProviders(<DetailPanel />);
    expect(
      await screen.findByText(
        "Nothing to explain: Rain here is about the same as the block average on this day.",
      ),
    ).toBeInTheDocument();
    expect(await screen.findByText("No earlier forecast to compare with.")).toBeInTheDocument();
  });

  it("keeps English reasons marked as English in the Hindi UI", async () => {
    stubFetch();
    const { default: i18n } = await import("i18next");
    await i18n.changeLanguage("hi");
    select("MP0305", "tmax", "hi");
    renderWithProviders(<DetailPanel />);
    const sentence = await screen.findByText(/Less built-up land than the rest of the block/);
    expect(sentence).toHaveAttribute("lang", "en");
    expect(
      screen.getByText("जब तक कोई मूल भाषी इन्हें नहीं लिखता, कारण अंग्रेज़ी में हैं।"),
    ).toBeInTheDocument();
  });

  it("switches the chart variable for the map too", async () => {
    stubFetch();
    select("MP0305", "tmax");
    const user = userEvent.setup();
    renderWithProviders(<DetailPanel />);
    const group = await screen.findByRole("group", { name: "Variable in the chart" });
    await user.click(within(group).getByRole("radio", { name: "Rain" }));
    expect(useAppStore.getState().variable).toBe("rain");
    expect(
      await screen.findByRole("table", { name: "Rain (mm) for the next 5 days" }),
    ).toBeInTheDocument();
  });
});
