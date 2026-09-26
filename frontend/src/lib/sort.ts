/** Row sorting for DataTable. */

export type SortDir = "asc" | "desc";
export type SortValue = number | string | null;

/**
 * Sorts rows by a value. Missing values (null, NaN) always go last in either direction,
 * and ties keep their original order.
 */
export function sortRows<R>(rows: readonly R[], value: (row: R) => SortValue, dir: SortDir): R[] {
  const sign = dir === "asc" ? 1 : -1;
  const missing = (v: SortValue) => v === null || (typeof v === "number" && Number.isNaN(v));
  return rows
    .map((row, i) => ({ row, i, v: value(row) }))
    .sort((a, b) => {
      if (missing(a.v) || missing(b.v)) {
        return missing(a.v) === missing(b.v) ? a.i - b.i : missing(a.v) ? 1 : -1;
      }
      const cmp =
        typeof a.v === "number" && typeof b.v === "number"
          ? a.v - b.v
          : String(a.v).localeCompare(String(b.v), undefined, { numeric: true });
      return cmp === 0 ? a.i - b.i : cmp * sign;
    })
    .map((x) => x.row);
}
