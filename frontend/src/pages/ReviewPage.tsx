import { useId, useMemo, useState } from "react";
import { FilterX, Inbox, MousePointerClick } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useLocation, useNavigate } from "react-router-dom";
import { isReal } from "../api/client";
import { useAdvisories, useAdvisory, useGeoPanchayats } from "../api/hooks";
import { STATUSES, type Advisory, type AdvisoryList } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { EmptyState } from "../components/states";
import { AdvisoryEditor } from "../features/review/AdvisoryEditor";
import { ReviewQueue } from "../features/review/ReviewQueue";
import {
  DEFAULT_STATUS,
  filterQueue,
  optionsOf,
  readQueue,
  sortQueue,
  writeQueue,
  type QueueFilters,
  type StatusFilter,
} from "../features/review/reviewState";
import { useReviewer } from "../features/review/useReviewer";
import { config } from "../lib/config";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";

/** Advisory review (Guide 6.3): queue with filters | editor with evidence and audit trail. */
export default function ReviewPage() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const location = useLocation();
  const navigate = useNavigate();
  const queue = readQueue(location.search);
  const advisories = useAdvisories(issueDate, queue.status === "all" ? undefined : queue.status);
  const [reviewer, setReviewer] = useReviewer();
  const writable = isReal("advisories");
  const date = issueDate ? formatDate(issueDate, lang) : "…";

  const setQueue = (next: Partial<QueueFilters & { adv: string | null }>) =>
    navigate(
      { pathname: location.pathname, search: writeQueue(location.search, next) },
      { replace: true },
    );

  return (
    <div className="page page-wide review-page">
      <PageHeader title={t("review.title")} subtitle={t("review.subtitle", { date })} />
      <ReviewerField value={reviewer} onChange={setReviewer} />
      {writable ? null : (
        // The published copy (GitHub Pages) is a snapshot: say so without developer set-up steps.
        <p className="provenance">
          {t(config.snapshot ? "review.readOnlySnapshot" : "review.readOnly")}
        </p>
      )}
      <QueryBoundary query={advisories} what={t("what.advisories")} skeletonLines={8}>
        {(list) => (
          <ReviewWorkspace
            list={list}
            queue={queue}
            setQueue={setQueue}
            reviewer={reviewer}
            writable={writable}
            date={date}
          />
        )}
      </QueryBoundary>
    </div>
  );
}

