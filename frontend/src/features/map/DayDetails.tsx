import { useTranslation } from "react-i18next";
import { useForecastPanchayat } from "../../api/hooks";
import {
  RAIN_EVENTS,
  VARS,
  type Derived,
  type EventProbs,
  type ForecastDay,
  type Lang,
  type PanchayatForecast,
} from "../../api/types";
import { QueryBoundary } from "../../components/QueryBoundary";
import { RiskChip } from "../../components/RiskChip";
import { EmptyState } from "../../components/states";
import { VAR_DIGITS, addDays, formatDate, formatNumber, formatValue } from "../../lib/format";
import { UNITS } from "../../lib/ramps";
import { formatPercent, probWord } from "../../lib/words";
import { useAppStore } from "../../state/store";
import { useRangeText } from "./useRangeText";

/**
 * Everything about the chosen day, from /forecast/panchayat: all variables, the chance
 * of rain in words, and derived farm values with units.
 */
export function DayDetails({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const forecast = useForecastPanchayat(pid, issueDate);
  const date = issueDate ? formatDate(addDays(issueDate, leadDay), lang, "day") : "";

  return (
    <section aria-labelledby="allvars-title">
      <h3 id="allvars-title" className="section-title">
        {t("panel.allVars", { date })}
      </h3>
      <QueryBoundary
        query={forecast}
        what={t("what.forecastPanchayat")}
        isEmpty={(f) => !f.days.some((d) => d.lead_day === leadDay)}
        empty={<EmptyState title={t("panel.noDay")} />}
      >
        {(f) => {
          const day = f.days.find((d) => d.lead_day === leadDay) as ForecastDay;
          return (
            <div className="stack">
              <VarTable day={day} lang={lang} />
              <RainChances prob={day.prob} lang={lang} />
              <AgroValues derived={day.derived} forecast={f} lang={lang} />
            </div>
          );
        }}
      </QueryBoundary>
    </section>
  );
}

function VarTable({ day, lang }: { day: ForecastDay; lang: Lang }) {
  const { t } = useTranslation();
  const rangeText = useRangeText();
  return (
    <table className="data-table compact">
      <caption className="visually-hidden">
        {t("panel.allVars", { date: formatDate(day.date, lang, "day") })}
      </caption>
      <thead>
        <tr>
          <th scope="col">{t("table.variable")}</th>
          <th scope="col" className="num">
            {t("table.panchayatShort")}
          </th>
          <th scope="col" className="num">
            {t("table.blockShort")}
          </th>
        </tr>
      </thead>
      <tbody>
        {VARS.map((v) => {
          const q = day[v];
          const unit = t(`units.${UNITS[v]}`);
          return (
            <tr key={v}>
              <th scope="row">
                {t(`vars.${v}`)}
                <span className="cell-sub">{rangeText(q.p10, q.p90, v, lang)}</span>
              </th>
              <td className="num">{formatValue(q.p50, unit, lang, VAR_DIGITS[v])}</td>
              <td className="num">{formatValue(q.block, unit, lang, VAR_DIGITS[v])}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}

/** "Rain of 2.5 mm or more: likely, 71%". */
function RainChances({ prob, lang }: { prob: EventProbs; lang: Lang }) {
  const { t } = useTranslation();
  return (
    <div>
      <h4 className="subsection-title">{t("panel.rainChances")}</h4>
      <dl className="kv-compact">
        {RAIN_EVENTS.map((e) => {
          const p = prob[e];
          return (
            <div key={e}>
              <dt>{t(`events.${e}`)}</dt>
              <dd>
                {p === null
                  ? "–"
                  : t("panel.probValue", {
                      word: t(`probWords.${probWord(p)}`),
                      pct: formatPercent(p, lang),
                    })}
              </dd>
            </div>
          );
        })}
      </dl>
    </div>
  );
}

/** Formats a 0..1 fraction as a whole percent ("73%"), or null when missing. */
function fracText(v: number | null | undefined, lang: Lang): string | null {
  return v === null || v === undefined ? null : `${formatNumber(v * 100, lang, 0)}%`;
}

/** ET0, soil water, waterlogging and the other derived values the API sends for the day. */
function AgroValues({
  derived,
  forecast,
  lang,
}: {
  derived: Derived;
  forecast: PanchayatForecast;
  lang: Lang;
}) {
  const { t } = useTranslation();
  const soil = fracText(derived.soil_moisture_frac, lang);
  const soilDry = fracText(derived.soil_moisture_frac_dry, lang);
  const soilWet = fracText(derived.soil_moisture_frac_wet, lang);
  return (
    <div>
      <h4 className="subsection-title">{t("panel.agroTitle")}</h4>
      <dl className="kv-compact">
        <div>
          <dt>{t("panel.et0")}</dt>
          <dd>
            {derived.et0_mm === null
              ? "–"
              : t("panel.et0Value", { value: formatNumber(derived.et0_mm, lang, 1) })}
          </dd>
        </div>
        <div>
          <dt>{t("panel.soilWater")}</dt>
          <dd>
            {soil === null ? "–" : t("panel.soilWaterValue", { value: soil })}
            {soilDry !== null && soilWet !== null && soilDry !== soilWet ? (
              <span className="cell-sub">
                {t("panel.soilWaterRange", { lo: soilDry, hi: soilWet })}
              </span>
            ) : null}
          </dd>
        </div>
        <div>
          <dt>{t("panel.waterlog")}</dt>
          <dd>{derived.waterlog_risk ? <RiskChip level={derived.waterlog_risk} /> : "–"}</dd>
        </div>
        {derived.frost_risk !== undefined ? (
          <div>
            <dt>{t("panel.frost")}</dt>
            <dd>{derived.frost_risk ? <RiskChip level={derived.frost_risk} /> : "–"}</dd>
          </div>
        ) : null}
        <div>
          <dt>{t("panel.thi")}</dt>
          <dd>{formatNumber(derived.thi, lang, 0)}</dd>
        </div>
        {derived.dry_spell_days !== undefined ? (
          <div>
            <dt>{t("panel.drySpell")}</dt>
            <dd>
              {derived.dry_spell_days === null
                ? "–"
                : t("panel.drySpellValue", { count: derived.dry_spell_days })}
            </dd>
          </div>
        ) : null}
      </dl>
      {forecast.thresholds_status === "placeholder" ? (
        <p className="muted small">{t("thresholds.placeholder")}</p>
      ) : null}
    </div>
  );
}
