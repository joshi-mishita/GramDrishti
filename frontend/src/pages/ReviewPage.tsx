import { ClipboardCheck, Inbox } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useAdvisories } from "../api/hooks";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { EmptyState } from "../components/states";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";

/** Advisory review queue (Guide 6.3). The editor and audit trail come with the review screen. */
export default function ReviewPage() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const advisories = useAdvisories(issueDate, "draft");
  const date = issueDate ? formatDate(issueDate, lang) : "…";

  return (
    <div className="page">
      <PageHeader title={t("review.title")} subtitle={date} />
      <QueryBoundary
        query={advisories}
        what={t("what.advisories")}
        isEmpty={(a) => a.total === 0}
        empty={
          <EmptyState icon={Inbox} title={t("review.emptyTitle")}>
            <p>{t("review.emptyBody", { date })}</p>
          </EmptyState>
        }
      >
        {(a) => (
          <div className="panel panel-pad stack">
            <h2>{t("review.waiting", { count: a.total })}</h2>
            <ProvenanceNote provenance={a.provenance} />
            <EmptyState icon={ClipboardCheck} title={t("review.notBuilt")} />
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}
