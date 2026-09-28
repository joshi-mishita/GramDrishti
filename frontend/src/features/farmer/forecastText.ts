import type { TFunction } from "i18next";
import type { ForecastDay, Lang } from "../../api/types";
import { formatNumber } from "../../lib/format";
import { probWord } from "../../lib/words";

/**
 * Rain in words and mm: the chance of any rain (1 mm or more), the most likely amount (p50)
 * and how high it could go (p90). The low end is left out: it is 0 mm on almost every day,
 * and "0 to 156 mm" hid a likely 104 mm (S18).
 */
export function rainText(day: ForecastDay, lang: Lang, t: TFunction): string {
  const word = t(`farmer.rainWord.${probWord(day.prob.rain_ge_1mm)}`);
  const mid = formatNumber(day.rain.p50, lang, 0);
  const hi = formatNumber(day.rain.p90, lang, 0);
  if (mid === "–" || hi === "–" || hi === formatNumber(0, lang, 0)) {
    return t("farmer.rainNone", { word });
  }
  if (mid === formatNumber(0, lang, 0)) return t("farmer.rainUpTo", { word, hi });
  if (mid === hi) return t("farmer.rainAbout", { word, value: mid });
  return t("farmer.rainRange", { word, mid, hi });
}

/** Night low to day high, from the middle estimates. */
export function tempText(day: ForecastDay, lang: Lang, t: TFunction) {
  return t("farmer.tempRange", {
    lo: formatNumber(day.tmin.p50, lang, 0),
    hi: formatNumber(day.tmax.p50, lang, 0),
  });
}
