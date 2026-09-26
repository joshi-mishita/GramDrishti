import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { ClientConfig } from "../lib/config";
import {
  apiGet,
  buildQuery,
  clearIndexCache,
  groupOf,
  requestKey,
  setRequestRole,
  sourceFor,
} from "./client";
import { ApiError } from "./errors";

const EXAMPLES = resolve(__dirname, "../../../contract/examples");

const cfg = (real: string[] = [], snapshot = false): ClientConfig => ({
  apiBase: "http://api.test/api/v1",
  realEndpoints: new Set(real),
  snapshot,
});

/** Serves /mock/* and /snapshot/* from contract/examples; records other calls. */
function stubFetch(apiResponse?: () => Response) {
  const calls: { url: string; init?: RequestInit }[] = [];
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string, init?: RequestInit) => {
      calls.push({ url, init });
      const m = /^\/(mock|snapshot)\/(.+)$/.exec(url);
      if (m) {
        try {
          return new Response(readFileSync(resolve(EXAMPLES, m[2] ?? ""), "utf8"), { status: 200 });
        } catch {
          return new Response("not found", { status: 404 });
        }
      }
      return apiResponse ? apiResponse() : new Response("{}", { status: 200 });
    }),
  );
  return calls;
}

beforeEach(() => clearIndexCache());
afterEach(() => vi.unstubAllGlobals());

describe("routing between real, mock and snapshot", () => {
  it("finds the endpoint group from the path", () => {
    expect(groupOf("/forecast/map")).toBe("forecast");
    expect(groupOf("/forecast/changes/MP0103")).toBe("forecast");
    expect(groupOf("/data-quality")).toBe("data-quality");
    expect(groupOf("/meta")).toBe("meta");
  });

  it("uses the real API only for listed groups, and never in snapshot mode", () => {
    expect(sourceFor("meta", cfg())).toBe("mock");
    expect(sourceFor("meta", cfg(["meta", "geo"]))).toBe("real");
    expect(sourceFor("forecast", cfg(["meta", "geo"]))).toBe("mock");
    expect(sourceFor("meta", cfg(["meta"], true))).toBe("snapshot");
  });

  it("drops empty params and sorts for matching", () => {
    expect(buildQuery({ b: 2, a: "x", c: null, d: undefined, e: "" })).toBe("?b=2&a=x");
    expect(requestKey("/p", { b: 2, a: "x" })).toBe("/p?a=x&b=2");
  });
});

describe("mock files", () => {
  it("serves the example that matches the request, whatever the param order", async () => {
    stubFetch();
    const map = await apiGet<{ var: string; issue_date: string }>(
      "/forecast/map",
      { var: "rain", lead_day: 1, issue_date: "2024-09-09" },
      cfg(),
    );
    expect(map.var).toBe("rain");
    expect(map.issue_date).toBe("2024-09-09");
  });

  it("refuses to serve another date's file and names the dates that exist", async () => {
    stubFetch();
    const err = await apiGet(
      "/forecast/map",
      { issue_date: "2024-01-12", lead_day: 1, var: "rain" },
      cfg(),
    ).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).code).toBe("not_in_mock");
    expect((err as ApiError).mockDates).toEqual(["2024-09-09"]);
  });

  it("replays error examples as errors in the contract shape", async () => {
    stubFetch();
    const err = await apiGet(
      "/forecast/panchayat/MP9999",
      { issue_date: "2024-09-09" },
      cfg(),
    ).catch((e: unknown) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect((err as ApiError).status).toBe(404);
    expect((err as ApiError).code).toBe("not_found");
  });

  it("reads snapshot files from /snapshot in snapshot mode", async () => {
    const calls = stubFetch();
    await apiGet("/meta", {}, cfg(["meta"], true));
    expect(calls.map((c) => c.url)).toEqual(["/snapshot/index.json", "/snapshot/meta.json"]);
  });

  it("every GET example in index.json resolves and carries data_mode", async () => {
    stubFetch();
    const index = JSON.parse(readFileSync(resolve(EXAMPLES, "index.json"), "utf8")) as {
      files: { file: string; method: string; path: string; status: number | null }[];
    };
    const gets = index.files.filter((f) => f.method === "GET" && f.status === 200);
    expect(gets.length).toBeGreaterThan(40);
    for (const f of gets) {
      const url = new URL(f.path, "http://x");
      const path = url.pathname.replace(/^\/api\/v1/, "");
      const body = await apiGet<{ data_mode?: string }>(
        path,
        Object.fromEntries(url.searchParams),
        cfg(),
      );
      expect(body.data_mode, f.file).toBe("mock");
    }
  });
});

describe("real API", () => {
  it("calls the base URL with the query and the X-Role header", async () => {
    const calls = stubFetch(() => new Response('{"district":"x"}', { status: 200 }));
    setRequestRole("farmer");
    await apiGet("/meta", {}, cfg(["meta"]));
    await apiGet("/priority", { issue_date: "2024-09-09", horizon_days: 2 }, cfg(["priority"]));
    expect(calls[0]?.url).toBe("http://api.test/api/v1/meta");
    expect(calls[1]?.url).toBe(
      "http://api.test/api/v1/priority?issue_date=2024-09-09&horizon_days=2",
    );
    expect((calls[0]?.init?.headers as Record<string, string>)["X-Role"]).toBe("farmer");
    setRequestRole("officer");
  });

  it("turns a contract error body into an ApiError", async () => {
    stubFetch(
      () =>
        new Response('{"error":{"code":"issue_date_not_available","message":"No forecast"}}', {
          status: 404,
        }),
    );
    const err = await apiGet("/meta", {}, cfg(["meta"])).catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("issue_date_not_available");
    expect((err as ApiError).message).toBe("No forecast");
  });

  it("reports a network failure as network_error", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new TypeError("Failed to fetch");
      }),
    );
    const err = await apiGet("/meta", {}, cfg(["meta"])).catch((e: unknown) => e);
    expect((err as ApiError).code).toBe("network_error");
    expect((err as ApiError).status).toBe(0);
  });
});
