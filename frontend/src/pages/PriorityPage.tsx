import { CircleCheck, ListOrdered } from "lucide-react";
import { useTranslation } from "react-i18next";
import { usePriority } from "../api/hooks";
import { LEVELS, type Level, type Priority } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { RiskChip } from "../components/RiskChip";
import { EmptyState } from "../components/states";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";

const HORIZON_DAYS = 2;

/** Panchayats needing attention (Guide 6.2). The ranked table comes with the priority screen. */
export default function PriorityPage() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const priority = usePriority(issueDate, HORIZON_DAYS);
  const date = issueDate ? formatDate(issueDate, lang) : "…";

  return (
    <div className="page">
      <PageHeader
        title={t("priority.title")}
        subtitle={t("priority.subtitle", { count: HORIZON_DAYS, date })}
      />
      <QueryBoundary
        query={priority}
        what={t("what.priority")}
        isEmpty={(p) => p.items.length === 0}
        empty={
          <EmptyState icon={CircleCheck} title={t("priority.emptyTitle")}>
            <p>{t("priority.emptyBody", { date })}</p>
          </EmptyState>
        }
      >
        {(p) => (
          <div className="panel panel-pad stack">
            <p>{t("priority.summary", { count: p.items.length })}</p>
            <LevelCounts data={p} />
            <ProvenanceNote provenance={p.provenance} />
            {p.thresholds_status === "placeholder" ? (
              <p className="muted small">{t("thresholds.placeholder")}</p>
            ) : null}
            <EmptyState icon={ListOrdered} title={t("priority.notBuilt")} />
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}

function LevelCounts({ data }: { data: Priority }) {
  const { t } = useTranslation();
  const counts = new Map<Level, number>();
  for (const i of data.items) counts.set(i.level, (counts.get(i.level) ?? 0) + 1);
  const levels = [...LEVELS].reverse().filter((l) => counts.get(l));
  return (
    <dl className="level-counts" aria-label={t("priority.byLevel")}>
      {levels.map((l) => (
        <div key={l}>
          <dt>
            <RiskChip level={l} />
          </dt>
          <dd className="num">{counts.get(l)}</dd>
        </div>
      ))}
    </dl>
  );
}
