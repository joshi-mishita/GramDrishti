import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { Advisory, AdvisoryList, ReviewRequest } from "../api/types";
import { clearIndexCache } from "../api/client";
import { useAppStore } from "../state/store";
import { renderWithProviders } from "../test/render";
import ReviewPage from "./ReviewPage";

// Advisories come from a stubbed "real" API so that reviews can be sent; everything else
// (geo, meta) from the demo files.
vi.mock("../lib/config", async (orig) => {
  const mod = await orig<typeof import("../lib/config")>();
  return {
    ...mod,
    config: { ...mod.config, apiBase: "/api/v1", realEndpoints: new Set(["advisories"]) },
  };
});

const EXAMPLES = resolve(__dirname, "../../../contract/examples");
const read = <T,>(f: string) => JSON.parse(readFileSync(resolve(EXAMPLES, f), "utf8")) as T;

/** A tiny in-memory advisories API: GET list, GET one, POST review. */
function stubApi() {
  const store = new Map(read<AdvisoryList>("advisories.json").items.map((a) => [a.id, a]));
  const calls: { method: string; url: string; body?: ReviewRequest }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      const method = init?.method ?? "GET";
      const body = init?.body ? (JSON.parse(String(init.body)) as ReviewRequest) : undefined;
      calls.push({ method, url, body });
      const mock = /^\/mock\/(.+)$/.exec(url)?.[1];
      if (mock) {
        try {
          return new Response(readFileSync(resolve(EXAMPLES, mock), "utf8"));
        } catch {
          return new Response("not found", { status: 404 });
        }
      }
      const u = new URL(url, "http://x");
      const review = /^\/api\/v1\/advisories\/([^/]+)\/review$/.exec(u.pathname);
      if (review && body) {
        const a = store.get(decodeURIComponent(review[1] ?? "")) as Advisory;
        const status = { approve: "approved", edit: "edited", reject: "rejected" } as const;
        const next: Advisory = {
          ...a,
          ...(body.edited?.action ? { action: body.edited.action } : {}),
          status: status[body.action],
          reviewed_by: body.reviewer,
          reviewed_at: "2026-09-27T10:30:00",
          audit: [
            ...a.audit,
            {
              at: "2026-09-27T10:30:00",
              actor: body.reviewer,
              action: status[body.action],
              note: body.note ?? "",
              before: body.edited?.action
                ? { action: a.action, status: a.status }
                : { status: a.status },
              after: body.edited?.action
                ? { action: body.edited.action, status: status[body.action] }
                : { status: status[body.action] },
            },
          ],
        };
        store.set(a.id, next);
        return new Response(JSON.stringify(next));
      }
      const one = /^\/api\/v1\/advisories\/([^/]+)$/.exec(u.pathname);
      if (one) return new Response(JSON.stringify(store.get(decodeURIComponent(one[1] ?? ""))));
      if (u.pathname === "/api/v1/advisories") {
        const s = u.searchParams.get("status");
        const items = [...store.values()].filter((a) => !s || a.status === s);
        return new Response(
          JSON.stringify({ data_mode: "mock", provenance: "computed", total: items.length, items }),
        );
      }
      return new Response("{}", { status: 404 });
    }),
  );
  return calls;
}

const ID = "ADV-2024-09-09-MP0301-cotton-spray";

beforeEach(() => {
  clearIndexCache();
  try {
    localStorage.removeItem("gramdrishti.reviewer");
  } catch {
    // jsdom storage can be missing; the default reviewer is used then.
  }
  useAppStore.setState({ issueDate: "2024-09-09", lang: "en" });
});
afterEach(() => vi.unstubAllGlobals());

