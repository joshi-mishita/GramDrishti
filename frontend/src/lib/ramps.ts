/**
 * Colour ramps and breaks for the map and its legend (Frontend Guide 8.2). This file is the
 * only place map colours are defined: the map style and the Legend are both built from the
 * Ramp objects returned here, so they cannot drift apart.
 *
 * Palettes are ColorBrewer (Cynthia Brewer, Apache-2.0 style licence, colorbrewer2.org).
 * The darkest class of each sequential palette is dropped so polygons stay distinct from
 * the dark block outlines; RdBu drops both extremes for the same reason.
 */
import type { Level, Var } from "../api/types";

export interface RampStop {
  value: number;
  color: string;
}

export interface Ramp {
  kind: "sequential" | "diverging";
  /** Ascending by value. The map interpolates linearly between neighbouring stops. */
  stops: RampStop[];
  unit: string;
}

// ColorBrewer 9-class palettes, light to dark, darkest class removed.
const BLUES = [
  "#f7fbff",
  "#deebf7",
  "#c6dbef",
  "#9ecae1",
  "#6baed6",
  "#4292c6",
  "#2171b5",
  "#08519c",
];
const YL_OR_RD = [
  "#ffffcc",
  "#ffeda0",
  "#fed976",
  "#feb24c",
  "#fd8d3c",
  "#fc4e2a",
  "#e31a1c",
  "#bd0026",
];
const YL_GN_BU = [
  "#ffffd9",
  "#edf8b1",
  "#c7e9b4",
  "#7fcdbb",
  "#41b6c4",
  "#1d91c0",
  "#225ea8",
  "#253494",
];
const GN_BU = [
  "#f7fcf0",
  "#e0f3db",
  "#ccebc5",
  "#a8ddb5",
  "#7bccc4",
  "#4eb3d3",
  "#2b8cbe",
  "#0868ac",
];
const GREYS = [
  "#ffffff",
  "#f0f0f0",
  "#d9d9d9",
  "#bdbdbd",
  "#969696",
  "#737373",
  "#525252",
  "#252525",
];
// ColorBrewer RdBu 11-class without its two extremes: red (low) to blue (high).
const RD_BU = [
  "#b2182b",
  "#d6604d",
  "#f4a582",
  "#fddbc7",
  "#f7f7f7",
  "#d1e5f0",
  "#92c5de",
  "#4393c3",
  "#2166ac",
];

/** Units per variable, as in the contract (rule 7). */
export const UNITS: Record<Var, string> = {
  rain: "mm",
  tmax: "C",
  tmin: "C",
  rh: "%",
  wind: "km/h",
};

/** Fixed breaks from Guide 8.2. Temperatures have none: they follow the data in 3 C steps. */
const FIXED_BREAKS: Partial<Record<Var, number[]>> = {
  rain: [0, 1, 5, 15, 35, 65],
  rh: [20, 40, 60, 80, 100],
  wind: [0, 5, 10, 15, 20, 30],
};

const PALETTES: Record<Var, readonly string[]> = {
  rain: BLUES,
  tmax: YL_OR_RD,
  tmin: [...YL_GN_BU].reverse(), // cold nights dark blue, warm nights pale yellow
  rh: GN_BU,
  wind: GREYS,
};

/**
 * Difference ramps run red to blue for "more water" variables (more rain, more humidity is
 * blue) and blue to red for the rest (warmer or windier than the block is red).
 */
const DELTA_REVERSED: Record<Var, boolean> = {
  rain: false,
  rh: false,
  tmax: true,
  tmin: true,
  wind: true,
};

/** Smallest half-width of the difference scale, so tiny deltas do not look dramatic. */
const DELTA_MIN_HALF: Record<Var, number> = { rain: 1, tmax: 0.5, tmin: 0.5, rh: 2, wind: 1 };

const TEMP_STEP = 3;

/** Risk levels map to the severity tokens; resolve them with the page's CSS variables. */
export const RISK_TOKENS: Record<Level, string> = {
  low: "--sev-low",
  moderate: "--sev-mod",
  high: "--sev-high",
  severe: "--sev-severe",
};

