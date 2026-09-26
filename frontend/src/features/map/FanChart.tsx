import { useTranslation } from "react-i18next";
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Lang, Var } from "../../api/types";
import { fanDomain, type FanRow } from "../../lib/fan";
import { VAR_DIGITS, formatDate, formatNumber } from "../../lib/format";

interface Props {
  rows: readonly FanRow[];
  variable: Var;
  /** Unit label as shown ("mm", "°C"). */
  unit: string;
  lang: Lang;
  showObserved: boolean;
  /** Date of the day chosen on the map; marked with a thin line. */
  selectedDate?: string;
}

const HEIGHT = 200;

/**
 * Fan chart (Guide 8.3): p10 to p90 band as two stacked areas, p50 line, dashed block
 * line and, when asked, observed points. Nulls are gaps, never zeros. The SVG is hidden
 * from screen readers; the same numbers are in a table for them.
 */
export function FanChart({ rows, variable, unit, lang, showObserved, selectedDate }: Props) {
  const { t } = useTranslation();
  const digits = VAR_DIGITS[variable];
  const domain = fanDomain(
    showObserved ? rows : rows.map((r) => ({ ...r, observed: null })),
    variable,
  );
  const fmt = (v: number | null) => formatNumber(v, lang, digits);
  const varName = t(`vars.${variable}`);

  return (
    <figure className="fan">
      <p className="fan-unit" aria-hidden="true">
        {t("panel.axisUnit", { unit })}
      </p>
      <div className="fan-plot" aria-hidden="true">
        <ResponsiveContainer
          width="100%"
          height={HEIGHT}
          initialDimension={{ width: 288, height: HEIGHT }}
        >
          <ComposedChart data={rows as FanRow[]} margin={{ top: 8, right: 8, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--line)" />
            <XAxis
              dataKey="date"
              tickFormatter={(d: string) => formatDate(d, lang, "short")}
              tick={{ fontSize: 12, fill: "var(--muted)" }}
              tickLine={false}
              axisLine={{ stroke: "var(--line)" }}
              interval={0}
              padding={{ left: 14, right: 18 }}
            />
            <YAxis
              domain={domain ?? [0, 1]}
              tickCount={5}
              width={40}
              tick={{ fontSize: 12, fill: "var(--muted)" }}
              tickFormatter={(v: number) => formatNumber(v, lang, digits)}
              tickLine={false}
              axisLine={false}
              // fanDomain already covers every plotted value. Without this Recharts widens
              // the axis to the stack's 0 baseline and a 30 C band becomes a flat line.
              allowDataOverflow
            />
            {selectedDate ? (
              <ReferenceLine x={selectedDate} stroke="var(--muted)" strokeDasharray="1 3" />
            ) : null}
            <Area
              dataKey="base"
              stackId="band"
              stroke="none"
              fill="transparent"
              isAnimationActive={false}
              activeDot={false}
            />
            <Area
              dataKey="band"
              stackId="band"
              stroke="none"
              fill="var(--water)"
              fillOpacity={0.22}
              isAnimationActive={false}
              activeDot={false}
            />
            <Line
              dataKey="block"
              stroke="var(--ink)"
              strokeWidth={1.5}
              strokeDasharray="4 3"
              dot={false}
              activeDot={false}
              isAnimationActive={false}
            />
            <Line
              dataKey="p50"
              stroke="var(--water)"
              strokeWidth={2}
              dot={{ r: 2.5, fill: "var(--water)", stroke: "var(--water)" }}
              activeDot={{ r: 4 }}
              isAnimationActive={false}
            />
            {showObserved ? (
              <Line
                dataKey="observed"
                stroke="none"
                dot={{ r: 4, fill: "var(--heat)", stroke: "var(--surface)", strokeWidth: 1.5 }}
                activeDot={{ r: 5, fill: "var(--heat)" }}
                isAnimationActive={false}
                legendType="circle"
              />
            ) : null}
            <Tooltip
              cursor={{ stroke: "var(--muted)", strokeWidth: 1 }}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const row = payload?.[0]?.payload as FanRow | undefined;
                if (!active || !row) return null;
                return (
                  <div className="fan-tip">
                    <p className="fan-tip-date">{formatDate(row.date, lang, "day")}</p>
                    {row.p10 !== null && row.p90 !== null ? (
                      <p>
                        {t("panel.tipRange", { lo: fmt(row.p10), hi: fmt(row.p90) })} {unit}
                      </p>
                    ) : null}
                    <p>
                      {t("panel.tipMiddle", { value: fmt(row.p50) })} {unit}
                    </p>
                    <p>
                      {t("panel.tipBlock", { value: fmt(row.block) })} {unit}
                    </p>
                    {showObserved && row.observed !== null ? (
                      <p>
                        {t("panel.tipObserved", { value: fmt(row.observed) })} {unit}
                      </p>
                    ) : null}
                  </div>
                );
              }}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <ul className="fan-legend" aria-hidden="true">
        <li>
          <span className="key key-band" />
          {t("panel.legendBand")}
        </li>
        <li>
          <span className="key key-middle" />
          {t("panel.legendMiddle")}
        </li>
        <li>
          <span className="key key-block" />
          {t("panel.legendBlock")}
        </li>
        {showObserved ? (
          <li>
            <span className="key key-observed" />
            {t("panel.legendObserved")}
          </li>
        ) : null}
      </ul>
      {/* The wrapper hides the table: overflow does not clip an element shown as a table. */}
      <div className="visually-hidden">
        <table>
          <caption>{t("panel.chartTableCaption", { variable: varName, unit })}</caption>
          <thead>
            <tr>
              <th scope="col">{t("panel.colDay")}</th>
              <th scope="col">{t("panel.colLow")}</th>
              <th scope="col">{t("panel.colMiddle")}</th>
              <th scope="col">{t("panel.colHigh")}</th>
              <th scope="col">{t("panel.colBlock")}</th>
              {showObserved ? <th scope="col">{t("panel.colObserved")}</th> : null}
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.date}>
                <th scope="row">{formatDate(r.date, lang, "day")}</th>
                <td>{fmt(r.p10)}</td>
                <td>{fmt(r.p50)}</td>
                <td>{fmt(r.p90)}</td>
                <td>{fmt(r.block)}</td>
                {showObserved ? <td>{fmt(r.observed)}</td> : null}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </figure>
  );
}
