import { ChartLine, MousePointerClick, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastMap, useForecastPanchayat, useGeoPanchayats } from "../../api/hooks";
import { VARS, type ForecastDay, type Lang, type PanchayatMapValue } from "../../api/types";
import { ProvenanceNote } from "../../components/ProvenanceNote";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { VAR_DIGITS, addDays, formatDate, formatSigned, formatValue } from "../../lib/format";
import { UNITS } from "../../lib/ramps";
import { useAppStore } from "../../state/store";
import { useRangeText } from "./useRangeText";

/** Right panel, first version (Guide 6.1): headline value, block comparison, all variables. */
export function DetailPanel() {
  const { t } = useTranslation();
  const selectedPid = useAppStore((s) => s.selectedPid);
  const setSelectedPid = useAppStore((s) => s.setSelectedPid);
  const geo = useGeoPanchayats();
  const feature = geo.data?.features.find((f) => f.properties.panchayat_id === selectedPid);

  if (!selectedPid) {
    return (
      <aside className="detail-panel" aria-label={t("map.panelLabel")}>
        <EmptyState icon={MousePointerClick} title={t("map.panelEmptyTitle")}>
          <p>{t("map.panelEmptyBody")}</p>
        </EmptyState>
      </aside>
    );
  }

  return (
    <aside className="detail-panel" aria-label={t("map.panelLabel")}>
      <div className="detail-head">
        <div>
          <h2>{feature?.properties.name ?? selectedPid}</h2>
          {feature ? (
            <p className="muted">{t("map.blockLabel", { block: feature.properties.block_id })}</p>
          ) : null}
        </div>
        <button
          type="button"
          className="btn btn-icon"
          onClick={() => setSelectedPid(null)}
          aria-label={t("map.clearSelection")}
        >
          <X size={18} aria-hidden="true" />
        </button>
      </div>
      {geo.data && !feature ? (
        <EmptyState title={t("map.unknownPid", { pid: selectedPid })} />
      ) : (
        <div className="detail-body">
          <Headline pid={selectedPid} />
          <section aria-labelledby="fan-slot-title">
            <h3 id="fan-slot-title" className="section-title">
              {t("panel.chartTitle")}
            </h3>
            <EmptyState icon={ChartLine} title={t("panel.chartEmptyTitle")}>
              <p>{t("panel.chartEmptyBody")}</p>
            </EmptyState>
          </section>
          <AllVariables pid={selectedPid} />
        </div>
      )}
    </aside>
  );
}

/** The chosen variable on the chosen day, from the map layer already on screen. */
function Headline({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const variable = useAppStore((s) => s.variable);
  const forecast = useForecastMap(issueDate, leadDay, variable);
  const rangeText = useRangeText();

  return (
    <QueryBoundary query={forecast} what={t("what.forecastMap")} skeletonLines={3}>
      {(f) => {
        const row: PanchayatMapValue | undefined = f.panchayat_layer.find(
          (r) => r.panchayat_id === pid,
        );
        const unit = t(`units.${f.unit}`, { defaultValue: f.unit });
        const digits = VAR_DIGITS[f.var];
        return (
          <section className="headline" aria-labelledby="headline-title">
            <h3 id="headline-title" className="section-title">
              {t("panel.valueOn", {
                variable: t(`vars.${f.var}`),
                date: formatDate(f.valid_date, lang, "day"),
              })}
            </h3>
            {row ? (
              <>
                <p className="headline-value">{formatValue(row.p50, unit, lang, digits)}</p>
                <p className="headline-range">{rangeText(row.p10, row.p90, f.var, lang)}</p>
                <dl className="kv-compact">
                  <div>
                    <dt>{t("panel.blockForecast")}</dt>
                    <dd>{formatValue(row.block_value, unit, lang, digits)}</dd>
                  </div>
                  <div>
                    <dt>{t("panel.difference")}</dt>
                    <dd>
                      {row.delta === null
                        ? "–"
                        : `${formatSigned(row.delta, lang, digits)} ${unit}`}
                    </dd>
                  </div>
                </dl>
              </>
            ) : (
              <p className="muted">{t("panel.notInLayer")}</p>
            )}
            <ProvenanceNote provenance={f.provenance} />
          </section>
        );
      }}
    </QueryBoundary>
  );
}

/** Small table of every variable for the chosen day, from /forecast/panchayat. */
function AllVariables({ pid }: { pid: string }) {
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
        {(f) => (
          <VarTable day={f.days.find((d) => d.lead_day === leadDay) as ForecastDay} lang={lang} />
        )}
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
