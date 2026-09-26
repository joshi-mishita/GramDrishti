import { useTranslation } from "react-i18next";
import { useFarmer } from "../../api/hooks";
import { LANG_OPTIONS } from "../../lib/langs";
import { QueryBoundary } from "../../components/QueryBoundary";
import { DEMO_FARMER_ID } from "../../lib/config";
import { formatDate } from "../../lib/format";
import { useAppStore } from "../../state/store";

/** My farm (Guide 7): the demo farmer's Panchayat, language and crops from /farmers/{id}. */
export default function FarmerFarm() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const farmer = useFarmer(DEMO_FARMER_ID);

  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.farmTitle")}</h1>
      </header>
      <QueryBoundary query={farmer} what={t("what.farmer")}>
        {(f) => {
          const langOpt = LANG_OPTIONS.find((o) => o.value === f.language);
          return (
            <section className="panel">
              <dl className="kv">
                <div>
                  <dt>{t("farmer.panchayat")}</dt>
                  <dd>{f.panchayat_id}</dd>
                </div>
                <div>
                  <dt>{t("farmer.language")}</dt>
                  <dd lang={langOpt?.lang}>{langOpt?.label ?? f.language}</dd>
                </div>
              </dl>
              <h2 className="panel-pad">{t("farmer.crops")}</h2>
              <ul className="divided">
                {f.crops.map((c) => (
                  <li key={`${c.crop}-${c.season}`} className="crop-row">
                    <span>{t(`crops.${c.crop}`, { defaultValue: c.crop })}</span>
                    <span className="muted">
                      {t("farmer.sown", { date: formatDate(c.sowing_date, lang) })}
                    </span>
                  </li>
                ))}
              </ul>
              <p className="panel-pad muted small">{t("farmer.demoNote")}</p>
            </section>
          );
        }}
      </QueryBoundary>
    </div>
  );
}
