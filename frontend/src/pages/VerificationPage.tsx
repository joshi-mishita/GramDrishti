import { useState } from "react";
import { TriangleAlert } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useCoverage, useRegions, useReliability, useVerificationSummary } from "../api/hooks";
import type { CheckSummary, RainEvent, VerificationSummary } from "../api/types";
import { RAIN_EVENTS } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { SegmentedControl } from "../components/SegmentedControl";
import { ComparisonTable } from "../features/verification/ComparisonTable";
import { CoverageChart } from "../features/verification/CoverageChart";
import { EventTable } from "../features/verification/EventTable";
import { RegionsTable } from "../features/verification/RegionsTable";
import { ReliabilityPlot } from "../features/verification/ReliabilityPlot";
import { formatDate, formatDateTime } from "../lib/format";
import { formatCount, readableNote, splitLossNote, splitNotes } from "../lib/verify";
import { useAppStore } from "../state/store";

type CheckId = CheckSummary["check"];

/**
 * Forecast accuracy check (Guide 6.4): is the Panchayat forecast better than the block
 * forecast? Every number comes from the verification job through the API; the screen only
 * lays it out. Losses are shown as plainly as wins.
 */
export default function VerificationPage() {
  const { t } = useTranslation();
  const summary = useVerificationSummary();

  return (
    <div className="page verify-page">
      <PageHeader title={t("verification.title")} />
      <QueryBoundary query={summary} what={t("what.verification")} skeletonLines={6}>
        {(s) => <VerificationBody s={s} />}
      </QueryBoundary>
    </div>
  );
}

