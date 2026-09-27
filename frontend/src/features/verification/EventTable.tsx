import { useTranslation } from "react-i18next";
import type { EventSummary } from "../../api/types";
import {
  METRIC_BETTER,
  METRIC_DIGITS,
  bestIndexes,
  formatCount,
  formatFixed,
  formatPercent,
  formatSkill,
  rowDigits,
} from "../../lib/verify";
import { useAppStore } from "../../state/store";

const EVENT_METRICS = ["pod", "far", "csi", "frequency_bias", "brier"] as const;
type EventMetric = (typeof EVENT_METRICS)[number];
type Baseline = "b0" | "b1" | "b2";

/**
 * Yes/no scores for the rain events, model against the block forecasts (the job scores
 * baselines as "block value at or above the threshold"). Best value per row in bold; the
 * heavy-rain rows where the model is far behind are shown like every other row.
 */
export function EventTable({ events }: { events: readonly EventSummary[] }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const baselines: Baseline[] = (["b0", "b1", "b2"] as const).filter((b) =>
    events.some((e) => (e.baselines ?? []).some((x) => x.baseline === b)),
  );
  const cols = 2 + baselines.length;

  return (
    <div className="table-wrap verify-table-wrap">
      <table className="data-table verify-table">
        <caption className="visually-hidden">{t("verification.eventsCaption")}</caption>
        <thead>
          <tr>
            <th scope="col">{t("verification.colMetric")}</th>
            <th scope="col" className="num">
              {t("verification.colModel")}
            </th>
            {baselines.map((b) => (
              <th key={b} scope="col" className="num">
                {t(`verification.baselineNames.${b}`)}
              </th>
            ))}
          </tr>
        </thead>
        {events.map((e) => (
          <tbody key={e.event}>
            <tr className="group-row">
              <th scope="rowgroup" colSpan={cols}>
                {t("verification.eventGroup", {
                  event: t(`verification.events.${e.event}`),
                  rate: formatPercent(e.base_rate, lang),
                  n: formatCount(e.n, lang),
                  bss: formatSkill(e.brier_skill_vs_climatology, lang),
                })}
              </th>
            </tr>
            {EVENT_METRICS.map((m) => {
              const values = [
                eventValue(e, m),
                ...baselines.map((b) => {
                  const s = (e.baselines ?? []).find((x) => x.baseline === b);
                  return s ? s[m] : null;
                }),
              ];
              const best = new Set(bestIndexes(values, METRIC_BETTER[m] ?? "lower"));
              const digits = rowDigits(values, METRIC_DIGITS[m] ?? 2);
              return (
                <tr key={m} data-metric={m}>
                  <th scope="row">{t(`verification.metrics.${m}`)}</th>
                  {values.map((v, i) => (
                    <td key={i} className={best.has(i) ? "num is-best" : "num"}>
                      {best.has(i) ? (
                        <strong>{formatFixed(v, lang, digits)}</strong>
                      ) : (
                        formatFixed(v, lang, digits)
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        ))}
      </table>
    </div>
  );
}

function eventValue(e: EventSummary, m: EventMetric): number | null {
  return e[m] ?? null;
}
