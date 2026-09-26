import type { Lang, Var } from "../api/types";

const LOCALES: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", pa: "pa-IN" };

// Day and month names are fixed tables, not Intl: browsers ship different locale data
// (Chrome has no Punjabi month names and prints "M09"; some ICU versions write "Sept").
// Hindi and Punjabi names follow CLDR and need native review with the other UI strings.
const WEEKDAYS: Record<Lang, readonly string[]> = {
  en: ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
  hi: ["रवि", "सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि"],
  pa: ["ਐਤ", "ਸੋਮ", "ਮੰਗਲ", "ਬੁੱਧ", "ਵੀਰ", "ਸ਼ੁੱਕਰ", "ਸ਼ਨਿੱਚਰ"],
};
const MONTHS: Record<Lang, readonly string[]> = {
  en: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
  hi: [
    "जनवरी",
    "फ़रवरी",
    "मार्च",
    "अप्रैल",
    "मई",
    "जून",
    "जुलाई",
    "अगस्त",
    "सितंबर",
    "अक्तूबर",
    "नवंबर",
    "दिसंबर",
  ],
  pa: [
    "ਜਨਵਰੀ",
    "ਫ਼ਰਵਰੀ",
    "ਮਾਰਚ",
    "ਅਪ੍ਰੈਲ",
    "ਮਈ",
    "ਜੂਨ",
    "ਜੁਲਾਈ",
    "ਅਗਸਤ",
    "ਸਤੰਬਰ",
    "ਅਕਤੂਬਰ",
    "ਨਵੰਬਰ",
    "ਦਸੰਬਰ",
  ],
};

const ISO_DATE = /^(\d{4})-(\d{2})-(\d{2})$/;

/** Returns the Intl locale used for a UI language. */
export function localeFor(lang: Lang): string {
  return LOCALES[lang];
}

/** True for a well-formed ISO calendar date (YYYY-MM-DD). */
export function isIsoDate(value: string): boolean {
  const m = ISO_DATE.exec(value);
  if (!m) return false;
  const d = new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
  return d.toISOString().slice(0, 10) === value;
}

/** Parses an ISO date as a UTC midnight so no time zone can shift the day. */
export function parseIsoDate(value: string): Date {
  const m = ISO_DATE.exec(value);
  if (!m) throw new Error(`Not an ISO date: ${value}`);
  return new Date(Date.UTC(Number(m[1]), Number(m[2]) - 1, Number(m[3])));
}

/** Adds whole days to an ISO date and returns an ISO date. */
export function addDays(value: string, days: number): string {
  const d = parseIsoDate(value);
  d.setUTCDate(d.getUTCDate() + days);
  return d.toISOString().slice(0, 10);
}

type DateStyle = "short" | "day" | "long";

/**
 * Formats an ISO date for display.
 * "short" gives weekday and day ("Tue 10"), for chart axes where the month is shown once.
 * "day" gives weekday, day and month ("Tue 10 Sep"), for lead-day buttons.
 * "long" adds the year ("Tue 10 Sep 2024"). Hindi and Punjabi write the month in full
 * ("मंगल 10 सितंबर 2024"), as the API's advisory text does. Digits are Western everywhere.
 */
export function formatDate(value: string, lang: Lang, style: DateStyle = "long"): string {
  const d = parseIsoDate(value);
  const parts = [WEEKDAYS[lang][d.getUTCDay()], String(d.getUTCDate())];
  if (style === "short") return parts.join(" ");
  parts.push(MONTHS[lang][d.getUTCMonth()]);
  if (style === "long") parts.push(String(d.getUTCFullYear()));
  return parts.join(" ");
}

/** Formats a number with Western digits in every language, so numerals stay consistent. */
export function formatNumber(value: number | null | undefined, lang: Lang, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  return new Intl.NumberFormat(localeFor(lang), {
    maximumFractionDigits: digits,
    numberingSystem: "latn",
  }).format(value);
}

/** Decimal places shown per variable: humidity in whole percent, the rest to 0.1. */
export const VAR_DIGITS: Record<Var, number> = { rain: 1, tmax: 1, tmin: 1, rh: 0, wind: 1 };

/** Formats a value with its unit label ("9.8 mm", "35.7 °C"); a dash when there is none. */
export function formatValue(
  value: number | null | undefined,
  unitLabel: string,
  lang: Lang,
  digits = 1,
): string {
  const n = formatNumber(value, lang, digits);
  return n === "–" ? n : `${n} ${unitLabel}`;
}

/** Formats a difference with an explicit sign ("+0.9", "-4.5"); zero after rounding has none. */
export function formatSigned(value: number | null | undefined, lang: Lang, digits = 1): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "–";
  return new Intl.NumberFormat(localeFor(lang), {
    maximumFractionDigits: digits,
    numberingSystem: "latn",
    signDisplay: "exceptZero",
  }).format(value);
}

export type RangeText =
  | { kind: "between"; lo: string; hi: string }
  | { kind: "about"; value: string }
  | { kind: "unknown" };

/**
 * Turns a p10..p90 band into the parts of a plain-language range. When both ends round to
 * the same number the band is "about" that number; a missing end gives "unknown".
 */
export function describeRange(
  p10: number | null | undefined,
  p90: number | null | undefined,
  lang: Lang,
  digits = 1,
): RangeText {
  const lo = formatNumber(p10, lang, digits);
  const hi = formatNumber(p90, lang, digits);
  if (lo === "–" || hi === "–") return { kind: "unknown" };
  if (lo === hi) return { kind: "about", value: lo };
  return { kind: "between", lo, hi };
}
