import { useTranslation } from "react-i18next";
import type { Lang, Var } from "../../api/types";
import { VAR_DIGITS, describeRange } from "../../lib/format";
import { UNITS } from "../../lib/ramps";

/** Plain-language range: "likely between 2 and 14 mm". */
export function useRangeText() {
  const { t } = useTranslation();
  return (p10: number | null, p90: number | null, variable: Var, lang: Lang): string => {
    const unit = t(`units.${UNITS[variable]}`);
    const r = describeRange(p10, p90, lang, VAR_DIGITS[variable]);
    if (r.kind === "between") return t("panel.rangeBetween", { lo: r.lo, hi: r.hi, unit });
    if (r.kind === "about") return t("panel.rangeAbout", { value: r.value, unit });
    return t("panel.rangeUnknown");
  };
}
