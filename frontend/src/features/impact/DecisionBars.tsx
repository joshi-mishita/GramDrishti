import { useTranslation } from "react-i18next";
import type { Decision, DecisionCounts, Lang } from "../../api/types";
import { formatCount, formatPercent, segments, type Segment } from "../../lib/verify";

export interface BarSpec {
  key: string;
  label: string;
  counts: DecisionCounts;
}

interface Props {
  bars: readonly BarSpec[];
  decision: Decision;
  lang: Lang;
}

/** A segment narrower than this share of the bar gets its number under the bar instead. */
export const INSIDE_MIN_SHARE = 0.12;

/**
 * Two stacked horizontal bars (Guide 6.5), one per forecast, split into correct, wasted
 * wait and washed off. Numbers are written on the segments; a segment too narrow to hold
 * its number has it written directly under the bar, next to a key of the same colour.
 * Widths are true shares of all decisions: small mistakes stay small.
 */
export function DecisionBars({ bars, decision, lang }: Props) {
  const { t } = useTranslation();
  const outcomeLabel = (s: Segment) => t(`impact.outcomes.${decision}.${s.outcome}`);
  const text = (s: Segment) =>
    t("impact.segmentLabel", {
      outcome: outcomeLabel(s),
      count: formatCount(s.count, lang),
      share: formatPercent(s.share, lang),
    });

  return (
    <div className="decision-bars">
      {bars.map((bar) => {
        const segs = segments(bar.counts);
        const outside = segs.filter((s) => s.share < INSIDE_MIN_SHARE && s.count > 0);
        return (
          <div key={bar.key} className="decision-bar" data-bar={bar.key}>
            <p className="decision-bar-label">{bar.label}</p>
            <div
              className="bar-track"
              role="img"
              aria-label={`${bar.label}: ${segs.map(text).join("; ")}`}
            >
              {segs.map((s) =>
                s.count > 0 ? (
                  <div
                    key={s.outcome}
                    className={`bar-seg seg-${s.outcome}`}
                    style={{ flexGrow: s.share }}
                    data-outcome={s.outcome}
                  >
                    {s.share >= INSIDE_MIN_SHARE ? (
                      <span className="bar-seg-text" aria-hidden="true">
                        {text(s)}
                      </span>
                    ) : null}
                  </div>
                ) : null,
              )}
            </div>
            {outside.length ? (
              <ul className="bar-outside" aria-hidden="true">
                {outside.map((s) => (
                  <li key={s.outcome}>
                    <span className={`key-swatch seg-${s.outcome}`} />
                    {text(s)}
                  </li>
                ))}
              </ul>
            ) : null}
          </div>
        );
      })}
    </div>
  );
}
