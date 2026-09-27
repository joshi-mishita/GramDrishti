/**
 * Number rules for the verification and impact screens (Guide 6.4, 6.5).
 *
 * Every number shown there comes from the verification job. These helpers only choose
 * decimals, pick the best value in a row and turn counts into shares; they never make
 * up a score.
 */
import type { DecisionCounts, Lang } from "../api/types";
import { formatNumber, localeFor } from "./format";

/** Which value in a row is best: the lowest, the highest, nearest 0 or nearest 1. */
export type Better = "lower" | "higher" | "zero" | "one";

/** Scores the job reports, with the direction that counts as better. */
export const METRIC_BETTER: Record<string, Better> = {
  MAE: "lower",
  RMSE: "lower",
  bias: "zero",
  quantile_loss: "lower",
  MAE_wet_days_obs_ge_1mm: "lower",
  pod: "higher",
  far: "lower",
  csi: "higher",
  frequency_bias: "one",
  brier: "lower",
};

/** Fixed decimals per metric. Scores in a unit get 2; probabilities and rates get 3. */
export const METRIC_DIGITS: Record<string, number> = {
  MAE: 2,
  RMSE: 2,
  bias: 2,
  quantile_loss: 2,
  MAE_wet_days_obs_ge_1mm: 2,
  pod: 2,
  far: 2,
  csi: 3,
  frequency_bias: 2,
  brier: 4,
};

/** Most decimals a row may grow to when its fixed decimals would hide a difference. */
export const MAX_DIGITS = 4;

/** Two job values closer than this are the same value (for example model and B1 bias). */
const SAME = 1e-9;

function distance(value: number, better: Better): number {
  switch (better) {
    case "lower":
      return value;
    case "higher":
      return -value;
    case "zero":
      return Math.abs(value);
    case "one":
      return Math.abs(value - 1);
  }
}

/**
 * Indexes of the best values in a row. Nulls never win; equal values share the win.
 * Returns an empty list when fewer than two values can be compared.
 */
export function bestIndexes(values: readonly (number | null)[], better: Better): number[] {
  const scored = values
    .map((v, i) => ({ i, d: v === null || !Number.isFinite(v) ? null : distance(v, better) }))
    .filter((x): x is { i: number; d: number } => x.d !== null);
  if (scored.length < 2) return [];
  const best = Math.min(...scored.map((x) => x.d));
  return scored.filter((x) => x.d - best <= SAME).map((x) => x.i);
}

function fixed(value: number, digits: number): string {
  return value.toFixed(digits);
}

/**
 * Decimals for one table row: the metric's fixed decimals, or more when two different
 * values in the row would otherwise print the same (up to MAX_DIGITS). A row that needs
 * more than that keeps MAX_DIGITS; values equal to within 1e-9 are not a difference.
 */
export function rowDigits(values: readonly (number | null)[], base: number): number {
  const nums = values.filter((v): v is number => v !== null && Number.isFinite(v));
  for (let d = base; d <= MAX_DIGITS; d++) {
    if (!hidesDifference(nums, d)) return d;
  }
  return Math.max(base, MAX_DIGITS);
}

function hidesDifference(nums: readonly number[], digits: number): boolean {
  for (let a = 0; a < nums.length; a++) {
    for (let b = a + 1; b < nums.length; b++) {
      const x = nums[a] as number;
      const y = nums[b] as number;
      if (Math.abs(x - y) > SAME && fixed(x, digits) === fixed(y, digits)) return true;
    }
  }
  return false;
}

/** Formats a score with exactly `digits` decimals (trailing zeros kept, so columns align). */
export function formatFixed(value: number | null | undefined, lang: Lang, digits: number): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  return new Intl.NumberFormat(localeFor(lang), {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    numberingSystem: "latn",
  }).format(value);
}

/**
 * Formats a 0..1 share as a percent with one decimal and an explicit sign ("+13.7%").
 * A value that is not zero never prints as zero: -0.000365 gives "-0.04%", not "0.0%",
 * because the sign of an interval end decides "worse" or "no clear difference".
 */
export function formatSkill(value: number | null | undefined, lang: Lang): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  let digits = 1;
  while (value !== 0 && Math.abs(value * 100) < 0.5 * 10 ** -digits && digits < MAX_DIGITS) {
    digits++;
  }
  return new Intl.NumberFormat(localeFor(lang), {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    numberingSystem: "latn",
    // "always" for any non-zero value, so a value too small to print still shows its sign.
    signDisplay: value === 0 ? "exceptZero" : "always",
  }).format(value);
}

/** Formats a 0..1 share as a plain percent ("93.4%"), `digits` decimals. */
export function formatPercent(value: number | null | undefined, lang: Lang, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  return new Intl.NumberFormat(localeFor(lang), {
    style: "percent",
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
    numberingSystem: "latn",
  }).format(value);
}

/** Formats a whole count with thousands separators ("73,800"). */
export function formatCount(value: number | null | undefined, lang: Lang): string {
  return formatNumber(value, lang, 0);
}

/**
 * What a 95 % skill interval says, by the job's own rule (D072): the whole interval above
 * zero is better than the baseline, the whole interval below zero is worse, otherwise the
 * difference is not clear. No interval: unknown.
 */
export type SkillReading = "better" | "worse" | "unclear" | "unknown";

export function readSkill(ci: readonly number[] | null | undefined): SkillReading {
  if (!ci || ci.length !== 2) return "unknown";
  const [lo, hi] = ci as [number, number];
  if (lo > 0) return "better";
  if (hi < 0) return "worse";
  return "unclear";
}

