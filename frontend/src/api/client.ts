/**
 * API client with a per-endpoint mock switch (Frontend Guide 9.1, Appendix B1.4).
 *
 * - Groups listed in VITE_REAL_ENDPOINTS go to the real API.
 * - Everything else reads public/mock/, a copy of contract/examples/.
 * - VITE_SNAPSHOT=1 reads public/snapshot/ only and never calls the server.
 *
 * Mock and snapshot requests are resolved through the folder's index.json, which maps
 * every example file to the exact request that produced it. A request with no file
 * fails with code "not_in_mock" instead of returning data for another date.
 */
import { config as defaultConfig, type ClientConfig } from "../lib/config";
import { ApiError } from "./errors";

/** First path segment of an endpoint; the unit that VITE_REAL_ENDPOINTS switches. */
export type EndpointGroup =
  | "health"
  | "meta"
  | "geo"
  | "forecast"
  | "observed"
  | "explain"
  | "risk"
  | "priority"
  | "advisories"
  | "audio"
  | "farmers"
  | "feedback"
  | "verification"
  | "impact"
  | "data-quality";

export type Source = "real" | "mock" | "snapshot";

export type QueryParams = Record<string, string | number | null | undefined>;

interface IndexEntry {
  file: string;
  method: string;
  path: string;
  status: number | null;
}

interface MockIndex {
  files: IndexEntry[];
}

const MOCK_ROOT = "/mock";
const SNAPSHOT_ROOT = "/snapshot";
const API_PREFIX = "/api/v1";

let requestRole = "officer";

/** Sets the X-Role header sent to the real API (logging only; there is no auth). */
export function setRequestRole(role: string): void {
  requestRole = role;
}

/** Returns the endpoint group of a path such as "/forecast/map" -> "forecast". */
export function groupOf(path: string): EndpointGroup {
  const seg = path.replace(/^\/+/, "").split(/[/?]/)[0] ?? "";
  return seg as EndpointGroup;
}

/** Decides where a request for this group is served from. */
export function sourceFor(group: EndpointGroup, cfg: ClientConfig = defaultConfig): Source {
  if (cfg.snapshot) return "snapshot";
  return cfg.realEndpoints.has(group) ? "real" : "mock";
}

/** Serialises query params, dropping null, undefined and empty values. */
export function buildQuery(params: QueryParams = {}, sort = false): string {
  const entries = Object.entries(params).filter(
    (e): e is [string, string | number] => e[1] !== null && e[1] !== undefined && e[1] !== "",
  );
  if (sort) entries.sort(([a], [b]) => a.localeCompare(b));
  const qs = new URLSearchParams(entries.map(([k, v]) => [k, String(v)])).toString();
  return qs ? `?${qs}` : "";
}

/** Canonical key for matching a request against index.json: path plus sorted query. */
export function requestKey(path: string, params: QueryParams = {}): string {
  return path + buildQuery(params, true);
}

function keyFromIndexPath(indexPath: string): string {
  const url = new URL(indexPath, "http://x");
  const path = url.pathname.startsWith(API_PREFIX)
    ? url.pathname.slice(API_PREFIX.length)
    : url.pathname;
  return requestKey(path, Object.fromEntries(url.searchParams));
}

const indexCache = new Map<string, Promise<Map<string, IndexEntry>>>();

async function loadIndex(root: string): Promise<Map<string, IndexEntry>> {
  let cached = indexCache.get(root);
  if (!cached) {
    cached = fetchJson<MockIndex>(`${root}/index.json`).then((idx) => {
      const map = new Map<string, IndexEntry>();
      for (const e of idx.files) {
        if (e.method === "GET" && e.status !== null) map.set(keyFromIndexPath(e.path), e);
      }
      return map;
    });
    cached.catch(() => indexCache.delete(root));
    indexCache.set(root, cached);
  }
  return cached;
}

/** Issue dates that have a file for this path in the index (to explain a missing file). */
function datesForPath(index: Map<string, IndexEntry>, path: string): string[] {
  const dates = new Set<string>();
  for (const key of index.keys()) {
    const url = new URL(key, "http://x");
    const date = url.searchParams.get("issue_date");
    if (url.pathname === path && date) dates.add(date);
  }
  return [...dates].sort();
}

async function fetchJson<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (e) {
    throw new ApiError({
      status: 0,
      url,
      code: "network_error",
      message: e instanceof Error ? e.message : "Network error",
    });
  }
  const body: unknown = await res.json().catch(() => undefined);
  if (!res.ok) throw ApiError.fromBody(res.status, url, body ?? null);
  if (body === undefined) {
    throw new ApiError({
      status: res.status,
      url,
      code: "bad_response",
      message: "Response is not JSON",
    });
  }
  return body as T;
}

async function getFromFiles<T>(root: string, path: string, params: QueryParams): Promise<T> {
  const index = await loadIndex(root);
  const entry = index.get(requestKey(path, params));
  const url = `${root}${requestKey(path, params)}`;
  if (!entry) {
    throw new ApiError({
      status: 404,
      url,
      code: "not_in_mock",
      message: `No demo file for GET ${requestKey(path, params)}`,
      mockDates: datesForPath(index, path),
    });
  }
  const fileUrl = `${root}/${entry.file}`;
  if (entry.status !== 200) {
    // Error examples replay as errors, exactly like the API would answer.
    const body = await fetch(fileUrl).then((r) => r.json() as Promise<unknown>);
    throw ApiError.fromBody(entry.status ?? 500, url, body);
  }
  return fetchJson<T>(fileUrl);
}

/**
 * GET an endpoint. `path` is relative to the API base, for example "/forecast/map".
 * Throws ApiError on any failure.
 */
export async function apiGet<T>(
  path: string,
  params: QueryParams = {},
  cfg: ClientConfig = defaultConfig,
  signal?: AbortSignal,
): Promise<T> {
  const source = sourceFor(groupOf(path), cfg);
  if (source === "real") {
    return fetchJson<T>(cfg.apiBase + path + buildQuery(params), {
      headers: { Accept: "application/json", "X-Role": requestRole },
      signal,
    });
  }
  return getFromFiles<T>(source === "snapshot" ? SNAPSHOT_ROOT : MOCK_ROOT, path, params);
}

/** Test helper: forget cached index files. */
export function clearIndexCache(): void {
  indexCache.clear();
}
