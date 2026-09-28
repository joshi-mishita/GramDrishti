import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { Route, Routes } from "react-router-dom";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { clearIndexCache } from "../../api/client";
import { applyLang } from "../../i18n";
import { useAppStore } from "../../state/store";
import { renderWithProviders } from "../../test/render";
import BulletinPage from "../BulletinPage";
import FarmerFarm from "./FarmerFarm";
import FarmerForecast from "./FarmerForecast";
import FarmerToday from "./FarmerToday";

const EXAMPLES = resolve(__dirname, "../../../../contract/examples");

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

function renderAt(route: string) {
  return renderWithProviders(
    <Routes>
      <Route path="/farmer" element={<FarmerToday />} />
      <Route path="/farmer/forecast" element={<FarmerForecast />} />
      <Route path="/farmer/farm" element={<FarmerFarm />} />
      <Route path="/bulletin/:pid" element={<BulletinPage />} />
    </Routes>,
    { route },
  );
}

beforeEach(() => {
  clearIndexCache();
  stubFetch();
  useAppStore.setState({ issueDate: "2024-09-09", lang: "en", farmerId: "F001" });
});
afterEach(() => {
  vi.unstubAllGlobals();
  applyLang("en");
});

describe("farmer Today", () => {
  it("shows the most urgent approved advisory in full and the rest as a list", async () => {
    renderAt("/farmer");
    const hero = await screen.findByRole("heading", { level: 2, name: /Do not spray/ });
    const block = hero.closest("article") as HTMLElement;
    expect(block).toHaveTextContent("Spray · Bajra · For Tue 10 Sep to Wed 11 Sep");
    // One-line reason: the first sentence only, the rest behind "Why, and what if".
    expect(within(block).getByText("Rain or wind would waste the spray.")).toBeInTheDocument();
    expect(within(block).getByText("Likely")).toBeInTheDocument();
    expect(within(block).getByRole("button", { name: "Listen" })).toBeInTheDocument();
    const share = within(block).getByRole("link", { name: "Share on WhatsApp" });
    const text = decodeURIComponent(share.getAttribute("href")?.split("text=")[1] ?? "");
    expect(text).toContain("Do not spray pesticide");
    expect(text).toContain("Synthetic demo data. Not real weather.");
    expect(screen.getByRole("heading", { name: "Also today (2)" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Village bulletin/ })).toHaveAttribute(
      "href",
      "/bulletin/MP0307?date=2024-09-09&lang=en",
    );
  });

  it("uses the API's Hindi text and Hindi UI words", async () => {
    useAppStore.setState({ lang: "hi" });
    applyLang("hi");
    renderAt("/farmer");
    const hero = await screen.findByRole("heading", { level: 2, name: /छिड़काव न करें/ });
    expect(hero).toHaveAttribute("lang", "hi");
    expect(screen.getAllByRole("button", { name: "सुनें" })).toHaveLength(3);
  });

  it("says so when a farmer has no advice today", async () => {
    useAppStore.setState({ farmerId: "F005" });
    renderAt("/farmer");
    expect(await screen.findByText("No advice for your crops today")).toBeInTheDocument();
  });
});

describe("farmer Forecast", () => {
  it("lists five days with rain words and mm, temperature, wind and spray words", async () => {
    renderAt("/farmer/forecast");
    const days = await screen.findAllByRole("listitem");
    expect(days).toHaveLength(5);
    const first = days[0] as HTMLElement;
    expect(first).toHaveTextContent("Tue 10 Sep");
    expect(first).toHaveTextContent(/Likely, about \d+ mm, could reach \d+ mm/);
    expect(first).toHaveTextContent(/\d+ to \d+ °C/);
    expect(first).toHaveTextContent(/\d+ km\/h/);
    expect(first).toHaveTextContent("AvoidDo not spray");
    expect(screen.getByText(/whole day, not for hours/)).toBeInTheDocument();
  });
});

describe("farmer My farm", () => {
  it("edits crops in local state only and says so", async () => {
    const user = userEvent.setup();
    renderAt("/farmer/farm");
    expect(await screen.findByText("MB03")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Change crops" }));
    expect(screen.getByText(/not saved or sent in this prototype/)).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Add crop" }));
    expect(screen.getAllByLabelText("Crop")).toHaveLength(4);
    await user.click(screen.getByRole("button", { name: "Done" }));
    expect(screen.getByText("Changed on this phone, not saved")).toBeInTheDocument();
  });

  it("asks about rain and explains that demo files cannot store the answer", async () => {
    const user = userEvent.setup();
    renderAt("/farmer/farm");
    await user.click(await screen.findByRole("button", { name: "Yes" }));
    await user.click(screen.getByRole("button", { name: "Heavy" }));
    expect(await screen.findByText(/your answer was not sent/)).toBeInTheDocument();
  });
});

describe("bulletin", () => {
  it("prints place, date, three days, approved actions with reasons and the mock notice", async () => {
    renderAt("/bulletin/MP0307?date=2024-09-09&lang=en");
    expect(
      await screen.findByRole("heading", {
        level: 1,
        name: "Synthetic Panchayat MP0307, block MB03",
      }),
    ).toBeInTheDocument();
    const table = screen.getByRole("table");
    expect(within(table).getAllByRole("columnheader")).toHaveLength(4); // label + 3 days
    const actions = await screen.findAllByText(/^Why: /);
    expect(actions.length).toBeGreaterThan(0);
    expect(actions.length).toBeLessThanOrEqual(4);
    expect(screen.getByText(/reviewed by an agriculture officer/)).toBeInTheDocument();
    expect(screen.getByText("Synthetic demo data. Not real weather.")).toBeInTheDocument();
  });

  it("uses the language from ?lang= without changing the app language", async () => {
    renderAt("/bulletin/MP0307?date=2024-09-09&lang=pa");
    expect(await screen.findByText("ਅਗਲੇ 3 ਦਿਨ")).toBeInTheDocument();
    await waitFor(() => expect(screen.getAllByText(/^ਕਿਉਂ: /).length).toBeGreaterThan(0));
    expect(screen.getByRole("button", { name: "Print" })).toBeInTheDocument();
    expect(useAppStore.getState().lang).toBe("en");
  });
});
