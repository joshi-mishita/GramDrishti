import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useImpact } from "../api/hooks";
import type { Decision, DecisionCounts, Impact, LocalizedText } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { SegmentedControl } from "../components/SegmentedControl";
import { DecisionBars, type BarSpec } from "../features/impact/DecisionBars";
import { formatDate, formatNumber } from "../lib/format";
import { pickText } from "../lib/text";
import { OUTCOMES, bestIndexes, formatCount, formatPercent, segments } from "../lib/verify";
import { useAppStore } from "../state/store";

const DECISIONS: readonly Decision[] = ["spray", "heat_alert", "irrigation_wait"];

/** Periods the replay job wrote (Impact.season). The whole test period comes first. */
const IMPACT_SEASONS = ["test_2024", "monsoon_2024", "post_monsoon_2024", "winter_2024"] as const;
type Season = (typeof IMPACT_SEASONS)[number];

/**
 * Decision replay (Guide 6.5): what would have happened had farmers followed the model
 * or the block forecast. Counts and percentages only, no money values.
 */
export default function ImpactPage() {
  const { t } = useTranslation();
  const [decision, setDecision] = useState<Decision>("spray");
  const [season, setSeason] = useState<Season>("test_2024");
  const impact = useImpact(decision, season);

  return (
    <div className="page">
      <PageHeader title={t("impact.title")} />
      <div className="toolbar impact-toolbar">
        <SegmentedControl<Decision>
          legend={t("impact.decision")}
          showLegend
          name="decision"
          variant="wrap"
          value={decision}
          options={DECISIONS.map((d) => ({ value: d, label: t(`impact.decisions.${d}`) }))}
          onChange={setDecision}
        />
        <SegmentedControl<Season>
          legend={t("impact.season")}
          showLegend
          name="season"
          variant="wrap"
          value={season}
          options={IMPACT_SEASONS.map((s) => ({ value: s, label: t(`impact.seasons.${s}`) }))}
          onChange={setSeason}
        />
      </div>
      <QueryBoundary query={impact} what={t("what.impact")} skeletonLines={5}>
        {(i) => <ImpactBody impact={i} />}
      </QueryBoundary>
    </div>
  );
}

function ImpactBody({ impact: i }: { impact: Impact }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const unit = i.unit ? t(`units.${i.unit}`, { defaultValue: i.unit }) : "";

  const bars: BarSpec[] = [
    { key: "model", label: t("impact.barModel"), counts: i.model },
    { key: "b0", label: t("impact.barBlock"), counts: i.block_baseline },
  ];
  const tableRows: BarSpec[] = i.block_corrected
    ? [...bars, { key: "b1", label: t("impact.barBlockCorrected"), counts: i.block_corrected }]
    : bars;

  return (
    <div className="stack">
      <section className="panel panel-pad stack" aria-labelledby="impact-bars">
        <h2 id="impact-bars">
          {t("impact.barsCaption", { decision: t(`impact.decisions.${i.decision}`) })}
        </h2>
        <p>
          {i.period
            ? t("impact.summary", {
                n: formatCount(i.n_decisions, lang),
                start: formatDate(i.period.start, lang),
                end: formatDate(i.period.end, lang),
                events: formatCount(i.events_observed, lang),
              })
            : t("impact.summaryNoPeriod", {
                n: formatCount(i.n_decisions, lang),
                events: formatCount(i.events_observed, lang),
              })}
        </p>
        {i.data_mode === "mock" ? (
          <p className="provenance">
            <TriangleAlert size={16} aria-hidden="true" />
            <span>{t("verification.mockNotice")}</span>
          </p>
        ) : null}
        <ProvenanceNote provenance={i.provenance} />
        <DecisionBars bars={bars} decision={i.decision} lang={lang} />
        {i.rule ? (
          <dl className="rules">
            <RuleRow label={t("impact.ruleModel")} text={i.rule.model} />
            <RuleRow label={t("impact.ruleBlock")} text={i.rule.block} />
          </dl>
        ) : null}
        {i.threshold !== null && i.threshold !== undefined ? (
          <p className="small">
            {t(`impact.meanings.${i.decision}`, {
              threshold: formatNumber(i.threshold, lang, 1),
              unit,
            })}
          </p>
        ) : null}
        <p className="small">{t("thresholds.placeholder")}</p>
      </section>

      <section className="panel panel-pad stack" aria-labelledby="impact-table">
        <h2 id="impact-table">{t("impact.tableCaption")}</h2>
        <p className="small muted">{t("impact.tableHelp")}</p>
        <OutcomeTable rows={tableRows} decision={i.decision} />
      </section>

      {i.notes?.length ? (
        <footer className="verify-footnote" aria-labelledby="impact-notes">
          <h2 id="impact-notes">{t("impact.notesTitle")}</h2>
          <ul className="notes" lang="en">
            {i.notes.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </footer>
      ) : null}
    </div>
  );
}

/**
 * Counts and shares per forecast. Bold: the most correct and the fewest of each mistake,
 * compared across the forecasts in the table.
 */
function OutcomeTable({ rows, decision }: { rows: readonly BarSpec[]; decision: Decision }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const bestByOutcome = Object.fromEntries(
    OUTCOMES.map((o) => [
      o,
      new Set(
        bestIndexes(
          rows.map((r) => r.counts[o]),
          o === "correct" ? "higher" : "lower",
        ),
      ),
    ]),
  ) as Record<keyof DecisionCounts, Set<number>>;

  return (
    <div className="table-wrap">
      <table className="data-table">
        <caption className="visually-hidden">{t("impact.tableCaption")}</caption>
        <thead>
          <tr>
            <th scope="col">{t("impact.colForecast")}</th>
            {OUTCOMES.map((o) => (
              <th key={o} scope="col" className="num">
                <span className={`key-swatch seg-${o}`} aria-hidden="true" />
                {t(`impact.outcomes.${decision}.${o}`)}
              </th>
            ))}
            <th scope="col" className="num">
              {t("impact.colTotal")}
            </th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r, idx) => {
            const segs = segments(r.counts);
            const total = OUTCOMES.reduce((a, o) => a + r.counts[o], 0);
            return (
              <tr key={r.key} data-row={r.key}>
                <th scope="row">{r.label}</th>
                {segs.map((s) => {
                  const best = bestByOutcome[s.outcome].has(idx);
                  const body = `${formatCount(s.count, lang)} (${formatPercent(s.share, lang)})`;
                  return (
                    <td key={s.outcome} className={best ? "num is-best" : "num"}>
                      {best ? <strong>{body}</strong> : body}
                    </td>
                  );
                })}
                <td className="num">{formatCount(total, lang)}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

function RuleRow({ label, text }: { label: string; text: LocalizedText }) {
  const lang = useAppStore((s) => s.lang);
  const picked = pickText(text, lang);
  return (
    <div>
      <dt>{label}</dt>
      <dd lang={picked.lang}>{picked.text}</dd>
    </div>
  );
}
