import { useTranslation } from "react-i18next";
import type { Lang, MetricRow, VariableSummary } from "../../api/types";
import {
  METRIC_BETTER,
  METRIC_DIGITS,
  bestIndexes,
  formatCount,
  formatFixed,
  formatSkill,
  readSkill,
  rowDigits,
} from "../../lib/verify";
import { useAppStore } from "../../state/store";

interface Props {
  variables: readonly VariableSummary[];
  caption: string;
}

/** The four score columns, in the order Guide 6.4 lists them. */
const SCORE_KEYS = ["model", "b0", "b1", "b2"] as const;

/**
 * Model against B0, B1 and B2 for every variable and score (Guide 6.4). The best value in a
 * row is bold. Rows where the model loses look exactly like the others: no greying, no
 * hiding, and the skill cell says "worse" in words.
 */
export function ComparisonTable({ variables, caption }: Props) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);

  return (
    <div className="table-wrap verify-table-wrap">
      <table className="data-table verify-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            <th scope="col">{t("verification.colMetric")}</th>
            <th scope="col" className="num">
              {t("verification.colModel")}
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
              {t("verification.colSkillB0")}
            </th>
            <th scope="col" className="num">
              {t("verification.colSkillB1")}
            </th>
          </tr>
        </thead>
        {variables.map((v) => (
          <tbody key={v.var}>
            <tr className="group-row">
              <th scope="rowgroup" colSpan={7}>
                {t("verification.varGroup", {
                  variable: t(`vars.${v.var}`),
                  n: formatCount(v.n, lang),
                })}
              </th>
            </tr>
            {v.metrics.map((m) => (
              <MetricTableRow key={m.name} row={m} lang={lang} />
            ))}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function MetricTableRow({ row, lang }: { row: MetricRow; lang: Lang }) {
  const { t } = useTranslation();
  const values = SCORE_KEYS.map((k) => row[k]);
  const best = new Set(bestIndexes(values, METRIC_BETTER[row.name] ?? "lower"));
  const digits = rowDigits(values, METRIC_DIGITS[row.name] ?? 2);
  const unit = t(`units.${row.unit}`, { defaultValue: row.unit });

  return (
    <tr data-metric={row.name}>
      <th scope="row">
        {t(`verification.metrics.${row.name}`, { defaultValue: row.name })}
        <span className="cell-sub">{unit}</span>
      </th>
      {values.map((v, i) => (
        <td key={SCORE_KEYS[i]} className={best.has(i) ? "num is-best" : "num"}>
          {best.has(i) ? (
            <strong>{formatFixed(v, lang, digits)}</strong>
          ) : (
            formatFixed(v, lang, digits)
          )}
        </td>
      ))}
      <SkillCell skill={row.skill_vs_b0} ci={row.skill_ci95} lang={lang} />
      <SkillCell skill={row.skill_vs_b1 ?? null} ci={row.skill_vs_b1_ci95 ?? null} lang={lang} />
    </tr>
  );
}

/** Skill with its interval and what the interval says, in words ("worse", not a colour). */
export function SkillCell({
  skill,
  ci,
  lang,
}: {
  skill: number | null;
  ci: readonly number[] | null;
  lang: Lang;
}) {
  const { t } = useTranslation();
  if (skill === null) return <td className="num">–</td>;
  const reading = readSkill(ci);
  return (
    <td className="num skill-cell" data-reading={reading}>
      {formatSkill(skill, lang)}
      <span className="cell-sub">
        {ci && ci.length === 2
          ? `${t("verification.interval", {
              lo: formatSkill(ci[0], lang),
              hi: formatSkill(ci[1], lang),
            })}, `
          : null}
        {t(`verification.readings.${reading}`)}
      </span>
    </td>
  );
}
