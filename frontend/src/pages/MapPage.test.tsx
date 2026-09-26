import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../api/client";
import { useAppStore } from "../state/store";
import { renderWithProviders } from "../test/render";
import MapPage from "./MapPage";

// jsdom has no WebGL. The stub shows what MapView would paint, which is what this test checks.
vi.mock("../features/map/MapView", () => ({
  MapView: (props: {
    values: ReadonlyMap<string, number | null>;
    ramp: { kind: string } | null;
  }) => (
    <div
      data-testid="mapview"
      data-ramp={props.ramp?.kind ?? "none"}
      data-mp0301={String(props.values.get("MP0301"))}
    />
  ),
}));

const EXAMPLES = resolve(__dirname, "../../../contract/examples");

/** Serves /mock/* from contract/examples and counts requests per file. */
function stubFetch() {
  const counts = new Map<string, number>();
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      const file = /^\/mock\/(.+)$/.exec(url)?.[1] ?? "";
      counts.set(file, (counts.get(file) ?? 0) + 1);
      try {
        return new Response(readFileSync(resolve(EXAMPLES, file), "utf8"), { status: 200 });
      } catch {
        return new Response("not found", { status: 404 });
      }
    }),
  );
  return counts;
}

beforeEach(() => {
  clearIndexCache();
  useAppStore.setState({
    issueDate: "2024-09-09",
    leadDay: 1,
    variable: "rain",
    viewMode: "panchayat",
    selectedPid: null,
    lang: "en",
  });
});
afterEach(() => vi.unstubAllGlobals());

describe("map explorer", () => {
  it("switches Block, Panchayat and Difference views without a new request", async () => {
    const counts = stubFetch();
    const user = userEvent.setup();
    renderWithProviders(<MapPage />);

    const map = await screen.findByTestId("mapview");
    // MP0301 is in MB03, the wettest block on 10 Sep 2024: p50 101.28, block 105.78 mm.
    await waitFor(() => expect(map).toHaveAttribute("data-mp0301", "101.28"));
    expect(map).toHaveAttribute("data-ramp", "sequential");
    const before = counts.get("forecast_map_rain.json");
    expect(before).toBe(1);

    await user.click(screen.getByRole("radio", { name: "Block" }));
    expect(map).toHaveAttribute("data-mp0301", "105.78");

    await user.click(screen.getByRole("radio", { name: "Difference from block" }));
    expect(map).toHaveAttribute("data-mp0301", "-4.5");
    expect(map).toHaveAttribute("data-ramp", "diverging");

    await user.click(screen.getByRole("radio", { name: "Panchayat" }));
    expect(map).toHaveAttribute("data-mp0301", "101.28");
    expect(counts.get("forecast_map_rain.json")).toBe(before);
  });

  it("offers a sortable table that selects a Panchayat from the keyboard", async () => {
    stubFetch();
    const user = userEvent.setup();
    renderWithProviders(<MapPage />);
    await waitFor(() =>
      expect(screen.getByTestId("mapview")).toHaveAttribute("data-mp0301", "101.28"),
    );

    await user.click(screen.getByRole("button", { name: "Show as table" }));
    const table = screen.getByRole("table", { name: /Rain for every Panchayat/ });
    expect(within(table).getAllByRole("row")).toHaveLength(91); // header + 90 Panchayats

    const sortBlock = within(table).getByRole("button", {
      name: /Block forecast \(mm\): sort from low/,
    });
    sortBlock.focus();
    await user.keyboard("{Enter}");
    await user.click(
      within(table).getByRole("button", { name: /Block forecast \(mm\): sort from high/ }),
    );
    const header = within(table).getByRole("columnheader", { name: /Block forecast/ });
    expect(header).toHaveAttribute("aria-sort", "descending");

    const firstRow = within(table).getAllByRole("row")[1];
    expect(firstRow).toHaveTextContent("MB03");
    const nameButton = within(firstRow as HTMLElement).getByRole("button");
    nameButton.focus();
    await user.keyboard("{Enter}");

    expect(useAppStore.getState().selectedPid).toMatch(/^MP03/);
    const panel = screen.getByRole("complementary", { name: "Selected Panchayat" });
    expect(await within(panel).findByText("101.3 mm")).toBeInTheDocument();
    expect(within(panel).getByText("likely between 40 and 193.2 mm")).toBeInTheDocument();
    expect(within(panel).getByText("-4.5 mm")).toBeInTheDocument();
  });

  it("keeps the risk layer selector visible but disabled with a reason", async () => {
    stubFetch();
    renderWithProviders(<MapPage />);
    const risk = await screen.findByRole("combobox", { name: "Risk layer" });
    expect(risk).toBeDisabled();
    expect(risk).toHaveAccessibleDescription(/Not connected yet/);
  });
});
