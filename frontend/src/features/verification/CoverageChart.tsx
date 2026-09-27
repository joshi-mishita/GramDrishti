import { useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  XAxis,
  YAxis,
} from "recharts";
import type { CoverageItem, Lang } from "../../api/types";
import { SegmentedControl } from "../../components/SegmentedControl";
import { VAR_DIGITS } from "../../lib/format";
import { formatCount, formatFixed, formatPercent, parseStratum } from "../../lib/verify";
import { chartItems, tableItems, type CoverageGroup as Group } from "./verifyData";
import { TableScroll } from "../../components/TableScroll";

const GROUPS: readonly Group[] = ["all", "lead_day", "season"];

interface Row {
  key: string;
  label: string;
  item: CoverageItem;
}

const BAR_H = 34;

/**
 * Interval coverage (Guide 6.4): the share of outcomes inside the p10..p90 range, per
 * variable, against the 80 % aim. The mean width sits beside it in the table, because a
 * wide range covers easily.
 */
export function CoverageChart({ items, lang }: { items: readonly CoverageItem[]; lang: Lang }) {
  const { t } = useTranslation();
  const [group, setGroup] = useState<Group>("all");
  const nominal = items[0]?.nominal ?? 0.8;

  const label = (it: CoverageItem): string => {
    const s = parseStratum(it.stratum);
    if (s.kind === "wet_days") return t("verification.wetDaysVar");
    return t(`varsShort.${it.var}`);
  };
  const stratumLabel = (it: CoverageItem): string => {
    const s = parseStratum(it.stratum);
    if (s.kind === "season") {
      return t("verification.strata.season", {
        value: t(`verification.seasons.${s.value}`, { defaultValue: s.value }),
      });
    }
    if (s.kind === "other") return s.value;
    return t(`verification.strata.${s.kind}`, { value: s.value });
  };

  const bars: Row[] = chartItems(items).map((it) => ({
    key: `${it.var}-${it.stratum ?? "all"}`,
    label: label(it),
    item: it,
  }));
  const data = bars.map((b) => ({ label: b.label, empirical: b.item.empirical }));
  const rows = tableItems(items, group);

  return (
    <div className="stack">
      <div className="chart-with-table">
        <figure className="verify-chart" aria-hidden="true">
          <ResponsiveContainer
            width="100%"
            height={bars.length * BAR_H + 48}
            initialDimension={{ width: 320, height: bars.length * BAR_H + 48 }}
          >
            <BarChart
              accessibilityLayer={false}
              data={data}
              layout="vertical"
              margin={{ top: 20, right: 16, bottom: 8, left: 0 }}
              barCategoryGap={8}
            >
              <CartesianGrid horizontal={false} stroke="var(--line)" />
              <XAxis
                type="number"
                domain={[0, 1]}
                ticks={[0, 0.2, 0.4, 0.6, 0.8, 1]}
                tickFormatter={(v: number) => formatPercent(v, lang, 0)}
                tick={{ fontSize: 12, fill: "var(--muted)" }}
                axisLine={{ stroke: "var(--line)" }}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="label"
                width={112}
                tick={{ fontSize: 12, fill: "var(--ink)" }}
                axisLine={false}
                tickLine={false}
              />
              <Bar
                dataKey="empirical"
                fill="var(--water)"
                radius={[0, 2, 2, 0]}
                isAnimationActive={false}
              >
                <LabelList
                  dataKey="empirical"
                  position="insideRight"
                  formatter={(v: unknown) => (typeof v === "number" ? formatPercent(v, lang) : "–")}
                  style={{ fontSize: 12, fontWeight: 500, fill: "var(--brand-ink)" }}
                />
              </Bar>
              <ReferenceLine
                x={nominal}
                stroke="var(--ink)"
                strokeWidth={1.5}
                strokeDasharray="4 3"
                label={{
                  value: t("verification.coverageAim"),
                  position: "top",
                  fontSize: 12,
                  fill: "var(--ink)",
                }}
              />
            </BarChart>
          </ResponsiveContainer>
          <p className="axis-x-label">{t("verification.coverageAxis")}</p>
        </figure>
        <div className="stack chart-table">
          <SegmentedControl<Group>
            legend={t("verification.coverageGroup")}
            name="coverage-group"
            variant="wrap"
            value={group}
            options={GROUPS.map((g) => ({
              value: g,
              label: t(`verification.coverageGroups.${g}`),
            }))}
            onChange={setGroup}
          />
          <TableScroll label={t("verification.coverageCaption")}>
            <table className="data-table compact">
              <caption className="visually-hidden">{t("verification.coverageCaption")}</caption>
              <thead>
                <tr>
                  <th scope="col">{t("verification.colVariable")}</th>
                  <th scope="col">{t("verification.colStratum")}</th>
                  <th scope="col" className="num">
                    {t("verification.colNominal")}
                  </th>
                  <th scope="col" className="num">
                    {t("verification.colEmpirical")}
                  </th>
                  <th scope="col" className="num">
                    {t("verification.colWidth")}
                  </th>
                  <th scope="col" className="num">
                    {t("verification.colForecasts")}
                  </th>
                </tr>
              </thead>
              <tbody>
                {rows.map((it) => (
                  <tr key={`${it.var}-${it.stratum ?? "all"}`}>
                    <th scope="row">{t(`varsShort.${it.var}`)}</th>
                    <td>{stratumLabel(it)}</td>
                    <td className="num">{formatPercent(it.nominal, lang, 0)}</td>
                    <td className="num">{formatPercent(it.empirical, lang)}</td>
                    <td className="num">
                      {formatFixed(it.mean_width, lang, Math.max(1, VAR_DIGITS[it.var]))}{" "}
                      {t(`units.${it.unit}`, { defaultValue: it.unit })}
                    </td>
                    <td className="num">{formatCount(it.n, lang)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </TableScroll>
        </div>
      </div>
    </div>
  );
}