function ReviewerField({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const { t } = useTranslation();
  const id = useId();
  return (
    <div className="field-inline reviewer">
      <label htmlFor={id}>{t("review.reviewer")}</label>
      <input
        id={id}
        type="text"
        value={value}
        maxLength={60}
        autoComplete="name"
        aria-describedby={`${id}-hint`}
        onChange={(e) => onChange(e.target.value)}
      />
      <span id={`${id}-hint`} className="muted small">
        {t("review.reviewerHint")}
      </span>
    </div>
  );
}

interface WorkspaceProps {
  list: AdvisoryList;
  queue: QueueFilters & { adv: string | null };
  setQueue: (next: Partial<QueueFilters & { adv: string | null }>) => void;
  reviewer: string;
  writable: boolean;
  date: string;
}

function ReviewWorkspace({ list, queue, setQueue, reviewer, writable, date }: WorkspaceProps) {
  const { t } = useTranslation();
  const id = useId();
  const geo = useGeoPanchayats();
  const names = useMemo(
    () =>
      new Map(geo.data?.features.map((f) => [f.properties.panchayat_id, f.properties.name]) ?? []),
    [geo.data],
  );
  const sorted = useMemo(() => sortQueue(list.items), [list.items]);
  const items = useMemo(() => filterQueue(sorted, queue), [sorted, queue]);
  const openIndex = items.findIndex((a) => a.id === queue.adv);
  // -1 until the keyboard moves: the first ArrowDown then lands on the first item.
  const [active, setActive] = useState(openIndex);
  const shownActive = Math.min(active, items.length - 1);

  const statusLabel = (s: StatusFilter) =>
    s === "all" ? t("review.statusAll") : t(`statuses.${s}`);
  const heading =
    queue.status === "draft"
      ? t("review.waiting", { count: items.length })
      : t("review.listed", { status: statusLabel(queue.status), count: items.length });

  return (
    <div className="review-layout">
      <section className="review-queue" aria-labelledby={`${id}-queue`}>
        <h2 id={`${id}-queue`}>{heading}</h2>
        <div className="filters toolbar" role="group" aria-label={t("review.filters")}>
          <FilterSelect
            label={t("review.statusFilter")}
            value={queue.status}
            options={[...STATUSES, "all"].map((s) => ({
              value: s,
              label: statusLabel(s as StatusFilter),
            }))}
            onChange={(v) => setQueue({ status: (v || DEFAULT_STATUS) as StatusFilter })}
          />
          <FilterSelect
            label={t("priority.block")}
            value={queue.block ?? ""}
            options={[
              { value: "", label: t("priority.allBlocks") },
              ...optionsOf(sorted, "block_id").map((b) => ({ value: b, label: b })),
            ]}
            onChange={(v) => setQueue({ block: v || null })}
          />
          <FilterSelect
            label={t("review.crop")}
            value={queue.crop ?? ""}
            options={[
              { value: "", label: t("review.allCrops") },
              ...optionsOf(sorted, "crop").map((c) => ({
                value: c,
                label: t(`crops.${c}`, { defaultValue: c }),
              })),
            ]}
            onChange={(v) => setQueue({ crop: v || null })}
          />
        </div>
        {items.length ? (
          <ReviewQueue
            items={items}
            openId={queue.adv}
            active={shownActive}
            onActive={setActive}
            onOpen={(a) => setQueue({ adv: a.id })}
            names={names}
            label={heading}
          />
        ) : list.items.length ? (
          <EmptyState
            icon={FilterX}
            title={t("review.noMatchTitle")}
            action={
              <button
                type="button"
                className="btn"
                onClick={() => setQueue({ block: null, crop: null })}
              >
                {t("priority.clearFilters")}
              </button>
            }
          />
        ) : (
          <EmptyState
            icon={Inbox}
            title={queue.status === "draft" ? t("review.emptyTitle") : t("review.noneTitle")}
          >
            <p>
              {queue.status === "draft"
                ? t("review.emptyBody", { date })
                : t("review.noneBody", { status: statusLabel(queue.status), date })}
            </p>
          </EmptyState>
        )}
        <ProvenanceNote provenance={list.provenance} />
      </section>
      <OpenAdvisory
        id={queue.adv}
        fromList={
          items.find((a) => a.id === queue.adv) ?? list.items.find((a) => a.id === queue.adv)
        }
        names={names}
        reviewer={reviewer}
        writable={writable}
      />
    </div>
  );
}

interface OpenProps {
  id: string | null;
  fromList: Advisory | undefined;
  names: ReadonlyMap<string, string>;
  reviewer: string;
  writable: boolean;
}

/**
 * The editor for the advisory named in the URL. A review writes the returned advisory into
 * the detail cache, so that copy wins over the list until the list has refetched; an
 * advisory not in the loaded list (for example approved, while the list shows drafts) is
 * fetched on its own.
 */
function OpenAdvisory({ id, fromList, names, reviewer, writable }: OpenProps) {
  const { t } = useTranslation();
  const detail = useAdvisory(id, !fromList);
  const advisory = newest(detail.data, fromList);

  if (!id) {
    return (
      <section className="review-editor">
        <EmptyState icon={MousePointerClick} title={t("review.pickTitle")}>
          <p>{t("review.pickBody")}</p>
        </EmptyState>
      </section>
    );
  }
  if (!advisory) {
    return (
      <section className="review-editor">
        <QueryBoundary query={detail} what={t("what.advisory", { id })} skeletonLines={10}>
          {() => null}
        </QueryBoundary>
      </section>
    );
  }
  return (
    <section className="review-editor">
      <AdvisoryEditor
        // A new audit entry means the server copy changed: start editing from it.
        key={`${advisory.id}-${advisory.audit.length}`}
        advisory={advisory}
        panchayatName={names.get(advisory.panchayat_id) ?? advisory.panchayat_id}
        reviewer={reviewer}
        writable={writable}
      />
    </section>
  );
}

/** The copy with the longer audit trail is the newer one; ties go to the list. */
function newest(a: Advisory | undefined, b: Advisory | undefined): Advisory | undefined {
  if (!a) return b;
  if (!b) return a;
  return a.audit.length > b.audit.length ? a : b;
}

interface FilterSelectProps {
  label: string;
  value: string;
  options: { value: string; label: string }[];
  onChange: (value: string) => void;
}

function FilterSelect({ label, value, options, onChange }: FilterSelectProps) {
  const id = useId();
  return (
    <div className="field-stack">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(e) => onChange(e.target.value)}>
        {options.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
    </div>
  );
}
