/** Pure helpers for the verification screen's charts and tables (tested in verifyData.test.ts). */
import type { CoverageItem, RegionItem, ReliabilityPoint } from "../../api/types";
import { parseStratum } from "../../lib/verify";

export type CoverageGroup = "all" | "lead_day" | "season";

export interface Dot {
  x: number;
  y: number;
  n: number;
  r: number;
  point: ReliabilityPoint;
}

const R_MIN = 4;
const R_MAX = 14;
/** Half the width of the job's probability bins (10 equal bins). */
const HALF_BIN = 0.05;

/**
 * Dots sit at the mean forecast chance of their bin when the job reports it (the bin centre
 * otherwise), so a bin whose forecasts cluster at one end is drawn where they are. Radius
 * grows with the square root of the count, so area follows the number of forecasts.
 */
export function reliabilityDots(points: readonly ReliabilityPoint[]): Dot[] {
  const withObs = points.filter((p) => p.observed_freq !== null);
  const maxN = Math.max(1, ...withObs.map((p) => p.n));
  return withObs.map((p) => ({
    x: p.mean_forecast_prob ?? p.forecast_prob,
    y: p.observed_freq as number,
    n: p.n,
    r: R_MIN + (R_MAX - R_MIN) * Math.sqrt(p.n / maxN),
    point: p,
  }));
}

/** Ends of the probability bin centred on `centre` (0.15 gives 0.1 and 0.2). */
export function binEnds(centre: number): [number, number] {
  return [Math.max(0, centre - HALF_BIN), Math.min(1, centre + HALF_BIN)];
}

/**
 * Items drawn as bars: every variable over all days, and rain on wet days right after rain,
 * because that is where the rain interval misses most.
 */
export function chartItems(items: readonly CoverageItem[]): CoverageItem[] {
  const out: CoverageItem[] = [];
  for (const it of items) {
    const kind = parseStratum(it.stratum).kind;
    if (kind === "all") out.push(it);
    if (kind === "wet_days") {
      const at = out.findIndex((x) => x.var === it.var);
      out.splice(at === -1 ? out.length : at + 1, 0, it);
    }
  }
  return out;
}

/** Items for the table under one strata group; "all" includes the wet-day row. */
export function tableItems(items: readonly CoverageItem[], group: CoverageGroup): CoverageItem[] {
  if (group === "all") return chartItems(items);
  return items.filter((it) => parseStratum(it.stratum).kind === group);
}

/** Model minus B0 in the metric's unit; null when either is missing. */
export function diffVsB0(item: RegionItem): number | null {
  if (item.model === null || item.b0 === null) return null;
  return item.model - item.b0;
}
