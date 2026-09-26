import { Sun } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useFarmer, useFarmerAdvice } from "../../api/hooks";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { DEMO_FARMER_ID } from "../../lib/config";
import { formatDate } from "../../lib/format";
import { pickText } from "../../lib/text";
import { useAppStore } from "../../state/store";

/** Today (Guide 7). Only advice an officer approved reaches this screen. */
export default function FarmerToday() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const farmer = useFarmer(DEMO_FARMER_ID);
  const advice = useFarmerAdvice(DEMO_FARMER_ID, issueDate);

  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.todayTitle")}</h1>
        <p className="muted">
          {farmer.data ? t("farmer.village", { pid: farmer.data.panchayat_id }) : null}
          {issueDate ? ` · ${formatDate(issueDate, lang)}` : null}
        </p>
      </header>
      <QueryBoundary
        query={advice}
        what={t("what.farmerAdvice")}
        isEmpty={(a) => a.items.length === 0}
        empty={
          <EmptyState icon={Sun} title={t("farmer.emptyTitle")}>
            <p>{t("farmer.emptyBody")}</p>
          </EmptyState>
        }
      >
        {(a) => (
          <section className="panel">
            <h2 className="panel-pad">{t("farmer.approvedTitle", { count: a.items.length })}</h2>
            <ul className="divided">
              {a.items.map((item) => {
                const action = pickText(item.action, lang);
                return (
                  <li key={item.id} lang={action.lang} className="farmer-advice">
                    {action.text}
                  </li>
                );
              })}
            </ul>
          </section>
        )}
      </QueryBoundary>
    </div>
  );
}
