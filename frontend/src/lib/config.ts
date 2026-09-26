/** Runtime configuration from Vite env variables. See .env.example. */

export interface ClientConfig {
  /** Base URL of the real API, for example "/api/v1" or "http://localhost:8000/api/v1". */
  apiBase: string;
  /** Endpoint groups served by the real API; everything else reads mock files. */
  realEndpoints: ReadonlySet<string>;
  /** When true, every request reads /snapshot/ and the server is never called. */
  snapshot: boolean;
}

/** Parses a comma-separated env value into a set of trimmed, non-empty items. */
export function parseList(value: string | undefined): Set<string> {
  return new Set(
    (value ?? "")
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean),
  );
}

export const config: ClientConfig = {
  apiBase: import.meta.env.VITE_API_BASE || "/api/v1",
  realEndpoints: parseList(import.meta.env.VITE_REAL_ENDPOINTS),
  snapshot: import.meta.env.VITE_SNAPSHOT === "1",
};

/** Issue date opened when the URL has none. The main demo date of contract v0.1.1. */
export const DEFAULT_ISSUE_DATE = import.meta.env.VITE_DEFAULT_ISSUE_DATE || "2024-09-09";

/** Demo farmer shown in the farmer app. There is no login in the prototype. */
export const DEMO_FARMER_ID = "F001";

/** Lead days offered by the forecast (Appendix A: 5-day detail). */
export const LEAD_DAYS = [1, 2, 3, 4, 5] as const;
