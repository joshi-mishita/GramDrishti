import { useId } from "react";
import { CircleCheck, FilterX, Printer } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useGeoPanchayats, usePriority } from "../api/hooks";
import { LEVELS, RISK_TYPES, type Level, type Priority, type RiskType } from "../api/types";
import { DataTable, type Column } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { RiskChip } from "../components/RiskChip";
import { EmptyState } from "../components/states";
import {
  HORIZONS,
  levelSortValue,
  mapLinkFor,
  rankAndFilter,
  readFilters,
  writeFilters,
  type PriorityFilters,
  type RankedItem,
} from "../features/priority/priorityData";
import { formatDate } from "../lib/format";
import { pickText } from "../lib/text";
import { useAppStore } from "../state/store";

/** Panchayats needing attention (Guide 6.2): ranked, filtered, printable. */
export default function PriorityPage() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const location = useLocation();
  const navigate = useNavigate();
  const filters = readFilters(location.search);
  const priority = usePriority(issueDate, filters.horizon);
  const date = issueDate ? formatDate(issueDate, lang) : "…";

  const setFilters = (next: Partial<PriorityFilters>) =>
    navigate(
      {
        pathname: location.pathname,
        search: writeFilters(location.search, { ...filters, ...next }),
      },
      { replace: true },
    );

  return (
    <div className="page page-wide">
      <PageHeader
        title={t("priority.title")}
        subtitle={t("priority.subtitle", { count: filters.horizon, date })}
      />
      <Filters filters={filters} blocks={blocksOf(priority.data)} onChange={setFilters} />
      <p className="print-only">{filterSummary(t, filters)}</p>
      <QueryBoundary
        query={priority}
        what={t("what.priority")}
        skeletonLines={8}
        isEmpty={(p) => p.items.length === 0}
        empty={
          <EmptyState icon={CircleCheck} title={t("priority.emptyTitle")}>
            <p>{t("priority.emptyBody", { count: filters.horizon, date })}</p>
          </EmptyState>
        }
      >
        {(p) => (
          <PriorityTable
            data={p}
            filters={filters}
            onClear={() => setFilters({ type: null, block: null })}
          />
        )}
      </QueryBoundary>
    </div>
  );
}

function blocksOf(p: Priority | undefined): string[] {
  return [...new Set(p?.items.map((i) => i.block_id) ?? [])].sort();
}

type T = ReturnType<typeof useTranslation>["t"];

/** One line naming the filters, shown on paper where the controls are hidden. */
function filterSummary(t: T, f: PriorityFilters): string {
  return t("priority.printFilters", {
    count: f.horizon,
    type: f.type ? t(`risks.${f.type}`) : t("priority.allTypes"),
    block: f.block ?? t("priority.allBlocks"),
  });
}

interface FiltersProps {
  filters: PriorityFilters;
  blocks: string[];
  onChange: (next: Partial<PriorityFilters>) => void;
}

function Filters({ filters, blocks, onChange }: FiltersProps) {
  const { t } = useTranslation();
  const id = useId();
  // Keep a block chosen from a link selectable even when this list has no item for it.
  const blockOptions =
    filters.block && !blocks.includes(filters.block) ? [...blocks, filters.block] : blocks;
  return (
    <div className="filters toolbar" role="group" aria-label={t("priority.filters")}>
      <div className="field-inline">
        <label htmlFor={`${id}-h`}>{t("priority.horizon")}</label>
        <select
          id={`${id}-h`}
          value={filters.horizon}
          onChange={(e) => onChange({ horizon: Number(e.target.value) })}
        >
          {HORIZONS.map((h) => (
            <option key={h} value={h}>
              {t("priority.horizonDays", { count: h })}
            </option>
          ))}
        </select>
      </div>
      <div className="field-inline">
        <label htmlFor={`${id}-t`}>{t("priority.type")}</label>
        <select
          id={`${id}-t`}
          value={filters.type ?? ""}
          onChange={(e) => onChange({ type: (e.target.value || null) as RiskType | null })}
        >
          <option value="">{t("priority.allTypes")}</option>
          {RISK_TYPES.map((r) => (
            <option key={r} value={r}>
              {t(`risks.${r}`)}
            </option>
          ))}
        </select>
      </div>
      <div className="field-inline">
        <label htmlFor={`${id}-b`}>{t("priority.block")}</label>
        <select
          id={`${id}-b`}
          value={filters.block ?? ""}
          onChange={(e) => onChange({ block: e.target.value || null })}
        >
          <option value="">{t("priority.allBlocks")}</option>
          {blockOptions.map((b) => (
            <option key={b} value={b}>
              {b}
            </option>
          ))}
        </select>
      </div>
      <button type="button" className="btn filters-print" onClick={() => window.print()}>
        <Printer size={16} aria-hidden="true" />
        {t("priority.print")}
      </button>
    </div>
  );
}