/** Replay outcomes in the contract's order. */
export const OUTCOMES = ["correct", "wasted_wait", "washed_off"] as const;
export type Outcome = (typeof OUTCOMES)[number];

export interface Segment {
  outcome: Outcome;
  count: number;
  /** Share of all decisions, 0..1. */
  share: number;
}

/** Splits replay counts into bar segments; shares are of the three counts' total. */
export function segments(counts: DecisionCounts): Segment[] {
  const total = counts.correct + counts.wasted_wait + counts.washed_off;
  return OUTCOMES.map((outcome) => ({
    outcome,
    count: counts[outcome],
    share: total > 0 ? counts[outcome] / total : 0,
  }));
}

/**
 * Coverage strata from the API ("all", "lead_day=2", "season=monsoon",
 * "observed_rain>=1mm"), split into a kind and a value for labels and grouping.
 */
export type StratumKind = "all" | "lead_day" | "season" | "wet_days" | "other";

export function parseStratum(stratum: string | null | undefined): {
  kind: StratumKind;
  value: string;
} {
  if (!stratum || stratum === "all") return { kind: "all", value: "" };
  if (stratum === "observed_rain>=1mm") return { kind: "wet_days", value: "" };
  const m = /^(lead_day|season)=(.+)$/.exec(stratum);
  if (m) return { kind: m[1] as "lead_day" | "season", value: m[2] as string };
  return { kind: "other", value: stratum };
}

/**
 * Splits the job's notes into those that report where the model does not help and the
 * rest. The job writes losses as "Does NOT beat ...", "Worse than or equal to ...",
 * "... is below B0 ..." or "... no better than ...". Unknown wording stays with the rest,
 * so every note is always shown somewhere.
 */
const LOSS_NOTE = /^(Does NOT beat|Worse than or equal)|\bis below B[0-2]\b|\bno better than\b/;

export function splitNotes(notes: readonly string[]): { losses: string[]; other: string[] } {
  const losses: string[] = [];
  const other: string[] = [];
  for (const n of notes) (LOSS_NOTE.test(n) ? losses : other).push(n);
  return { losses, other };
}

/**
 * Job terms in the API's notes, in plain English (the notes are English only). Numbers and
 * verdicts are left exactly as the job wrote them; only names change.
 */
const NOTE_TERMS: [RegExp, string | ((...m: string[]) => string)][] = [
  [/\bDoes NOT beat\b/g, "Does not beat"],
  [/\b95% CI\b/g, "95% interval"],
  [/\btemporal_holdout\b/g, "held-out period"],
  [/\bleave_one_block_out\b/g, "held-out block"],
  [/\blead_day (\d)/g, "lead day $1"],
  [/\bseason (\w+)/g, (_, s) => `${s.replace(/_/g, "-")} season`],
  [/\brain_intensity dry_lt_1mm\b/g, "dry days (under 1 mm)"],
  [/\brain_intensity light_1_10mm\b/g, "light rain days (1 to 10 mm)"],
  [/\brain_intensity moderate_10_35mm\b/g, "moderate rain days (10 to 35 mm)"],
  [/\brain_intensity heavy_ge_35mm\b/g, "heavy rain days (35 mm or more)"],
  [/\bdrainage_class (\w+)/g, "$1 drainage"],
  [/\btoo_few_days\b/g, "too few days"],
  [/\bMAE_wet_days_obs_ge_1mm\b/g, "mean absolute error on wet days (1 mm or more observed)"],
  [/\bMAE\b/g, "mean absolute error"],
  [/\bRMSE\b/g, "root mean square error"],
  [/\brain_ge_(\d+)(?:_(\d+))?mm\b/g, (_, a, b) => `Rain ${b ? `${a}.${b}` : a} mm or more`],
  [/\bon rh\b/g, "on humidity"],
  [/\bon tmax\b/g, "on max temperature"],
  [/\bon tmin\b/g, "on min temperature"],
  [/\bforecast_prob\b/g, "the forecast chance"],
  [/\bscore_model\b/g, "model score"],
  [/\bscore_baseline\b/g, "baseline score"],
  [/\bwasted_wait\b/g, "wasted wait"],
  [/\bwashed_off\b/g, "washed off"],
  [/\bblock_baseline\b/g, "block baseline"],
  [/\bblock_corrected\b/g, "corrected block"],
  [/ >= /g, " ≥ "],
];

/** One API note in plain words, starting with a capital letter. */
export function readableNote(note: string): string {
  let out = note;
  for (const [re, to] of NOTE_TERMS) {
    // Two calls because TypeScript's replace overloads take a string or a function, not both.
    out = typeof to === "string" ? out.replace(re, to) : out.replace(re, to);
  }
  return out.charAt(0).toUpperCase() + out.slice(1);
}

/**
 * Splits a loss note "Does not beat B1 on rain ... (held-out period): overall: tie (...);
 * lead day 1: tie (...)" into its headline and one item per stratum, so a long line of
 * results reads as a list. Notes without that shape come back whole, with no items.
 */
export function splitLossNote(note: string): { head: string; items: string[] } {
  const m = /^(.*?\)): (.*)$/.exec(note);
  // "overall: tie (...)" is a stratum result; "skill -4.3%." is a single number and stays inline.
  if (!m?.[1] || !m[2] || !/^[^:]+: /.test(m[2])) return { head: note, items: [] };
  return { head: m[1], items: m[2].replace(/\.$/, "").split("; ") };
}
