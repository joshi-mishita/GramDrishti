/** Pure helpers that turn a /forecast/map response into what the map paints. */
import type { ForecastMap, Lang, PanchayatCollection, PanchayatMapValue } from "../../api/types";
import { formatNumber, formatSigned } from "../../lib/format";
import { deltaRamp, valueRamp, type Ramp } from "../../lib/ramps";
import type { ViewMode } from "../../state/store";

/** The number a Panchayat is painted with in a view mode (Guide 8.1). */
export function valueForMode(row: PanchayatMapValue, mode: ViewMode): number | null {
  if (mode === "block") return row.block_value;
  if (mode === "delta") return row.delta;
  return row.p50;
}

/** Map of panchayat_id to the painted value for one view mode. */
export function valuesForMode(
  rows: readonly PanchayatMapValue[],
  mode: ViewMode,
): Map<string, number | null> {
  return new Map(rows.map((r) => [r.panchayat_id, valueForMode(r, mode)]));
}

const finite = (xs: (number | null)[]): number[] =>
  xs.filter((x): x is number => x !== null && Number.isFinite(x));

/**
 * The ramp for a view. Block and Panchayat views share one ramp built from both columns,
 * so switching between them changes only the polygons, never the legend.
 */
export function rampForMode(forecast: ForecastMap, mode: ViewMode): Ramp {
  const rows = forecast.panchayat_layer;
  if (mode === "delta") return deltaRamp(forecast.var, finite(rows.map((r) => r.delta)));
  return valueRamp(forecast.var, finite(rows.flatMap((r) => [r.p50, r.block_value])));
}

/**
 * True when every block's Panchayats share one p50 (the provisional forecast is block-level),
 * so the screen can say that the Panchayat view has no within-block variation yet.
 */
export function isFlatWithinBlocks(rows: readonly PanchayatMapValue[]): boolean {
  const first = new Map<string, number | null>();
  for (const r of rows) {
    if (!first.has(r.block_id)) first.set(r.block_id, r.p50);
    else if (first.get(r.block_id) !== r.p50) return false;
  }
  return rows.length > 0;
}

export interface TableRow extends PanchayatMapValue {
  name: string;
}

/** Joins map values with Panchayat names; values without a boundary keep their id as name. */
export function tableRows(forecast: ForecastMap, geo: PanchayatCollection): TableRow[] {
  const names = new Map(geo.features.map((f) => [f.properties.panchayat_id, f.properties.name]));
  return forecast.panchayat_layer.map((r) => ({
    ...r,
    name: names.get(r.panchayat_id) ?? r.panchayat_id,
  }));
}

/** Break values formatted for a legend tick; differences keep their sign. */
export function legendTicks(ramp: Ramp, lang: Lang): string[] {
  // Breaks are round numbers such as 1.25 or 2.5; two decimals show them exactly.
  const digits = 2;
  return ramp.stops.map((s) =>
    ramp.kind === "diverging"
      ? formatSigned(s.value, lang, digits)
      : formatNumber(s.value, lang, digits),
  );
}

/** [west, south, east, north] of every coordinate in a FeatureCollection. */
export function boundsOf(fc: {
  features: { geometry: { coordinates: unknown } }[];
}): [number, number, number, number] | null {
  let w = Infinity;
  let s = Infinity;
  let e = -Infinity;
  let n = -Infinity;
  const walk = (c: unknown): void => {
    if (!Array.isArray(c)) return;
    if (typeof c[0] === "number" && typeof c[1] === "number") {
      w = Math.min(w, c[0]);
      e = Math.max(e, c[0]);
      s = Math.min(s, c[1]);
      n = Math.max(n, c[1]);
      return;
    }
    for (const x of c) walk(x);
  };
  for (const f of fc.features) walk(f.geometry.coordinates);
  return Number.isFinite(w) ? [w, s, e, n] : null;
}
