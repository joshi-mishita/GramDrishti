import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes, useLocation } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../api/client";
import { useAppStore } from "../state/store";
import { renderWithProviders } from "../test/render";
import PriorityPage from "./PriorityPage";

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

function MapProbe() {
  const { search } = useLocation();
  return <p data-testid="map-probe">{search}</p>;
}

function renderPage(route = "/priority") {
  return renderWithProviders(
    <Routes>
      <Route path="/priority" element={<PriorityPage />} />
      <Route path="/map" element={<MapProbe />} />
    </Routes>,
    { route },
  );
}

beforeEach(() => {
  clearIndexCache();
  stubFetch();
  useAppStore.setState({ issueDate: "2024-09-09", lang: "en" });
});
afterEach(() => vi.unstubAllGlobals());

describe("priority screen", () => {
  it("ranks every Panchayat needing attention with level chips and headlines", async () => {
    renderPage();
    const table = await screen.findByRole("table", { name: /Panchayats needing attention/ });
    const rows = within(table).getAllByRole("row");
    expect(rows).toHaveLength(75); // header + 74 items in priority.json
    const first = rows[1] as HTMLElement;
    expect(first).toHaveTextContent("MP0301");
    expect(first).toHaveTextContent("Heavy rain");
    expect(first).toHaveTextContent("Severe");
    expect(first).toHaveTextContent("Cotton");
    expect(first).toHaveTextContent("64% chance of 35 mm or more");
    expect(screen.getByText("74 Panchayats at moderate level or above.")).toBeInTheDocument();
    expect(screen.getByText("Thresholds pending expert review.")).toBeInTheDocument();
  });

  it("filters by risk type and block, keeping the rank, and can clear the filters", async () => {
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("table", { name: /Panchayats needing attention/ });

    // priority.json (2024-09-09): 32 heavy rain in MB03 and MB05, 42 dry spell elsewhere.
    await user.selectOptions(screen.getByRole("combobox", { name: "Type" }), "Heavy rain");
    const table = screen.getByRole("table", { name: /Panchayats needing attention/ });
    const rows = within(table).getAllByRole("row").slice(1);
    expect(rows).toHaveLength(32);
    for (const r of rows) expect(r).toHaveTextContent("Heavy rain");
    expect(within(rows[0] as HTMLElement).getAllByRole("cell")[0]).toHaveTextContent(/^1$/);
    expect(screen.getByText("32 of 74 Panchayats match these filters.")).toBeInTheDocument();

    await user.selectOptions(screen.getByRole("combobox", { name: "Block" }), "MB05");
    expect(within(table).getAllByRole("row")).toHaveLength(17);

    await user.selectOptions(screen.getByRole("combobox", { name: "Block" }), "MB01");
    expect(screen.getByText("No Panchayat matches these filters")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Clear filters" }));
    expect(await screen.findByText("74 Panchayats at moderate level or above.")).toBeVisible();
  });

  it("sorts by a column and asks for another horizon", async () => {
    const user = userEvent.setup();
    renderPage();
    const table = await screen.findByRole("table", { name: /Panchayats needing attention/ });
    await user.click(within(table).getByRole("button", { name: /Block: sort from low/ }));
    expect(within(table).getAllByRole("row")[1]).toHaveTextContent("MB01");

    // The demo files only hold the 2-day horizon: 3 days is a clear empty state, not an error.
    await user.selectOptions(screen.getByRole("combobox", { name: "Next" }), "3 days");
    expect(
      await screen.findByText("No demo file for the priority list with these settings"),
    ).toBeInTheDocument();
  });

  it("opens the map at the Panchayat with its risk layer when a row is clicked", async () => {
    const user = userEvent.setup();
    renderPage();
    const table = await screen.findByRole("table", { name: /Panchayats needing attention/ });
    const first = within(table).getAllByRole("row")[1] as HTMLElement;
    await user.click(within(first).getByText("Heavy rain"));
    const probe = await screen.findByTestId("map-probe");
    const q = new URLSearchParams(probe.textContent ?? "");
    expect(q.get("pid")).toBe("MP0301");
    expect(q.get("risk")).toBe("heavy_rain");
    expect(q.get("var")).toBe("rain");
    expect(q.get("date")).toBe("2024-09-09");
  });

  it("offers a print button", async () => {
    const print = vi.fn();
    vi.stubGlobal("print", print);
    const user = userEvent.setup();
    renderPage();
    await screen.findByRole("table", { name: /Panchayats needing attention/ });
    await user.click(screen.getByRole("button", { name: "Print list" }));
    await waitFor(() => expect(print).toHaveBeenCalledOnce());
  });
});
