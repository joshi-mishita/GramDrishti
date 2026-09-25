import { ChartScatter } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useVerificationSummary } from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { EmptyState } from "../components/states";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";

/**
 * Forecast accuracy check (Guide 6.4). Until the verification job runs, the API sends
 * placeholder numbers; this screen shows the method and period, never those numbers.
 */
export default function VerificationPage() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const summary = useVerificationSummary();

  return (
    <div className="page">
      <PageHeader title={t("verification.title")} />
      <QueryBoundary query={summary} what={t("what.verification")}>
        {(s) => (
          <div className="panel panel-pad stack">
            <p>
              {t("verification.method", {
                method: s.method,
                start: formatDate(s.period.start, lang),
                end: formatDate(s.period.end, lang),
              })}
            </p>
            <ProvenanceNote provenance={s.provenance} />
            {s.notes.length ? (
              <div>
                <h2>{t("verification.notesTitle")}</h2>
                <ul className="notes" lang="en">
                  {s.notes.map((n) => (
                    <li key={n}>{n}</li>
                  ))}
                </ul>
              </div>
            ) : null}
            <EmptyState icon={ChartScatter} title={t("verification.notBuilt")} />
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}