function VerificationBody({ s }: { s: VerificationSummary }) {
  const { t } = useTranslation();
  const lang = useAppStore((st) => st.lang);
  const checks = s.checks ?? [];
  const [checkId, setCheckId] = useState<CheckId>(checks[0]?.check ?? "temporal_holdout");
  const check = checks.find((c) => c.check === checkId);
  const variables = check?.variables ?? s.variables;
  const { losses, other } = splitNotes(s.notes);

  const truth = checks[0]?.truth ?? "";
  const checkNames = checks.map((c) => t(`verification.checkNames.${c.check}`)).join(", ");
  const period = {
    start: formatDate(s.period.start, lang),
    end: formatDate(s.period.end, lang),
  };
  const gaps = Object.values(s.block_mean_error).filter((v): v is number => v !== null);
  const maxGap = gaps.length ? Math.max(...gaps.map(Math.abs)) : null;

  return (
    <>
      <section className="panel panel-pad stack" aria-label={t("verification.title")}>
        <p className="lead">
          {s.model_version
            ? t("verification.sentence", {
                model: s.model_version,
                ...period,
                truth,
                checks: checkNames,
              })
            : t("verification.sentenceNoModel", { ...period, truth, checks: checkNames })}
        </p>
        {s.data_mode === "mock" ? (
          <p className="provenance">
            <TriangleAlert size={16} aria-hidden="true" />
            <span>{t("verification.mockNotice")}</span>
          </p>
        ) : null}
        <ProvenanceNote provenance={s.provenance} />
        <p className="small muted">
          {s.test_first_opened_at
            ? t("verification.testOpened", {
                when: formatDateTime(s.test_first_opened_at, lang),
                reused: s.test_reused ? t("verification.yes") : t("verification.no"),
              }) + " "
            : null}
          {maxGap !== null ? t("verification.consistency", { gap: maxGap.toExponential(1) }) : null}
        </p>
      </section>

      <section className="panel panel-pad stack" aria-labelledby="verify-compare">
        <h2 id="verify-compare">{t("verification.compareTitle")}</h2>
        {checks.length > 1 ? (
          <SegmentedControl<CheckId>
            legend={t("verification.checkLegend")}
            showLegend
            name="check"
            variant="wrap"
            value={checkId}
            options={checks.map((c) => ({
              value: c.check,
              label: t(`verification.checkLabels.${c.check}`),
            }))}
            onChange={setCheckId}
          />
        ) : null}
        {check ? (
          <p className="small">
            <span lang="en">{check.description}</span>{" "}
            {t("verification.checkTruth", { truth: check.truth, n: formatCount(check.n, lang) })}
          </p>
        ) : null}
        <p className="small muted">{t("verification.howToRead")}</p>
        <ComparisonTable
          variables={variables}
          caption={t("verification.tableCaption", {
            check: t(`verification.checkLabels.${checkId}`),
          })}
        />
      </section>

      {s.events.length ? (
        <section className="panel panel-pad stack" aria-labelledby="verify-events">
          <h2 id="verify-events">{t("verification.eventsTitle")}</h2>
          <EventTable events={s.events} />
          <Footnotes
            notes={[...new Set(s.events.map((e) => e.yes_rule).filter((r): r is string => !!r))]}
          />
        </section>
      ) : null}

      <div className="verify-grid">
        <ReliabilitySection shared={s.notes} />
        <CoverageSection shared={s.notes} />
      </div>

      <RegionsSection shared={s.notes} />

      <section className="panel panel-pad stack" aria-labelledby="verify-losses">
        <h2 id="verify-losses">{t("verification.lossesTitle")}</h2>
        {losses.length ? (
          <ul className="loss-notes" lang="en">
            {losses.map((n) => {
              const { head, items } = splitLossNote(readableNote(n));
              return (
                <li key={n}>
                  {items.length ? (
                    <>
                      <p className="loss-head">{head}</p>
                      <ul className="loss-items">
                        {items.map((it) => (
                          // A real loss (interval below 0) is set apart from ties.
                          <li key={it} className={/: loss \(/.test(it) ? "is-loss" : undefined}>
                            {it}
                          </li>
                        ))}
                      </ul>
                    </>
                  ) : (
                    <p>{head}</p>
                  )}
                </li>
              );
            })}
          </ul>
        ) : (
          <p>{t("verification.lossesEmpty")}</p>
        )}
      </section>

      {other.length ? (
        <footer className="verify-footnote" aria-labelledby="verify-notes">
          <h2 id="verify-notes">{t("verification.notesTitle")}</h2>
          <ul className="notes" lang="en">
            {other.map((n) => (
              <li key={n}>{readableNote(n)}</li>
            ))}
          </ul>
        </footer>
      ) : null}
    </>
  );
}

function ReliabilitySection({ shared }: { shared: readonly string[] }) {
  const { t } = useTranslation();
  const lang = useAppStore((st) => st.lang);
  const [event, setEvent] = useState<RainEvent>("rain_ge_2_5mm");
  const reliability = useReliability(event);
  const eventLabel = t(`verification.events.${event}`);

  return (
    <section className="panel panel-pad stack" aria-labelledby="verify-reliability">
      <h2 id="verify-reliability">{t("verification.reliabilityTitle")}</h2>
      <SegmentedControl<RainEvent>
        legend={t("verification.reliabilityEvent")}
        showLegend
        name="reliability-event"
        variant="wrap"
        value={event}
        options={RAIN_EVENTS.map((e) => ({ value: e, label: t(`verification.eventsShort.${e}`) }))}
        onChange={setEvent}
      />
      <p className="small muted">{t("verification.reliabilityHelp")}</p>
      <QueryBoundary
        query={reliability}
        what={eventLabel}
        isEmpty={(r) => r.points.length === 0}
        empty={<p>{t("verification.noPoints")}</p>}
      >
        {(r) => (
          <>
            <ProvenanceNote provenance={r.provenance} />
            <ReliabilityPlot points={r.points} eventLabel={eventLabel} lang={lang} />
            <Footnotes notes={r.notes.filter((n) => !shared.includes(n))} />
          </>
        )}
      </QueryBoundary>
    </section>
  );
}

function CoverageSection({ shared }: { shared: readonly string[] }) {
  const { t } = useTranslation();
  const lang = useAppStore((st) => st.lang);
  const coverage = useCoverage();

  return (
    <section className="panel panel-pad stack" aria-labelledby="verify-coverage">
      <h2 id="verify-coverage">{t("verification.coverageTitle")}</h2>
      <p className="small muted">{t("verification.coverageHelp")}</p>
      <QueryBoundary query={coverage} what={t("verification.coverageCaption")}>
        {(c) => (
          <>
            <ProvenanceNote provenance={c.provenance} />
            <CoverageChart items={c.items} lang={lang} />
            <Footnotes notes={c.notes.filter((n) => !shared.includes(n))} />
          </>
        )}
      </QueryBoundary>
    </section>
  );
}

function RegionsSection({ shared }: { shared: readonly string[] }) {
  const { t } = useTranslation();
  const lang = useAppStore((st) => st.lang);
  const regions = useRegions();

  return (
    <section className="panel panel-pad stack" aria-labelledby="verify-regions">
      <h2 id="verify-regions">{t("verification.regionsTitle")}</h2>
      <p className="small muted">{t("verification.regionsHelp")}</p>
      <QueryBoundary query={regions} what={t("verification.regionsTitle")}>
        {(r) => (
          <>
            <ProvenanceNote provenance={r.provenance} />
            <RegionsTable items={r.items} lang={lang} />
            <Footnotes notes={r.notes.filter((n) => !shared.includes(n))} />
          </>
        )}
      </QueryBoundary>
    </section>
  );
}

/** Section notes from the API, in English as the job wrote them. */
function Footnotes({ notes }: { notes: readonly string[] }) {
  const { t } = useTranslation();
  if (!notes.length) return null;
  return (
    <div className="section-notes">
      <h3 className="visually-hidden">{t("verification.sectionNotes")}</h3>
      <ul className="notes small" lang="en">
        {notes.map((n) => (
          <li key={n}>{readableNote(n)}</li>
        ))}
      </ul>
    </div>
  );
}
