import { useTranslation } from "react-i18next";
import type { ForecastMap, PanchayatCollection } from "../../api/types";
import { DataTable, type Column } from "../../components/DataTable";
import { VAR_DIGITS, formatNumber, formatSigned } from "../../lib/format";
import { useAppStore } from "../../state/store";
import { tableRows, type TableRow as Row } from "./mapData";

interface Props {
  forecast: ForecastMap;
  geo: PanchayatCollection;
  caption: string;
}

/**
 * "Show as table": every Panchayat with the values the map paints (Guide 6.1). The keyboard
 * and screen-reader route to the same information; the name button selects a Panchayat.
 */
export function PanchayatTable({ forecast, geo, caption }: Props) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const selectedPid = useAppStore((s) => s.selectedPid);
  const setSelectedPid = useAppStore((s) => s.setSelectedPid);
  const digits = VAR_DIGITS[forecast.var];
  const unit = t(`units.${forecast.unit}`, { defaultValue: forecast.unit });
  const num = (v: number | null) => formatNumber(v, lang, digits);

  const columns: Column<Row>[] = [
    {
      key: "name",
      header: t("table.panchayat"),
      rowHeader: true,
      sortValue: (r) => r.name,
      render: (r) => (
        <button type="button" className="link-btn" onClick={() => setSelectedPid(r.panchayat_id)}>
          {r.name}
        </button>
      ),
    },
    {
      key: "block",
      header: t("table.block"),
      sortValue: (r) => r.block_id,
      render: (r) => r.block_id,
    },
    {
      key: "p50",
      header: t("table.panchayatValue", { unit }),
      numeric: true,
      sortValue: (r) => r.p50,
      render: (r) => num(r.p50),
    },
    {
      key: "range",
      header: t("table.range", { unit }),
      numeric: true,
      sortValue: (r) => r.p90,
      render: (r) => (r.p10 === null || r.p90 === null ? "–" : `${num(r.p10)} – ${num(r.p90)}`),
    },
    {
      key: "block_value",
      header: t("table.blockValue", { unit }),
      numeric: true,
      sortValue: (r) => r.block_value,
      render: (r) => num(r.block_value),
    },
    {
      key: "delta",
      header: t("table.delta", { unit }),
      numeric: true,
      sortValue: (r) => r.delta,
      render: (r) => formatSigned(r.delta, lang, digits),
    },
  ];

  return (
    <DataTable
      caption={caption}
      columns={columns}
      rows={tableRows(forecast, geo)}
      rowKey={(r) => r.panchayat_id}
      isCurrent={(r) => r.panchayat_id === selectedPid}
      sortLabel={(header, next) =>
        t(next === "asc" ? "table.sortAsc" : "table.sortDesc", { column: header })
      }
    />
  );
}
