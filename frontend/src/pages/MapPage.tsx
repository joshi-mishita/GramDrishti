import { useId } from "react";
import { MapPinned, MousePointerClick, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastMap, useGeoBlocks, useGeoPanchayats, useMeta } from "../api/hooks";
import type { PanchayatCollection, Var } from "../api/types";
import { SegmentedControl } from "../components/SegmentedControl";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { EmptyState } from "../components/states";
import { LEAD_DAYS } from "../lib/config";
import { addDays, formatDate, formatNumber } from "../lib/format";
import { useAppStore, type ViewMode } from "../state/store";

/** Map explorer (Guide 6.1). This version has the controls and data; drawing comes next. */
export default function MapPage() {
  const { t } = useTranslation();
  return (
    <div className="map-page">
      <h1 className="visually-hidden">{t("map.title")}</h1>
      <MapControls />
      <section className="map-area" aria-label={t("map.areaLabel")}>
        <MapPlaceholder />
      </section>
      <DetailPanel />
    </div>
  );
}

function MapControls() {
  const { t } = useTranslation();
  const meta = useMeta();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const setLeadDay = useAppStore((s) => s.setLeadDay);
  const variable = useAppStore((s) => s.variable);
  const setVariable = useAppStore((s) => s.setVariable);
  const viewMode = useAppStore((s) => s.viewMode);
  const setViewMode = useAppStore((s) => s.setViewMode);

  const dayOptions = LEAD_DAYS.map((d) => ({
    value: String(d),
    label: issueDate ? formatDate(addDays(issueDate, d), lang, "day") : String(d),
  }));
  const varOptions = (meta.data?.vars ?? []).map((v) => ({
    value: v.var,
    label: t(`vars.${v.var}`),
    hint: t(`units.${v.unit}`, { defaultValue: v.unit }),
  }));

  return (
    <aside className="map-controls toolbar" aria-label={t("map.controls")}>
      <SegmentedControl
        legend={t("map.day")}
        showLegend
        name="lead-day"
        variant="wrap"
        value={String(leadDay)}
        options={dayOptions}
        onChange={(v) => setLeadDay(Number(v))}
      />
      {varOptions.length ? (
        <SegmentedControl<Var>
          legend={t("map.show")}
          showLegend
          name="variable"
          variant="list"
          value={variable}
          options={varOptions}
          onChange={setVariable}
        />
      ) : null}
      <SegmentedControl<ViewMode>
        legend={t("map.view")}
        showLegend
        name="view-mode"
        variant="list"
        value={viewMode}
        options={[
          { value: "block", label: t("viewModes.block") },
          { value: "panchayat", label: t("viewModes.panchayat") },
          { value: "delta", label: t("viewModes.delta") },
        ]}
        onChange={setViewMode}
      />
      <PanchayatPicker />
    </aside>
  );
}

/** Keyboard route to a Panchayat until the map is drawn; later it stays as the table alternative. */
function PanchayatPicker() {
  const { t } = useTranslation();
  const id = useId();
  const geo = useGeoPanchayats();
  const selectedPid = useAppStore((s) => s.selectedPid);
  const setSelectedPid = useAppStore((s) => s.setSelectedPid);
  const byBlock = groupByBlock(geo.data);
  return (
    <div className="field-stack">
      <label htmlFor={id}>{t("map.jumpTo")}</label>
      <select
        id={id}
        value={selectedPid ?? ""}
        disabled={!geo.data}
        onChange={(e) => setSelectedPid(e.target.value || null)}
      >
        <option value="">{t("map.jumpNone")}</option>
        {[...byBlock].map(([block, pids]) => (
          <optgroup key={block} label={t("map.blockLabel", { block })}>
            {pids.map((pid) => (
              <option key={pid} value={pid}>
                {pid}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}

function groupByBlock(geo: PanchayatCollection | undefined): Map<string, string[]> {
  const out = new Map<string, string[]>();
  for (const f of geo?.features ?? []) {
    const { block_id, panchayat_id } = f.properties;
    out.set(block_id, [...(out.get(block_id) ?? []), panchayat_id]);
  }
  return out;
}

function MapPlaceholder() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const variable = useAppStore((s) => s.variable);
  const geo = useGeoPanchayats();
  const blocks = useGeoBlocks();
  const forecast = useForecastMap(issueDate, leadDay, variable);

  return (
    <div className="map-stack">
      <QueryBoundary query={geo} what={t("what.geo")}>
        {(g) => (
          <EmptyState icon={MapPinned} title={t("map.notBuiltTitle")}>
            <p>{t("map.notBuiltBody")}</p>
            <p className="facts">
              {t("map.loadedGeo", {
                panchayats: g.features.length,
                blocks: blocks.data?.features.length ?? groupByBlock(g).size,
              })}
            </p>
          </EmptyState>
        )}
      </QueryBoundary>
      <QueryBoundary
        query={forecast}
        what={t("what.forecastMap")}
        isEmpty={(f) => f.panchayat_layer.length === 0}
        empty={<EmptyState title={t("map.noValues")} />}
      >
        {(f) => {
          const values = f.block_layer.map((b) => b.value).filter((v): v is number => v !== null);
          return (
            <div className="panel panel-pad">
              <h2>
                {t(`vars.${f.var}`)}, {formatDate(f.valid_date, lang)}
              </h2>
              <p className="facts">
                {t("map.loadedValues", {
                  count: f.panchayat_layer.length,
                  min: formatNumber(values.length ? Math.min(...values) : null, lang),
                  max: formatNumber(values.length ? Math.max(...values) : null, lang),
                  unit: t(`units.${f.unit}`, { defaultValue: f.unit }),
                })}
              </p>
              <ProvenanceNote provenance={f.provenance} />
            </div>
          );
        }}
      </QueryBoundary>
    </div>
  );
}

function DetailPanel() {
  const { t } = useTranslation();
  const selectedPid = useAppStore((s) => s.selectedPid);
  const setSelectedPid = useAppStore((s) => s.setSelectedPid);
  const geo = useGeoPanchayats();
  const feature = geo.data?.features.find((f) => f.properties.panchayat_id === selectedPid);

  return (
    <aside className="detail-panel" aria-label={t("map.panelLabel")}>
      {selectedPid ? (
        <>
          <div className="detail-head">
            <div>
              <h2>{feature?.properties.name ?? selectedPid}</h2>
              {feature ? (
                <p className="muted">
                  {t("map.blockLabel", { block: feature.properties.block_id })}
                </p>
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
            <p className="muted">{t("map.panelNotBuilt")}</p>
          )}
        </>
      ) : (
        <EmptyState icon={MousePointerClick} title={t("map.panelEmptyTitle")}>
          <p>{t("map.panelEmptyBody")}</p>
        </EmptyState>
      )}
    </aside>
  );
}
