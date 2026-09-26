import { useId } from "react";
import { useTranslation } from "react-i18next";
import { useGeoPanchayats, useMeta } from "../../api/hooks";
import type { PanchayatCollection, Var } from "../../api/types";
import { SegmentedControl } from "../../components/SegmentedControl";
import { LEAD_DAYS } from "../../lib/config";
import { addDays, formatDate } from "../../lib/format";
import { useAppStore, type ViewMode } from "../../state/store";

/** Left column of the map explorer: day, variable, view, risk layer and a Panchayat picker. */
export function MapControls() {
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
      <RiskLayerSelect />
      <PanchayatPicker />
    </aside>
  );
}

/** Present but disabled until the risk endpoint is wired into the map (S9). */
function RiskLayerSelect() {
  const { t } = useTranslation();
  const id = useId();
  return (
    <div className="field-stack">
      <label htmlFor={id}>{t("map.riskLayer")}</label>
      <select
        id={id}
        disabled
        aria-describedby={`${id}-hint`}
        value="none"
        onChange={() => undefined}
      >
        <option value="none">{t("map.riskNone")}</option>
      </select>
      <p id={`${id}-hint`} className="muted small">
        {t("map.riskHint")}
      </p>
    </div>
  );
}

/** Keyboard route to a Panchayat without the map; the table view is the fuller one. */
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
        {[...byBlock].map(([block, items]) => (
          <optgroup key={block} label={t("map.blockLabel", { block })}>
            {items.map(({ pid, name }) => (
              <option key={pid} value={pid}>
                {name}
              </option>
            ))}
          </optgroup>
        ))}
      </select>
    </div>
  );
}

function groupByBlock(
  geo: PanchayatCollection | undefined,
): Map<string, { pid: string; name: string }[]> {
  const out = new Map<string, { pid: string; name: string }[]>();
  for (const f of geo?.features ?? []) {
    const { block_id, panchayat_id, name } = f.properties;
    out.set(block_id, [...(out.get(block_id) ?? []), { pid: panchayat_id, name }]);
  }
  return out;
}
