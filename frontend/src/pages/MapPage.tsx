import { useMemo, useState } from "react";
import { Map as MapIcon, Table } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastMap, useGeoBlocks, useGeoPanchayats, useRisk } from "../api/hooks";
import type { ForecastMap, Level, PanchayatCollection } from "../api/types";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { RiskChip } from "../components/RiskChip";
import { EmptyState } from "../components/states";
import { DetailPanel } from "../features/map/DetailPanel";
import { Legend } from "../features/map/Legend";
import { MapControls } from "../features/map/MapControls";
import { MapView } from "../features/map/MapView";
import { PanchayatTable } from "../features/map/PanchayatTable";
import { RiskLegend } from "../features/map/RiskLegend";
import {
  isFlatWithinBlocks,
  rampForMode,
  riskLevels,
  riskValues,
  valuesForMode,
} from "../features/map/mapData";
import { cssVar } from "../lib/cssVar";
import { riskRamp } from "../lib/ramps";
import {
  VAR_DIGITS,
  addDays,
  formatDate,
  formatNumber,
  formatSigned,
  formatValue,
} from "../lib/format";
import { useAppStore } from "../state/store";

/** Map explorer (Guide 6.1): controls | map or table | detail panel. */
export default function MapPage() {
  const { t } = useTranslation();
  return (
    <div className="map-page">
      <h1 className="visually-hidden">{t("map.title")}</h1>
      <MapControls />
      <MapArea />
      <DetailPanel />
    </div>
  );
}

const EMPTY = new Map<string, number | null>();

