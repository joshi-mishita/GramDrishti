import { Printer, Sun } from "lucide-react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useFarmerAdvice } from "../../api/hooks";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { AdviceCard } from "../../features/farmer/AdviceCard";
import { useFarmerContext } from "../../features/farmer/useFarmerContext";
import { formatDate } from "../../lib/format";
import { useAppStore } from "../../state/store";

/**
 * Today (Guide 7): the most urgent approved advisory as a full-width block, the rest as a
 * plain list, and the printable bulletin. Only advice an officer approved reaches here.
 */
export default function FarmerToday() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const { farmerId, issueDate, pid, village } = useFarmerContext();
  const advice = useFarmerAdvice(farmerId, issueDate);

  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.todayTitle")}</h1>
        {issueDate ? (
          <p className="muted">{t("farmer.issuedOn", { date: formatDate(issueDate, lang) })}</p>
        ) : null}
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
        {(a) => {
          const [top, ...rest] = a.items;
          return (
            <>
              {top ? (
                <section aria-label={t("farmer.topLabel")}>
                  <AdviceCard advisory={top} village={village} dataMode={a.data_mode} hero />
                </section>
              ) : null}
              {rest.length ? (
                <section className="panel" aria-labelledby="also-today">
                  <h2 id="also-today" className="panel-pad">
                    {t("farmer.alsoToday", { count: rest.length })}
                  </h2>
                  <ul className="divided advice-list">
                    {rest.map((item) => (
                      <li key={item.id}>
                        <AdviceCard advisory={item} village={village} dataMode={a.data_mode} />
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          );
        }}
      </QueryBoundary>
      {pid && issueDate ? (
        <Link
          className="btn btn-farmer btn-wide"
          to={`/bulletin/${pid}?date=${issueDate}&lang=${lang}`}
        >
          <Printer size={20} aria-hidden="true" />
          {t("farmer.bulletinLink")}
        </Link>
      ) : null}
    </div>
  );
}