function hexToRgb(hex: string): [number, number, number] {
  const n = Number.parseInt(hex.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function rgbToHex([r, g, b]: [number, number, number]): string {
  return `#${[r, g, b].map((c) => Math.round(c).toString(16).padStart(2, "0")).join("")}`;
}

/** Blends two hex colours in RGB; t = 0 gives a, t = 1 gives b. */
export function mixColors(a: string, b: string, t: number): string {
  const [ar, ag, ab] = hexToRgb(a);
  const [br, bg, bb] = hexToRgb(b);
  return rgbToHex([ar + (br - ar) * t, ag + (bg - ag) * t, ab + (bb - ab) * t]);
}

/** Array item that must exist (indices computed from the array's own length). */
function at<T>(xs: readonly T[], i: number): T {
  const x = xs[i];
  if (x === undefined) throw new RangeError(`Index ${i} out of range`);
  return x;
}

/**
 * Picks n colours evenly along a palette, blending neighbours in RGB when a position falls
 * between two palette entries. n = 1 gives the middle colour.
 */
export function sampleColors(palette: readonly string[], n: number): string[] {
  if (n <= 0) return [];
  if (palette.length === 0) throw new Error("Empty palette");
  if (n === 1) return [at(palette, Math.floor((palette.length - 1) / 2))];
  const out: string[] = [];
  for (let i = 0; i < n; i++) {
    const pos = (i * (palette.length - 1)) / (n - 1);
    const lo = Math.floor(pos);
    const hi = Math.min(lo + 1, palette.length - 1);
    out.push(mixColors(at(palette, lo), at(palette, hi), pos - lo));
  }
  return out;
}

/**
 * Temperature breaks every 3 C covering the values, with at least two steps.
 * Example: 26.6..36.1 gives 24, 27, 30, 33, 36, 39.
 */
export function temperatureBreaks(values: readonly number[], step = TEMP_STEP): number[] {
  const finite = values.filter(Number.isFinite);
  if (finite.length === 0) return [0, step, 2 * step];
  const lo = Math.floor(Math.min(...finite) / step) * step;
  let hi = Math.ceil(Math.max(...finite) / step) * step;
  while (hi - lo < 2 * step) hi += step;
  const out: number[] = [];
  for (let v = lo; v <= hi + 1e-9; v += step) out.push(v);
  return out;
}

/** Rounds up to 1, 2, 2.5 or 5 times a power of ten. */
export function niceCeil(x: number): number {
  if (!(x > 0) || !Number.isFinite(x)) return 0;
  const pow = 10 ** Math.floor(Math.log10(x));
  const f = x / pow;
  const nice = f <= 1 ? 1 : f <= 2 ? 2 : f <= 2.5 ? 2.5 : f <= 5 ? 5 : 10;
  return nice * pow;
}

/**
 * Ramp for forecast values of one variable. `values` are all values on screen in the block
 * and Panchayat views together, so both views share one scale and toggling is comparable.
 * Rain, humidity and wind ignore `values` and use the fixed breaks.
 */
export function valueRamp(variable: Var, values: readonly number[] = []): Ramp {
  const breaks = FIXED_BREAKS[variable] ?? temperatureBreaks(values);
  const colors = sampleColors(PALETTES[variable], breaks.length);
  return {
    kind: "sequential",
    unit: UNITS[variable],
    stops: breaks.map((value, i) => ({ value, color: at(colors, i) })),
  };
}

/**
 * Diverging ramp for Panchayat minus block, centred on 0 and symmetric. The half-width m is
 * the largest absolute difference rounded up to a nice number (1, 2, 2.5 or 5 x 10^k), never
 * below a floor per variable. Five stops: -m, -m/2, 0, m/2, m, so every tick is a round value.
 */
export function deltaRamp(variable: Var, deltas: readonly number[]): Ramp {
  const finite = deltas.filter(Number.isFinite).map(Math.abs);
  const maxAbs = finite.length ? Math.max(...finite) : 0;
  const m = Math.max(niceCeil(maxAbs), DELTA_MIN_HALF[variable]);
  const palette = DELTA_REVERSED[variable] ? [...RD_BU].reverse() : RD_BU;
  const colors = sampleColors(palette, 5);
  const values = [-m, -m / 2, 0, m / 2, m];
  return {
    kind: "diverging",
    unit: UNITS[variable],
    stops: values.map((value, i) => ({ value, color: at(colors, i) })),
  };
}

/** Returns the ramp colour for a value, interpolated like the map does; null for no value. */
export function colorFor(ramp: Ramp, value: number | null | undefined): string | null {
  if (value === null || value === undefined || !Number.isFinite(value)) return null;
  const { stops } = ramp;
  const first = stops[0];
  const last = stops[stops.length - 1];
  if (!first || !last) return null;
  if (value <= first.value) return first.color;
  if (value >= last.value) return last.color;
  for (let i = 1; i < stops.length; i++) {
    const a = at(stops, i - 1);
    const b = at(stops, i);
    if (value <= b.value)
      return mixColors(a.color, b.color, (value - a.value) / (b.value - a.value));
  }
  return last.color;
}

/**
 * MapLibre paint expression for a fill coloured by the feature-state "v" (Guide 8.1).
 * Features without a value get `noValueColor`.
 */
export function fillColorExpression(ramp: Ramp, noValueColor: string): unknown[] {
  const stops = ramp.stops.flatMap((s) => [s.value, s.color]);
  const interpolate =
    ramp.stops.length === 1
      ? at(ramp.stops, 0).color
      : ["interpolate", ["linear"], ["to-number", ["feature-state", "v"]], ...stops];
  return ["case", ["==", ["feature-state", "v"], null], noValueColor, interpolate];
}