interface TableProps {
  data: Priority;
  filters: PriorityFilters;
  onClear: () => void;
}

function PriorityTable({ data, filters, onClear }: TableProps) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const navigate = useNavigate();
  const geo = useGeoPanchayats();
  const names = new Map(
    geo.data?.features.map((f) => [f.properties.panchayat_id, f.properties.name]) ?? [],
  );
  const rows = rankAndFilter(data.items, filters);
  const nameOf = (r: RankedItem) => names.get(r.panchayat_id) ?? r.panchayat_id;
  const cropName = (c: string) => t(`crops.${c}`, { defaultValue: c });

  const columns: Column<RankedItem>[] = [
    {
      key: "rank",
      header: t("priority.colRank"),
      numeric: true,
      sortValue: (r) => r.rank,
      render: (r) => r.rank,
    },
    {
      key: "name",
      header: t("table.panchayat"),
      rowHeader: true,
      sortValue: nameOf,
      render: (r) => (
        <>
          <Link to={mapLinkFor(r, data.issue_date)} className="link-btn">
            {nameOf(r)}
          </Link>
          <span className="cell-sub">{r.panchayat_id}</span>
        </>
      ),
    },
    {
      key: "block",
      header: t("table.block"),
      sortValue: (r) => r.block_id,
      render: (r) => r.block_id,
    },
    {
      key: "risk",
      header: t("priority.colRisk"),
      sortValue: (r) => t(`risks.${r.top_risk}`),
      render: (r) => t(`risks.${r.top_risk}`),
    },
    {
      key: "level",
      header: t("priority.colLevel"),
      sortValue: levelSortValue,
      render: (r) => <RiskChip level={r.level} />,
    },
    {
      key: "crops",
      header: t("priority.colCrops"),
      sortValue: (r) => r.crops_affected.map(cropName).join(", ") || null,
      render: (r) =>
        r.crops_affected.length ? (
          r.crops_affected.map(cropName).join(", ")
        ) : (
          <span className="muted">{t("priority.noCrops")}</span>
        ),
    },
    {
      key: "why",
      header: t("priority.colWhy"),
      render: (r) => {
        const h = pickText(r.headline, lang);
        return <span lang={h.lang}>{h.text}</span>;
      },
    },
  ];

  return (
    <div className="stack">
      <div className="priority-summary">
        <p>
          {filters.type || filters.block
            ? t("priority.summaryFiltered", { count: rows.length, total: data.items.length })
            : t("priority.summary", { count: data.items.length })}
        </p>
        <LevelCounts items={rows} />
      </div>
      {rows.length === 0 ? (
        <EmptyState
          icon={FilterX}
          title={t("priority.noMatchTitle")}
          action={
            <button type="button" className="btn" onClick={onClear}>
              {t("priority.clearFilters")}
            </button>
          }
        >
          <p>{t("priority.noMatchBody", { total: data.items.length })}</p>
        </EmptyState>
      ) : (
        <DataTable
          className="priority-table"
          caption={t("priority.caption", {
            count: filters.horizon,
            date: formatDate(data.issue_date, lang),
          })}
          columns={columns}
          rows={rows}
          rowKey={(r) => r.panchayat_id}
          initialSort={{ key: "rank", dir: "asc" }}
          onRowClick={(r) => navigate(mapLinkFor(r, data.issue_date))}
          sortLabel={(header, next) =>
            t(next === "asc" ? "table.sortAsc" : "table.sortDesc", { column: header })
          }
        />
      )}
      <p className="muted small">{t("priority.rowHint")}</p>
      <ProvenanceNote provenance={data.provenance} />
      {data.thresholds_status === "placeholder" ? (
        <p className="muted small">{t("thresholds.placeholder")}</p>
      ) : null}
    </div>
  );
}

function LevelCounts({ items }: { items: readonly RankedItem[] }) {
  const { t } = useTranslation();
  const counts = new Map<Level, number>();
  for (const i of items) counts.set(i.level, (counts.get(i.level) ?? 0) + 1);
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
