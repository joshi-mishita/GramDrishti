import { useTranslation } from "react-i18next";
import {
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Lang, ReliabilityPoint } from "../../api/types";
import { formatCount, formatPercent } from "../../lib/verify";
import { binEnds, reliabilityDots, type Dot } from "./verifyData";

interface Props {
  points: readonly ReliabilityPoint[];
  /** Event name as shown ("Rain 2.5 mm or more"). */
  eventLabel: string;
  lang: Lang;
}

const HEIGHT = 300;
const TICKS = [0, 0.2, 0.4, 0.6, 0.8, 1];

/**
 * Reliability diagram (Guide 6.4): forecast chance on x, how often it rained on y, the
 * diagonal as the perfect line. The chart is hidden from screen readers; the table next to
 * it has every number.
 */
export function ReliabilityPlot({ points, eventLabel, lang }: Props) {
  const { t } = useTranslation();
  const dots = reliabilityDots(points);
  const pct = (v: number) => formatPercent(v, lang, 0);
  const binRange = (centre: number) => {
    const [lo, hi] = binEnds(centre);
    return t("verification.binRange", { lo: pct(lo), hi: pct(hi) });
  };

  return (
    <div className="chart-with-table">
      <figure className="verify-chart" aria-hidden="true">
        <ResponsiveContainer
          width="100%"
          height={HEIGHT}
          initialDimension={{ width: 320, height: HEIGHT }}
        >
          <ScatterChart margin={{ top: 8, right: 16, bottom: 28, left: 8 }}>
            <CartesianGrid stroke="var(--line)" />
            <XAxis
              type="number"
              dataKey="x"
              domain={[0, 1]}
              ticks={TICKS}
              tickFormatter={pct}
              tick={{ fontSize: 12, fill: "var(--muted)" }}
              axisLine={{ stroke: "var(--line)" }}
              tickLine={false}
              label={{
                value: t("verification.reliabilityX"),
                position: "bottom",
                offset: 8,
                fontSize: 12,
                fill: "var(--muted)",
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              domain={[0, 1]}
              ticks={TICKS}
              tickFormatter={pct}
              width={44}
              tick={{ fontSize: 12, fill: "var(--muted)" }}
              axisLine={false}
              tickLine={false}
            />
            <ReferenceLine
              segment={[
                { x: 0, y: 0 },
                { x: 1, y: 1 },
              ]}
              stroke="var(--muted)"
              strokeDasharray="4 3"
              ifOverflow="visible"
            />
            <Scatter
              data={dots}
              isAnimationActive={false}
              shape={(props: unknown) => {
                const { cx, cy, payload } = props as { cx: number; cy: number; payload: Dot };
                return (
                  <circle
                    cx={cx}
                    cy={cy}
                    r={payload.r}
                    fill="var(--water)"
                    fillOpacity={0.55}
                    stroke="var(--surface)"
                    strokeWidth={1.5}
                  />
                );
              }}
            />
            <Tooltip
              cursor={false}
              isAnimationActive={false}
              content={({ active, payload }) => {
                const dot = payload?.[0]?.payload as Dot | undefined;
                if (!active || !dot) return null;
                const p = dot.point;
                return (
                  <div className="fan-tip">
                    <p className="fan-tip-date">
                      {t("verification.tipBin", { range: binRange(p.forecast_prob) })}
                    </p>
                    <p>{t("verification.tipMean", { value: formatPercent(dot.x, lang) })}</p>
                    <p>{t("verification.tipObserved", { value: formatPercent(dot.y, lang) })}</p>
                    <p>{t("verification.tipCount", { count: formatCount(dot.n, lang) })}</p>
                  </div>
                );
              }}
            />
          </ScatterChart>
        </ResponsiveContainer>
        <p className="axis-y-label">{t("verification.reliabilityY")}</p>
      </figure>
      <div className="table-wrap chart-table">
        <table className="data-table compact">
          <caption className="visually-hidden">
            {t("verification.reliabilityCaption", { event: eventLabel })}
          </caption>
          <thead>
            <tr>
              <th scope="col">{t("verification.colBin")}</th>
              <th scope="col" className="num">
                {t("verification.colMeanProb")}
              </th>
              <th scope="col" className="num">
                {t("verification.colObserved")}
              </th>
              <th scope="col" className="num">
                {t("verification.colForecasts")}
              </th>
            </tr>
          </thead>
          <tbody>
            {points.map((p) => (
              <tr key={p.forecast_prob}>
                <th scope="row">{binRange(p.forecast_prob)}</th>
                <td className="num">{formatPercent(p.mean_forecast_prob, lang)}</td>
                <td className="num">{formatPercent(p.observed_freq, lang)}</td>
                <td className="num">{formatCount(p.n, lang)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
