import type { TFunction } from "i18next";
import type { ForecastDay, Lang } from "../../api/types";
import { describeRange, formatNumber } from "../../lib/format";
import { probWord } from "../../lib/words";

/** Rain in words and mm: the chance of any rain (1 mm or more) and the likely range. */
export function rainText(day: ForecastDay, lang: Lang, t: TFunction): string {
  const word = t(`farmer.rainWord.${probWord(day.prob.rain_ge_1mm)}`);
  const r = describeRange(day.rain.p10, day.rain.p90, lang, 0);
  if (r.kind === "between") return t("farmer.rainRange", { word, lo: r.lo, hi: r.hi });
  if (r.kind === "about") return t("farmer.rainAbout", { word, value: r.value });
  return t("farmer.rainNone", { word });
}

/** Night low to day high, from the middle estimates. */
export function tempText(day: ForecastDay, lang: Lang, t: TFunction) {
  return t("farmer.tempRange", {
    lo: formatNumber(day.tmin.p50, lang, 0),
    hi: formatNumber(day.tmax.p50, lang, 0),
  });
}
