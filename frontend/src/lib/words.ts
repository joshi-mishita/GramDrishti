import type { Confidence, Lang } from "../api/types";
import { localeFor } from "./format";

/**
 * Probability words, chosen from the rounded percent so the word and the number shown
 * next to it never disagree ("possible, 60%" cannot happen). Bands (D060):
 * under 10 % very unlikely, 10 to 29 % unlikely, 30 to 59 % possible, 60 % and over likely.
 */
export type ProbWord = "very_unlikely" | "unlikely" | "possible" | "likely" | "unknown";

/** Rounds a probability (0..1) to a whole percent; null when missing or not finite. */
export function toPercent(p: number | null | undefined): number | null {
  if (p === null || p === undefined || !Number.isFinite(p)) return null;
  return Math.round(Math.min(1, Math.max(0, p)) * 100);
}

/** The word for a probability (0..1). */
export function probWord(p: number | null | undefined): ProbWord {
  const pct = toPercent(p);
  if (pct === null) return "unknown";
  if (pct < 10) return "very_unlikely";
  if (pct < 30) return "unlikely";
  if (pct < 60) return "possible";
  return "likely";
}

/**
 * Formats a probability as a whole percent. The API rounds to two decimals, so 0 and 1
 * mean "below 0.5 %" and "above 99.5 %": they are shown as "<1%" and ">99%", never as
 * certainty.
 */
export function formatPercent(p: number | null | undefined, lang: Lang): string {
  const pct = toPercent(p);
  if (pct === null) return "–";
  const nf = new Intl.NumberFormat(localeFor(lang), { numberingSystem: "latn" });
  if (pct < 1) return `<${nf.format(1)}%`;
  if (pct > 99) return `>${nf.format(99)}%`;
  return `${nf.format(pct)}%`;
}

/** Confidence words from Guide 2.7: the contract enum high/medium/low, in words. */
export type ConfidenceWord = "likely" | "possible" | "uncertain";

export const CONFIDENCE_WORD: Record<Confidence, ConfidenceWord> = {
  high: "likely",
  medium: "possible",
  low: "uncertain",
};

/** Maps a contract confidence value to its word; unknown values read as "uncertain". */
export function confidenceWord(c: Confidence | null | undefined): ConfidenceWord {
  return (c && CONFIDENCE_WORD[c]) || "uncertain";
}
