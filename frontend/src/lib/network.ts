/**
 * Online state and "served from the offline copy" bookkeeping (Frontend Guide 10.2).
 *
 * The service worker (src/sw.ts) answers GET requests network first. When it has to fall
 * back to its cache it adds two headers: X-GD-From-Cache: 1 and X-GD-Fetched-At (when the
 * copy was stored). The API client reports every response here, so a screen can say
 * "Last updated ..." whenever what it shows is an offline copy.
 */
import { useSyncExternalStore } from "react";
import { create } from "zustand";

export const FROM_CACHE_HEADER = "X-GD-From-Cache";
export const FETCHED_AT_HEADER = "X-GD-Fetched-At";

interface CacheState {
  /** Request URL -> time its offline copy was stored; only URLs last served from cache. */
  cached: Record<string, string>;
  note: (url: string, fetchedAt: string | null) => void;
}

export const useCacheStore = create<CacheState>()((set) => ({
  cached: {},
  note: (url, fetchedAt) =>
    set((s) => {
      if (fetchedAt === null) {
        if (!(url in s.cached)) return s;
        return { cached: Object.fromEntries(Object.entries(s.cached).filter(([k]) => k !== url)) };
      }
      if (s.cached[url] === fetchedAt) return s;
      return { cached: { ...s.cached, [url]: fetchedAt } };
    }),
}));

/** Records where a response came from. Called by the API client for every response. */
export function noteResponse(url: string, headers: Headers): void {
  const fromCache = headers.get(FROM_CACHE_HEADER) === "1";
  const at = headers.get(FETCHED_AT_HEADER);
  useCacheStore.getState().note(url, fromCache ? (at ?? "") : null);
}

/**
 * The oldest stored time among the responses currently shown from the offline copy, or
 * null when everything came from the network. An empty string means "from the offline
 * copy, time unknown".
 */
export function oldestCached(cached: Record<string, string>): string | null {
  const times = Object.values(cached);
  if (times.length === 0) return null;
  const known = times.filter(Boolean).sort();
  return known[0] ?? "";
}

export const useLastUpdated = () => useCacheStore((s) => oldestCached(s.cached));

function subscribe(onChange: () => void): () => void {
  window.addEventListener("online", onChange);
  window.addEventListener("offline", onChange);
  return () => {
    window.removeEventListener("online", onChange);
    window.removeEventListener("offline", onChange);
  };
}

/** True while the browser reports a network connection. */
export function useOnline(): boolean {
  return useSyncExternalStore(
    subscribe,
    () => navigator.onLine,
    () => true,
  );
}
