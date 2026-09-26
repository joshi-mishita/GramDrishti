import { useState } from "react";
import { ChartLine } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastPanchayat, useObserved } from "../../api/hooks";
import { VARS, type Observed, type PanchayatForecast, type Var } from "../../api/types";
import { QueryBoundary } from "../../components/QueryBoundary";
import { SegmentedControl } from "../../components/SegmentedControl";
import { EmptyState } from "../../components/states";
import { hasAnyValue, hasObserved, shapeFanRows } from "../../lib/fan";
import { addDays } from "../../lib/format";
import { UNITS } from "../../lib/ramps";
import { useAppStore } from "../../state/store";
import { FanChart } from "./FanChart";

/**
 * 5-day fan chart for the selected Panchayat, with its own variable switch (the same
 * variable as the map, D059) and the "Show what happened" overlay.
 */
export function ForecastChart({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const issueDate = useAppStore((s) => s.issueDate);
  const forecast = useForecastPanchayat(pid, issueDate);

  return (
    <section aria-labelledby="fan-title">
      <h3 id="fan-title" className="section-title">
        {t("panel.chartTitle")}
      </h3>
      <QueryBoundary query={forecast} what={t("what.forecastPanchayat")} skeletonLines={6}>
        {(f) => <ChartBody forecast={f} />}
      </QueryBoundary>
    </section>
  );
}

function ChartBody({ forecast }: { forecast: PanchayatForecast }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const leadDay = useAppStore((s) => s.leadDay);
  const variable = useAppStore((s) => s.variable);
  const setVariable = useAppStore((s) => s.setVariable);
  const [showObserved, setShowObserved] = useState(false);

  const dates = forecast.days.map((d) => d.date).sort();
  const from = dates[0] ?? null;
  const to = dates[dates.length - 1] ?? null;
  const observed = useObserved(forecast.panchayat_id, from, to, showObserved);

  const obsDays = showObserved ? observed.data?.days : undefined;
  const rows = shapeFanRows(forecast.days, variable, obsDays);
  const unit = t(`units.${UNITS[variable]}`);
  const selectedDate = addDays(forecast.issue_date, leadDay);

  return (
    <div className="stack">
      <SegmentedControl<Var>
        legend={t("panel.chartVar")}
        name="panel-variable"
        value={variable}
        variant="wrap"
        options={VARS.map((v) => ({ value: v, label: t(`varsShort.${v}`) }))}
        onChange={setVariable}
      />
      {hasAnyValue(rows) ? (
        <FanChart
          rows={rows}
          variable={variable}
          unit={unit}
          lang={lang}
          showObserved={showObserved && hasObserved(rows)}
          selectedDate={dates.includes(selectedDate) ? selectedDate : undefined}
        />
      ) : (
        <EmptyState icon={ChartLine} title={t("panel.chartEmptyTitle")}>
          <p>{t("panel.chartEmptyBody", { variable: t(`vars.${variable}`) })}</p>
        </EmptyState>
      )}
      <label className="check">
        <input
          type="checkbox"
          checked={showObserved}
          onChange={(e) => setShowObserved(e.target.checked)}
        />
        {t("panel.showObserved")}
      </label>
      {showObserved ? (
        <QueryBoundary query={observed} what={t("what.observed")} skeletonLines={1}>
          {(o) => (
            <ObservedSourceNote observed={o} variable={variable} anyShown={hasObserved(rows)} />
          )}
        </QueryBoundary>
      ) : null}
    </div>
  );
}

/** Says where the observed points come from, and why there are none when there are none. */
function ObservedSourceNote({
  observed,
  variable,
  anyShown,
}: {
  observed: Observed;
  variable: Var;
  anyShown: boolean;
}) {
  const { t } = useTranslation();
  if (observed.source === "none") return <p className="muted small">{t("panel.sourceNone")}</p>;
  const source =
    observed.source === "station"
      ? t("panel.sourceStation", { station: observed.station_id ?? "" })
      : t("panel.sourceTruth");
  return (
    <div className="muted small">
      <p>{source}</p>
      {anyShown ? null : (
        <p>{t("panel.observedNoneForVar", { variable: t(`vars.${variable}`) })}</p>
      )}
    </div>
  );
}
