/** Pure helpers that map the URL query to the mirrored part of the store and back. */
import { VARS, type Var } from "../api/types";
import { isIsoDate } from "../lib/format";

export interface UrlState {
  issueDate: string | null;
  variable: Var | null;
  selectedPid: string | null;
}

export const URL_KEYS = { issueDate: "date", variable: "var", selectedPid: "pid" } as const;

const PID = /^[A-Za-z0-9_-]{1,32}$/;

/** Reads date, var and pid from a query string. Invalid values read as null. */
export function readUrlState(search: string): UrlState {
  const q = new URLSearchParams(search);
  const date = q.get(URL_KEYS.issueDate);
  const v = q.get(URL_KEYS.variable);
  const pid = q.get(URL_KEYS.selectedPid);
  return {
    issueDate: date && isIsoDate(date) ? date : null,
    variable: v && VARS.includes(v as Var) ? (v as Var) : null,
    selectedPid: pid && PID.test(pid) ? pid : null,
  };
}

/** Returns the query string with date, var and pid set from state; other keys are kept. */
export function writeUrlState(
  search: string,
  state: { issueDate: string | null; variable: Var; selectedPid: string | null },
): string {
  const q = new URLSearchParams(search);
  const put = (key: string, value: string | null) => {
    if (value) q.set(key, value);
    else q.delete(key);
  };
  put(URL_KEYS.issueDate, state.issueDate);
  put(URL_KEYS.variable, state.variable);
  put(URL_KEYS.selectedPid, state.selectedPid);
  const s = q.toString();
  return s ? `?${s}` : "";
}