describe("review screen", () => {
  it("lists drafts, filters them and opens one with its evidence and notes", async () => {
    stubApi();
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />, { route: "/review" });
    const list = await screen.findByRole("listbox", { name: "Waiting for review (198)" });
    expect(within(list).getAllByRole("option")).toHaveLength(198);

    await user.selectOptions(screen.getByRole("combobox", { name: "Crop" }), "Cotton");
    await user.selectOptions(screen.getByRole("combobox", { name: "Block" }), "MB03");
    const filtered = within(list).getAllByRole("option");
    expect(filtered.length).toBeGreaterThan(0);
    for (const o of filtered) expect(o).toHaveTextContent("Cotton");

    await user.click(within(list).getByText(/MP0301/));
    const editor = await screen.findByRole("article");
    expect(within(editor).getByRole("heading", { level: 2 })).toHaveTextContent(
      "Spray: Cotton, boll development and picking",
    );
    expect(within(editor).getByText("Thresholds pending expert review.")).toBeInTheDocument();
    expect(within(editor).getByText(/need review by a native speaker/)).toBeInTheDocument();
    expect(within(editor).getByText("Likely")).toBeInTheDocument();
    expect(
      within(editor).getByText("Chance of 2.5 mm or more of rain on 10 Sep"),
    ).toBeInTheDocument();
    expect(within(editor).getByText(/Drafted/)).toBeInTheDocument();
  });

  it("edits the English text, saves and approves, and shows it in the toast and history", async () => {
    const calls = stubApi();
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />, { route: `/review?adv=${ID}` });
    const editor = await screen.findByRole("article");

    const approve = within(editor).getByRole("button", { name: "Approve" });
    const save = within(editor).getByRole("button", { name: "Save edit and approve" });
    expect(approve).toBeEnabled();
    expect(save).toBeDisabled();

    const action = within(editor).getByRole("textbox", { name: /Action/ });
    await user.clear(action);
    await user.type(action, "No spraying on 10 September.");
    expect(within(editor).getByRole("tab", { name: /English.*changed/ })).toBeInTheDocument();
    expect(approve).toBeDisabled();
    expect(save).toBeEnabled();

    // Hindi still holds the old text, which saving would clear: the editor says so.
    await user.click(within(editor).getByRole("tab", { name: /हिन्दी/ }));
    expect(within(editor).getAllByText(/this translation will be cleared/).length).toBe(1);

    const listGets = () =>
      calls.filter((c) => c.method === "GET" && c.url.startsWith("/api/v1/advisories?")).length;
    const before = listGets();
    await user.click(save);

    expect(await screen.findByText(`Edited and approved: MP0301 Cotton Spray`)).toBeInTheDocument();
    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toEqual({
      action: "edit",
      reviewer: "Demo officer",
      note: "",
      edited: { action: { en: "No spraying on 10 September.", hi: null, pa: null } },
    });
    const updated = await screen.findByRole("article");
    expect(within(updated).getAllByText("Edited and approved").length).toBeGreaterThan(1);
    expect(within(updated).getByText("by Demo officer")).toBeInTheDocument();
    // The queue refetches, and the reviewed draft leaves it.
    await waitFor(() => expect(listGets()).toBeGreaterThan(before));
    expect(
      await screen.findByRole("listbox", { name: "Waiting for review (197)" }),
    ).toBeInTheDocument();
    // Approving again without a change is not offered.
    expect(within(updated).getByRole("button", { name: "Approve" })).toBeDisabled();
  });

  it("moves with arrow keys, opens with Enter and approves with Ctrl+Enter", async () => {
    const calls = stubApi();
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />, { route: "/review" });
    const list = await screen.findByRole("listbox", { name: /Waiting for review/ });
    list.focus();
    await user.keyboard("{ArrowDown}{ArrowDown}");
    const second = within(list).getAllByRole("option")[1] as HTMLElement;
    expect(list).toHaveAttribute("aria-activedescendant", second.id);
    await user.keyboard("{Enter}");
    expect(second).toHaveAttribute("aria-selected", "true");
    await screen.findByRole("article");

    await user.keyboard("{Control>}{Enter}{/Control}");
    expect(await screen.findByText(/^Approved: /)).toBeInTheDocument();
    expect(calls.filter((c) => c.method === "POST").map((c) => c.body?.action)).toEqual([
      "approve",
    ]);
  });

  it("rejects only with a reason, which is saved as the note", async () => {
    const calls = stubApi();
    const user = userEvent.setup();
    renderWithProviders(<ReviewPage />, { route: `/review?adv=${ID}` });
    const editor = await screen.findByRole("article");
    await user.click(within(editor).getByRole("button", { name: "Reject" }));
    const confirm = within(editor).getByRole("button", { name: "Reject" });
    expect(confirm).toBeDisabled();
    await user.type(
      within(editor).getByRole("textbox", { name: /Reason for rejecting/ }),
      "Cotton here is already picked",
    );
    await user.click(confirm);
    expect(await screen.findByText("Rejected: MP0301 Cotton Spray")).toBeInTheDocument();
    expect(calls.find((c) => c.method === "POST")?.body).toEqual({
      action: "reject",
      reviewer: "Demo officer",
      note: "Cotton here is already picked",
    });
  });
});
