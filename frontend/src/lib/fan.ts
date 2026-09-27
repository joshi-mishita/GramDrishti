import type { ForecastDay, ObservedDay, Var } from "../api/types";

/** One row of the fan chart (Guide 8.3). Missing numbers stay null and are skipped. */
export interface FanRow {
  date: string;
  p10: number | null;
  p50: number | null;
  p90: number | null;
  /** Lower edge of the band, drawn transparent; null when either edge is missing. */
  base: number | null;
  /** p90 minus p10, stacked on base; null when either edge is missing. */
  band: number | null;
  block: number | null;
  observed: number | null;
}

function num(v: number | null | undefined): number | null {
  return v === null || v === undefined || !Number.isFinite(v) ? null : v;
}

/**
 * Shapes forecast days (and optional observations) into fan chart rows for one variable.
 * Observations are matched by date; days without one get null. A band whose edges are
 * reversed is drawn with zero height rather than upside down.
 */
export function shapeFanRows(
  days: readonly ForecastDay[],
  variable: Var,
  observed?: readonly ObservedDay[] | null,
): FanRow[] {
  const obs = new Map((observed ?? []).map((d) => [d.date, num(d[variable])]));
  return [...days]
    .sort((a, b) => a.date.localeCompare(b.date))
    .map((d) => {
      const q = d[variable];
      const p10 = num(q.p10);
      const p90 = num(q.p90);
      const hasBand = p10 !== null && p90 !== null;
      return {
        date: d.date,
        p10,
        p50: num(q.p50),
        p90,
        base: hasBand ? p10 : null,
        band: hasBand ? Math.max(0, p90 - p10) : null,
        block: num(q.block),
        observed: obs.get(d.date) ?? null,
      };
    });
}

/** True when the chart has at least one number to draw. */
export function hasAnyValue(rows: readonly FanRow[]): boolean {
  return rows.some((r) => [r.p10, r.p50, r.p90, r.block, r.observed].some((v) => v !== null));
}

/** True when at least one row has an observation. */
export function hasObserved(rows: readonly FanRow[]): boolean {
  return rows.some((r) => r.observed !== null);
}

/** Round step sizes for the y axis: 1, 2, 2.5 or 5 times a power of ten. */
function niceStep(span: number, ticks: number): number {
  const raw = span / Math.max(1, ticks);
  const mag = 10 ** Math.floor(Math.log10(raw));
  const f = raw / mag;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return nice * mag;
}

/** Smallest axis span per variable, so a flat series is drawn inside the frame. */
const MIN_SPAN: Record<Var, number> = { rain: 4, tmax: 2, tmin: 2, rh: 10, wind: 4 };

/**
 * Y axis covering every value on the chart, widened to round numbers, with its tick values.
 * Rain, humidity and wind never go below 0, humidity never above 100. The ticks are the
 * same round steps as the ends, so the axis never reads 0, 0.2, 0.3, 0.5. Null when there
 * is nothing to draw.
 */
export function fanScale(
  rows: readonly FanRow[],
  variable: Var,
  ticks = 4,
): { domain: [number, number]; ticks: number[] } | null {
  const values = rows.flatMap((r) =>
    [r.p10, r.p50, r.p90, r.block, r.observed].filter((v): v is number => v !== null),
  );
  if (values.length === 0) return null;
  const floorZero = variable !== "tmax" && variable !== "tmin";
  let lo = Math.min(...values);
  let hi = Math.max(...values);
  if (floorZero) lo = Math.max(0, lo);
  const minSpan = MIN_SPAN[variable];
  if (hi - lo < minSpan) {
    const mid = (hi + lo) / 2;
    lo = mid - minSpan / 2;
    hi = mid + minSpan / 2;
    if (floorZero && lo < 0) {
      hi -= lo;
      lo = 0;
    }
  }
  const step = niceStep(hi - lo, ticks);
  lo = Math.floor(lo / step) * step;
  hi = Math.ceil(hi / step) * step;
  if (variable === "rh") hi = Math.min(100, hi);
  const count = Math.round((hi - lo) / step);
  // Rounded to the step's decimals so 0.1 + 0.2 does not become 0.30000000000000004.
  const digits = Math.max(0, -Math.floor(Math.log10(step)) + 1);
  const tickValues = Array.from({ length: count + 1 }, (_, i) =>
    Number((lo + i * step).toFixed(digits)),
  );
  return { domain: [lo, hi], ticks: tickValues };
}

/** The domain part of fanScale. */
export function fanDomain(
  rows: readonly FanRow[],
  variable: Var,
  ticks = 4,
): [number, number] | null {
  return fanScale(rows, variable, ticks)?.domain ?? null;
}
