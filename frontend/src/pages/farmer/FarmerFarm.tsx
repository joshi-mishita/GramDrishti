import { useState } from "react";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useMeta } from "../../api/hooks";
import type { Farmer } from "../../api/types";
import { QueryBoundary } from "../../components/QueryBoundary";
import { FeedbackCard } from "../../features/farmer/FeedbackCard";
import { useFarmerContext } from "../../features/farmer/useFarmerContext";
import { formatDate } from "../../lib/format";
import { LANG_OPTIONS } from "../../lib/langs";
import { useAppStore } from "../../state/store";

interface CropRow {
  key: string;
  crop: string;
  sowing_date: string;
}

const toRows = (f: Farmer): CropRow[] =>
  f.crops.map((c, i) => ({
    key: `${c.crop}-${c.season}-${i}`,
    crop: c.crop,
    sowing_date: c.sowing_date,
  }));

/**
 * Crops with sowing dates. Editing is local state only in the prototype (Guide 7): the
 * change is not saved or sent, and the advice does not follow it. The screen says so.
 */
function Crops({ farmer }: { farmer: Farmer }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const meta = useMeta();
  const [rows, setRows] = useState<CropRow[]>(() => toRows(farmer));
  const [draft, setDraft] = useState<CropRow[] | null>(null);
  const [changed, setChanged] = useState(false);
  const cropNames = meta.data?.crops ?? [...new Set(rows.map((r) => r.crop))];
  const cropLabel = (c: string) => t(`crops.${c}`, { defaultValue: c });

  if (draft) {
    const update = (key: string, patch: Partial<CropRow>) =>
      setDraft(draft.map((r) => (r.key === key ? { ...r, ...patch } : r)));
    return (
      <section className="panel" aria-labelledby="crops-title">
        <h2 id="crops-title" className="panel-pad">
          {t("farmer.crops")}
        </h2>
        <ul className="divided crop-edit">
          {draft.map((r) => (
            <li key={r.key}>
              <label>
                <span>{t("farmer.cropLabel")}</span>
                <select value={r.crop} onChange={(e) => update(r.key, { crop: e.target.value })}>
                  {cropNames.map((c) => (
                    <option key={c} value={c}>
                      {cropLabel(c)}
                    </option>
                  ))}
                </select>
              </label>
              <label>
                <span>{t("farmer.sowingLabel")}</span>
                <input
                  type="date"
                  value={r.sowing_date}
                  onChange={(e) => update(r.key, { sowing_date: e.target.value })}
                />
              </label>
              <button
                type="button"
                className="btn btn-icon"
                aria-label={t("farmer.removeCrop", { crop: cropLabel(r.crop) })}
                onClick={() => setDraft(draft.filter((x) => x.key !== r.key))}
              >
                <Trash2 size={18} aria-hidden="true" />
              </button>
            </li>
          ))}
        </ul>
        <div className="panel-pad stack">
          <button
            type="button"
            className="btn btn-farmer"
            onClick={() =>
              setDraft([
                ...draft,
                {
                  key: `new-${draft.length}-${Date.now()}`,
                  crop: cropNames[0] ?? "wheat",
                  sowing_date: issueDate ?? "",
                },
              ])
            }
          >
            <Plus size={20} aria-hidden="true" />
            {t("farmer.addCrop")}
          </button>
          <p className="muted small">{t("farmer.localOnly")}</p>
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-farmer btn-primary"
              onClick={() => {
                setRows(draft.filter((r) => r.sowing_date));
                setDraft(null);
                setChanged(true);
              }}
            >
              {t("farmer.saveCrops")}
            </button>
            <button type="button" className="btn btn-farmer" onClick={() => setDraft(null)}>
              {t("farmer.cancelEdit")}
            </button>
          </div>
        </div>
      </section>
    );
  }

  return (
    <section className="panel" aria-labelledby="crops-title">
      <h2 id="crops-title" className="panel-pad">
        {t("farmer.crops")}
      </h2>
      {rows.length ? (
        <ul className="divided">
          {rows.map((r) => (
            <li key={r.key} className="crop-row">
              <span>{cropLabel(r.crop)}</span>
              <span className="muted">
                {t("farmer.sown", { date: formatDate(r.sowing_date, lang) })}
              </span>
            </li>
          ))}
        </ul>
      ) : (
        <p className="panel-pad">{t("farmer.noCrops")}</p>
      )}
      <div className="panel-pad stack">
        {changed ? <p className="muted small">{t("farmer.edited")}</p> : null}
        <button type="button" className="btn btn-farmer" onClick={() => setDraft(rows)}>
          <Pencil size={20} aria-hidden="true" />
          {t("farmer.editCrops")}
        </button>
      </div>
    </section>
  );
}

/** My farm (Guide 7): Panchayat, language, crops with sowing dates, and the rain question. */
export default function FarmerFarm() {
  const { t } = useTranslation();
  const { farmer, village } = useFarmerContext();

  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.farmTitle")}</h1>
      </header>
      <QueryBoundary query={farmer} what={t("what.farmer")}>
        {(f) => {
          const langOpt = LANG_OPTIONS.find((o) => o.value === f.language);
          return (
            <>
              <section className="panel">
                <dl className="kv">
                  <div>
                    <dt>{t("farmer.panchayat")}</dt>
                    <dd>{village || f.panchayat_id}</dd>
                  </div>
                  <div>
                    <dt>{t("farmer.block")}</dt>
                    <dd>{f.block_id}</dd>
                  </div>
                  <div>
                    <dt>{t("farmer.language")}</dt>
                    <dd lang={langOpt?.lang}>{langOpt?.label ?? f.language}</dd>
                  </div>
                </dl>
                <p className="panel-pad muted small">{t("farmer.demoNote")}</p>
              </section>
              {/* key: another demo farmer starts from their own crops, not the last edits */}
              <Crops key={f.farmer_id} farmer={f} />
              <FeedbackCard pid={f.panchayat_id} />
            </>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
