import { useState, type ReactNode } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown } from "lucide-react";
import { sortRows, type SortDir, type SortValue } from "../lib/sort";

export interface Column<R> {
  key: string;
  header: string;
  /** Value used for sorting; omit to make the column unsortable. */
  sortValue?: (row: R) => SortValue;
  render: (row: R) => ReactNode;
  numeric?: boolean;
  /** Renders the cell as a row header (<th scope="row">), for the name column. */
  rowHeader?: boolean;
}

interface Props<R> {
  caption: ReactNode;
  columns: Column<R>[];
  rows: readonly R[];
  rowKey: (row: R) => string;
  initialSort?: { key: string; dir: SortDir };
  /** Marks a row as the current selection (aria-current and a highlight). */
  isCurrent?: (row: R) => boolean;
  /** Text read out with each sort button, e.g. "Sort by". */
  sortLabel: (header: string, next: SortDir) => string;
}

/**
 * Sortable table with a sticky header and 36 px rows (Guide 8). Headers are buttons, so
 * sorting works from the keyboard, and aria-sort tells screen readers the order.
 */
export function DataTable<R>({
  caption,
  columns,
  rows,
  rowKey,
  initialSort,
  isCurrent,
  sortLabel,
}: Props<R>) {
  const [sort, setSort] = useState(initialSort ?? null);
  const col = sort ? columns.find((c) => c.key === sort.key) : undefined;
  const shown = col?.sortValue && sort ? sortRows(rows, col.sortValue, sort.dir) : rows;

  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption className="visually-hidden">{caption}</caption>
        <thead>
          <tr>
            {columns.map((c) => {
              const active = sort?.key === c.key;
              const next: SortDir = active && sort?.dir === "asc" ? "desc" : "asc";
              const Icon = active ? (sort?.dir === "asc" ? ArrowUp : ArrowDown) : ArrowUpDown;
              return (
                <th
                  key={c.key}
                  scope="col"
                  className={c.numeric ? "num" : undefined}
                  aria-sort={
                    active ? (sort?.dir === "asc" ? "ascending" : "descending") : undefined
                  }
                >
                  {c.sortValue ? (
                    <button
                      type="button"
                      className="th-sort"
                      onClick={() => setSort({ key: c.key, dir: next })}
                      aria-label={sortLabel(c.header, next)}
                    >
                      <span>{c.header}</span>
                      <Icon size={14} aria-hidden="true" className={active ? "" : "muted"} />
                    </button>
                  ) : (
                    c.header
                  )}
                </th>
              );
            })}
          </tr>
        </thead>
        <tbody>
          {shown.map((row) => {
            const current = isCurrent?.(row) ?? false;
            return (
              <tr
                key={rowKey(row)}
                className={current ? "is-current" : undefined}
                aria-current={current || undefined}
              >
                {columns.map((c) =>
                  c.rowHeader ? (
                    <th key={c.key} scope="row">
                      {c.render(row)}
                    </th>
                  ) : (
                    <td key={c.key} className={c.numeric ? "num" : undefined}>
                      {c.render(row)}
                    </td>
                  ),
                )}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
