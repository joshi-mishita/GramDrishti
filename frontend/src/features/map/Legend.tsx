import { useId } from "react";
import { useTranslation } from "react-i18next";
import type { Lang } from "../../api/types";
import type { Ramp } from "../../lib/ramps";
import { legendTicks } from "./mapData";

interface Props {
  ramp: Ramp;
  title: string;
  unitLabel: string;
  lang: Lang;
  /** Explains the scale in a short line, e.g. "Panchayat minus block". */
  caption?: string;
}

const WIDTH = 240;
const BAR_H = 12;

/**
 * Colour key built from the same Ramp as the map style (Guide 8). Break values sit at equal
 * spacing and colours blend between them exactly as the map's linear interpolation does.
 * The colour bar is a data encoding, not decoration.
 */
export function Legend({ ramp, title, unitLabel, lang, caption }: Props) {
  const { t } = useTranslation();
  const gradientId = useId();
  const ticks = legendTicks(ramp, lang);
  const n = ramp.stops.length;
  const x = (i: number) => (n === 1 ? WIDTH / 2 : (i * WIDTH) / (n - 1));
  const last = ramp.stops[n - 1];
  const summary = t("legend.summary", {
    from: ticks[0],
    to: ticks[n - 1],
    unit: unitLabel,
  });

  return (
    <figure className="legend">
      <figcaption className="legend-title">
        {title} <span className="muted">({unitLabel})</span>
      </figcaption>
      {caption ? <p className="legend-caption muted">{caption}</p> : null}
      <svg
        className="legend-bar"
        width={WIDTH + 16}
        height={BAR_H + 22}
        viewBox={`-8 0 ${WIDTH + 16} ${BAR_H + 22}`}
        role="img"
        aria-label={summary}
      >
        <defs>
          <linearGradient id={gradientId}>
            {ramp.stops.map((s, i) => (
              <stop key={i} offset={n === 1 ? 0 : i / (n - 1)} stopColor={s.color} />
            ))}
          </linearGradient>
        </defs>
        <rect
          x={0}
          y={0}
          width={WIDTH}
          height={BAR_H}
          fill={`url(#${gradientId})`}
          className="legend-rect"
        />
        {ticks.map((label, i) => (
          <g key={i} transform={`translate(${x(i)},0)`}>
            <line y1={BAR_H} y2={BAR_H + 4} className="legend-tick" />
            <text y={BAR_H + 16} textAnchor="middle" className="legend-label">
              {i === n - 1 && ramp.kind === "sequential" && last ? `${label}+` : label}
            </text>
          </g>
        ))}
      </svg>
      <p className="legend-novalue">
        <span className="legend-swatch" aria-hidden="true" />
        {t("legend.noValue")}
      </p>
    </figure>
  );
}
