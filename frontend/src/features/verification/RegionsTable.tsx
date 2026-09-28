import { useState } from "react";
import { diffVsB0 } from "./verifyData";
import { useTranslation } from "react-i18next";
import type { Lang, RegionItem, Var } from "../../api/types";
import { VARS } from "../../api/types";
import { SegmentedControl } from "../../components/SegmentedControl";
import { METRIC_DIGITS, bestIndexes, formatCount, formatFixed, rowDigits } from "../../lib/verify";
import { TableScroll } from "../../components/TableScroll";

const SCORE_KEYS = ["model", "b0", "b1", "b2"] as const;

/**
 * "Where it works" (Guide 6.4): error of the model and the baselines for every held-out
 * block and every station, one variable at a time. Blocks first, then stations; both in
 * the order the job wrote them.
 */
export function RegionsTable({ items, lang }: { items: readonly RegionItem[]; lang: Lang }) {
  const { t } = useTranslation();
  const present = VARS.filter((v) => items.some((i) => i.var === v));
  const [variable, setVariable] = useState<Var>(present[0] ?? "rain");
  const rows = items
    .filter((i) => i.var === variable)
    .sort((a, b) => Number(a.region_type === "station") - Number(b.region_type === "station"));
  const unit = rows[0] ? t(`units.${rows[0].unit}`, { defaultValue: rows[0].unit }) : "";
  const metric = rows[0]?.metric ?? "MAE";
  const varName = t(`vars.${variable}`);
  // One decimal count for the whole table, so each column lines up; enough decimals for
  // every row to show its differences.
  const digits = Math.max(
    METRIC_DIGITS[metric] ?? 2,
    ...rows.map((r) =>
      rowDigits(
        SCORE_KEYS.map((k) => r[k] ?? null),
        METRIC_DIGITS[r.metric] ?? 2,
      ),
    ),
  );

  return (
    <div className="stack">
      <SegmentedControl<Var>
        legend={t("verification.regionsVar")}
        name="regions-var"
        variant="wrap"
        value={variable}
        options={present.map((v) => ({ value: v, label: t(`varsShort.${v}`) }))}
        onChange={setVariable}
      />
      <TableScroll
        label={t("verification.regionsCaption", { variable: varName })}
        className="verify-table-wrap"
      >
        <table className="data-table verify-table">
          <caption className="visually-hidden">
            {t("verification.regionsCaption", { variable: varName })}
          </caption>
          <thead>
            <tr>
              <th scope="col">{t("verification.colRegion")}</th>
              <th scope="col" className="num">
                {t("verification.colForecastsShort")}
              </th>
              <th scope="col" className="num">
                {t("verification.colModel")}
                <span className="cell-sub">
                  {t(`verification.metrics.${metric}`, { defaultValue: metric })}, {unit}
                </span>
              </th>
              <th scope="col" className="num">
                {t("verification.colB0")}
              </th>
              <th scope="col" className="num">
                {t("verification.colB1")}
              </th>
              <th scope="col" className="num">
                {t("verification.colB2")}
              </th>
              <th scope="col" className="num">
                {t("verification.colDiffB0")}
                <span className="cell-sub">{unit}</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => {
              const values = SCORE_KEYS.map((k) => r[k] ?? null);
              const best = new Set(bestIndexes(values, "lower"));
              return (
                <tr key={`${r.region_type}-${r.region_id}`}>
                  <th scope="row">
                    {r.region_type === "block"
                      ? t("verification.regionBlock", { id: r.region_id })
                      : t("verification.regionStation", { id: r.region_id })}
                  </th>
                  <td className="num">{formatCount(r.n, lang)}</td>
                  {values.map((v, i) => (
                    <td key={SCORE_KEYS[i]} className={best.has(i) ? "num is-best" : "num"}>
                      {best.has(i) ? (
                        <strong>{formatFixed(v, lang, digits)}</strong>
                      ) : (
                        formatFixed(v, lang, digits)
                      )}
                    </td>
                  ))}
                  <td className="num">{signedFixed(diffVsB0(r), lang, digits)}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </TableScroll>
    </div>
  );
}

/** Signed difference with fixed decimals ("-0.091", "+0.012"). */
function signedFixed(value: number | null, lang: Lang, digits: number): string {
  if (value === null) return "–";
  if (Math.abs(value) < 0.5 * 10 ** -digits) return formatFixed(0, lang, digits);
  return (value < 0 ? "-" : "+") + formatFixed(Math.abs(value), lang, digits);
}
