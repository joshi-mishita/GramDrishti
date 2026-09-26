import { MousePointerClick, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastMap, useGeoPanchayats } from "../../api/hooks";
import type { PanchayatMapValue } from "../../api/types";
import { ProvenanceNote } from "../../components/ProvenanceNote";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { VAR_DIGITS, formatDate, formatSigned, formatValue } from "../../lib/format";
import { useAppStore } from "../../state/store";
import { ChangeList } from "./ChangeList";
import { DayDetails } from "./DayDetails";
import { ExplainList } from "./ExplainList";
import { ForecastChart } from "./ForecastChart";
import { useRangeText } from "./useRangeText";

/**
 * Right panel (Guide 6.1), top to bottom: name and block, the chosen day's value with a
 * plain range, the 5-day fan chart, all variables for the day, why it differs from the
 * block, and what changed since the previous forecast. Advisories follow in S9.
 */
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
          <ForecastChart pid={selectedPid} />
          <DayDetails pid={selectedPid} />
          <ExplainList pid={selectedPid} />
          <ChangeList pid={selectedPid} />
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
