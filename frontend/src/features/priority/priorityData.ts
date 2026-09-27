/** Pure helpers for the priority screen (Guide 6.2). */
import type { PriorityItem, RiskType } from "../../api/types";
import { RISK_TYPES } from "../../api/types";
import { LEAD_DAYS } from "../../lib/config";
import { parseIsoDate } from "../../lib/format";
import { LEVEL_INDEX } from "../../lib/ramps";
import { RISK_VAR } from "../map/mapData";

/** Horizons offered on the screen: the next 1, 2 or 3 days. */
export const HORIZONS = [1, 2, 3] as const;
export const DEFAULT_HORIZON = 2;

export interface PriorityFilters {
  horizon: number;
  type: RiskType | null;
  block: string | null;
}

/** URL keys of the filters, so a printed or shared list says what it shows. */
export const FILTER_KEYS = { horizon: "horizon", type: "type", block: "block" } as const;

/** Reads the filters from a query string; unknown values fall back to "all". */
export function readFilters(search: string): PriorityFilters {
  const q = new URLSearchParams(search);
  const h = Number(q.get(FILTER_KEYS.horizon));
  const type = q.get(FILTER_KEYS.type);
  const block = q.get(FILTER_KEYS.block);
  return {
    horizon: (HORIZONS as readonly number[]).includes(h) ? h : DEFAULT_HORIZON,
    type: type && RISK_TYPES.includes(type as RiskType) ? (type as RiskType) : null,
    block: block && /^[A-Za-z0-9_-]{1,32}$/.test(block) ? block : null,
  };
}

/** Writes the filters into a query string, dropping defaults and keeping other keys. */
export function writeFilters(search: string, f: PriorityFilters): string {
  const q = new URLSearchParams(search);
  const put = (key: string, value: string | null) => {
    if (value) q.set(key, value);
    else q.delete(key);
  };
  put(FILTER_KEYS.horizon, f.horizon === DEFAULT_HORIZON ? null : String(f.horizon));
  put(FILTER_KEYS.type, f.type);
  put(FILTER_KEYS.block, f.block);
  const s = q.toString();
  return s ? `?${s}` : "";
}

/** A ranked item: its position in the API's order (level, then score, then id). */
export interface RankedItem extends PriorityItem {
  rank: number;
}

/** Keeps the API ranking as `rank`, then applies the risk type and block filters. */
export function rankAndFilter(
  items: readonly PriorityItem[],
  f: Pick<PriorityFilters, "type" | "block">,
): RankedItem[] {
  return items
    .map((item, i) => ({ ...item, rank: i + 1 }))
    .filter((i) => (!f.type || i.top_risk === f.type) && (!f.block || i.block_id === f.block));
}

/** Sort value for the level column: level first, then score, so ties keep a meaning. */
export function levelSortValue(item: PriorityItem): number {
  return LEVEL_INDEX[item.level] + item.score / 10;
}

/** Lead day (1 to 5) of a valid date after an issue date; 1 when it is unknown. */
export function leadDayOf(issueDate: string, validDate: string | null | undefined): number {
  if (!validDate) return 1;
  const days = Math.round(
    (parseIsoDate(validDate).getTime() - parseIsoDate(issueDate).getTime()) / 86_400_000,
  );
  return (LEAD_DAYS as readonly number[]).includes(days) ? days : 1;
}

/**
 * Map link for a priority row: the Panchayat selected, on the day of its top risk, with
 * that risk layer on and the variable behind it in the panel.
 */
export function mapLinkFor(item: PriorityItem, issueDate: string): string {
  const q = new URLSearchParams({
    date: issueDate,
    var: RISK_VAR[item.top_risk],
    pid: item.panchayat_id,
    risk: item.top_risk,
  });
  const day = leadDayOf(issueDate, item.valid_date);
  if (day !== 1) q.set("day", String(day));
  return `/map?${q.toString()}`;
}
