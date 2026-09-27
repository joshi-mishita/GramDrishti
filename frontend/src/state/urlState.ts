/** Pure helpers that map the URL query to the mirrored part of the store and back. */
import { RISK_TYPES, VARS, type RiskType, type Var } from "../api/types";
import { LEAD_DAYS } from "../lib/config";
import { isIsoDate } from "../lib/format";
import type { ViewMode } from "./store";

export interface UrlState {
  issueDate: string | null;
  variable: Var | null;
  selectedPid: string | null;
  leadDay: number | null;
  viewMode: ViewMode | null;
  riskType: RiskType | null;
}

export type MirroredState = {
  issueDate: string | null;
  variable: Var;
  selectedPid: string | null;
  leadDay: number;
  viewMode: ViewMode;
  riskType: RiskType | null;
};

export const URL_KEYS = {
  issueDate: "date",
  variable: "var",
  selectedPid: "pid",
  leadDay: "day",
  viewMode: "view",
  riskType: "risk",
} as const;

/** Day and view are written only when they differ from these, to keep links short. */
export const URL_DEFAULTS = { leadDay: 1, viewMode: "panchayat" } as const;

const PID = /^[A-Za-z0-9_-]{1,32}$/;
const VIEW_MODES: readonly ViewMode[] = ["block", "panchayat", "delta"];

/** Reads date, var, pid, day, view and risk from a query string. Invalid values read as null. */
export function readUrlState(search: string): UrlState {
  const q = new URLSearchParams(search);
  const date = q.get(URL_KEYS.issueDate);
  const v = q.get(URL_KEYS.variable);
  const pid = q.get(URL_KEYS.selectedPid);
  const day = Number(q.get(URL_KEYS.leadDay));
  const view = q.get(URL_KEYS.viewMode);
  const risk = q.get(URL_KEYS.riskType);
  return {
    issueDate: date && isIsoDate(date) ? date : null,
    variable: v && VARS.includes(v as Var) ? (v as Var) : null,
    selectedPid: pid && PID.test(pid) ? pid : null,
    leadDay: (LEAD_DAYS as readonly number[]).includes(day) ? day : null,
    viewMode: view && VIEW_MODES.includes(view as ViewMode) ? (view as ViewMode) : null,
    riskType: risk && RISK_TYPES.includes(risk as RiskType) ? (risk as RiskType) : null,
  };
}

/** Returns the query string with the mirrored state set; other keys are kept. */
export function writeUrlState(search: string, state: MirroredState): string {
  const q = new URLSearchParams(search);
  const put = (key: string, value: string | null) => {
    if (value) q.set(key, value);
    else q.delete(key);
  };
  put(URL_KEYS.issueDate, state.issueDate);
  put(URL_KEYS.variable, state.variable);
  put(URL_KEYS.selectedPid, state.selectedPid);
  put(URL_KEYS.leadDay, state.leadDay === URL_DEFAULTS.leadDay ? null : String(state.leadDay));
  put(URL_KEYS.viewMode, state.viewMode === URL_DEFAULTS.viewMode ? null : state.viewMode);
  put(URL_KEYS.riskType, state.riskType);
  const s = q.toString();
  return s ? `?${s}` : "";
}

/**
 * The query string with only the keys shared by every screen (the store mirror). Screen
 * filters such as the priority list's block stay on their own screen when navigating.
 */
export function sharedSearch(search: string): string {
  const keep = new Set<string>(Object.values(URL_KEYS));
  const q = new URLSearchParams(search);
  for (const key of [...q.keys()]) if (!keep.has(key)) q.delete(key);
  const s = q.toString();
  return s ? `?${s}` : "";
}