function MapArea() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const variable = useAppStore((s) => s.variable);
  const viewMode = useAppStore((s) => s.viewMode);
  const selectedPid = useAppStore((s) => s.selectedPid);
  const setSelectedPid = useAppStore((s) => s.setSelectedPid);
  const [showTable, setShowTable] = useState(false);
  const geo = useGeoPanchayats();
  const blocks = useGeoBlocks();
  const riskType = useAppStore((s) => s.riskType);
  const forecast = useForecastMap(issueDate, leadDay, variable);
  const risk = useRisk(issueDate, leadDay, riskType);

  // View mode is not part of the query key: switching it reuses the loaded layer.
  const data = forecast.data;
  const riskData = riskType ? risk.data : undefined;
  const values = useMemo(() => {
    if (riskType) return riskData ? riskValues(riskData) : EMPTY;
    return data ? valuesForMode(data.panchayat_layer, viewMode) : EMPTY;
  }, [data, viewMode, riskType, riskData]);
  const ramp = useMemo(() => {
    if (riskType) return riskData ? riskRamp(cssVar) : null;
    return data ? rampForMode(data, viewMode) : null;
  }, [data, viewMode, riskType, riskData]);
  const levels = useMemo(() => riskLevels(riskData), [riskData]);
  const rowsById = useMemo(
    () => new Map(data?.panchayat_layer.map((r) => [r.panchayat_id, r]) ?? []),
    [data],
  );

  const varLabel = t(`vars.${variable}`);
  const validDate = data ? formatDate(data.valid_date, lang) : "";
  const unit = data ? t(`units.${data.unit}`, { defaultValue: data.unit }) : "";

  const renderTooltip = (pid: string) => {
    const name =
      geo.data?.features.find((f) => f.properties.panchayat_id === pid)?.properties.name ?? pid;
    const r = rowsById.get(pid);
    const digits = VAR_DIGITS[variable];
    const level = levels.get(pid);
    return (
      <>
        <strong>{name}</strong>
        {riskType ? (
          <p className="tooltip-risk">
            <span>{t("risk.tooltip", { risk: t(`risks.${riskType}`) })}</span>
            {level ? <RiskChip level={level} /> : <span>{t("legend.noValue")}</span>}
          </p>
        ) : null}
        {r && data ? (
          <dl>
            <div>
              <dt>{t("tooltip.value")}</dt>
              <dd>{formatValue(r.p50, unit, lang, digits)}</dd>
            </div>
            <div>
              <dt>{t("tooltip.range")}</dt>
              <dd>
                {r.p10 === null || r.p90 === null
                  ? "–"
                  : `${formatNumber(r.p10, lang, digits)} – ${formatValue(r.p90, unit, lang, digits)}`}
              </dd>
            </div>
            {viewMode !== "panchayat" && !riskType ? (
              <div>
                <dt>{viewMode === "block" ? t("tooltip.block") : t("tooltip.delta")}</dt>
                <dd>
                  {viewMode === "block"
                    ? formatValue(r.block_value, unit, lang, digits)
                    : r.delta === null
                      ? "–"
                      : `${formatSigned(r.delta, lang, digits)} ${unit}`}
                </dd>
              </div>
            ) : null}
          </dl>
        ) : (
          <p>{t("legend.noValue")}</p>
        )}
      </>
    );
  };

  return (
    <section className="map-area" aria-labelledby="map-heading">
      <div className="map-head">
        <h2 id="map-heading">
          {riskType && issueDate
            ? t("risk.heading", {
                risk: t(`risks.${riskType}`),
                date: formatDate(riskData?.valid_date ?? addDays(issueDate, leadDay), lang),
              })
            : data
              ? t("map.heading", {
                  variable: varLabel,
                  date: validDate,
                  view: t(`viewModes.${viewMode}`),
                })
              : varLabel}
        </h2>
        <button
          type="button"
          className="btn"
          aria-pressed={showTable}
          onClick={() => setShowTable((v) => !v)}
          disabled={!geo.data || !data}
        >
          {showTable ? (
            <MapIcon size={16} aria-hidden="true" />
          ) : (
            <Table size={16} aria-hidden="true" />
          )}
          {showTable ? t("map.showMap") : t("map.showTable")}
        </button>
      </div>

      {forecast.isSuccess ? null : (
        <QueryBoundary query={forecast} what={t("what.forecastMap")} skeletonLines={1}>
          {() => null}
        </QueryBoundary>
      )}
      {riskType && !risk.isSuccess ? (
        <QueryBoundary query={risk} what={t("what.risk")} skeletonLines={1}>
          {() => null}
        </QueryBoundary>
      ) : null}
      {riskData && riskData.items.length === 0 ? <EmptyState title={t("risk.noItems")} /> : null}
      {data && data.panchayat_layer.length === 0 ? <EmptyState title={t("map.noValues")} /> : null}
      {!riskType && data && isFlatWithinBlocks(data.panchayat_layer) ? (
        <p className="map-note">{t("map.flatNote")}</p>
      ) : null}

      <QueryBoundary query={geo} what={t("what.geo")} skeletonLines={6}>
        {(g) => (
          <>
            <div className="map-wrap" hidden={showTable}>
              <MapView
                panchayats={g}
                blocks={blocks.data}
                values={values}
                ramp={ramp}
                selectedPid={selectedPid}
                onSelect={setSelectedPid}
                renderTooltip={renderTooltip}
                label={t("map.regionLabel", { variable: varLabel })}
                paintKey={`${issueDate}|${leadDay}|${variable}|${viewMode}|${forecast.status}|${riskType}|${risk.status}`}
                fallback={
                  <EmptyState title={t("map.noWebglTitle")}>
                    <p>{t("map.noWebglBody")}</p>
                  </EmptyState>
                }
              />
              {riskType && riskData ? (
                <div className="map-legend">
                  <RiskLegend
                    type={riskType}
                    placeholder={riskData.thresholds_status === "placeholder"}
                  />
                </div>
              ) : null}
              {!riskType && ramp && data ? (
                <div className="map-legend">
                  <Legend
                    ramp={ramp}
                    title={viewMode === "delta" ? t("viewModes.delta") : varLabel}
                    unitLabel={unit}
                    lang={lang}
                    caption={viewMode === "delta" ? t("legend.deltaCaption") : undefined}
                  />
                </div>
              ) : null}
            </div>
            {showTable ? <TableView data={data} geo={g} levels={riskType ? levels : null} /> : null}
          </>
        )}
      </QueryBoundary>
      {data ? <ProvenanceNote provenance={data.provenance} /> : null}
      {riskData ? <ProvenanceNote provenance={riskData.provenance} /> : null}
    </section>
  );
}

interface TableViewProps {
  data: ForecastMap | undefined;
  geo: PanchayatCollection;
  levels: ReadonlyMap<string, Level> | null;
}

function TableView({ data, geo, levels }: TableViewProps) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  if (!data) return null;
  return (
    <PanchayatTable
      forecast={data}
      geo={geo}
      levels={levels}
      caption={t("map.tableCaption", {
        variable: t(`vars.${data.var}`),
        date: formatDate(data.valid_date, lang),
      })}
    />
  );
}
