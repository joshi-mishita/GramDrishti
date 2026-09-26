import { History } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useForecastChanges } from "../../api/hooks";
import type { ForecastChanges, Lang, VarChange } from "../../api/types";
import { ProvenanceNote } from "../../components/ProvenanceNote";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import {
  isPreviousDay,
  materialChanges,
  summariseEventChanges,
  type EventChangeLine,
} from "../../lib/changes";
import { VAR_DIGITS, formatDate, formatValue } from "../../lib/format";
import { UNITS } from "../../lib/ramps";
import { formatPercent } from "../../lib/words";
import { useAppStore } from "../../state/store";

/** "Forecast changed since yesterday" (/forecast/changes). */
export function ChangeList({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const changes = useForecastChanges(pid, issueDate);
  const prev = changes.data?.previous_issue_date ?? null;
  const title =
    prev && issueDate && !isPreviousDay(issueDate, prev)
      ? t("panel.changesTitleOn", { date: formatDate(prev, lang, "day") })
      : t("panel.changesTitle");

  return (
    <section aria-labelledby="changes-title">
      <h3 id="changes-title" className="section-title">
        {title}
      </h3>
      <QueryBoundary query={changes} what={t("what.changes")}>
        {(c) => <ChangeBody changes={c} lang={lang} />}
      </QueryBoundary>
    </section>
  );
}

function ChangeBody({ changes, lang }: { changes: ForecastChanges; lang: Lang }) {
  const { t } = useTranslation();
  const prev = changes.previous_issue_date;
  if (prev === null) return <EmptyState icon={History} title={t("panel.changesNone")} />;

  const events = summariseEventChanges(changes.event_changes);
  const values = materialChanges(changes.changes);
  if (events.length === 0 && values.length === 0) {
    return (
      <EmptyState
        icon={History}
        title={t("panel.changesNoMaterial", { date: formatDate(prev, lang, "day") })}
      />
    );
  }

  const before = isPreviousDay(changes.issue_date, prev)
    ? t("panel.yesterday")
    : t("panel.earlier", { date: formatDate(prev, lang, "day") });
  const dates = [...new Set([...events.map((e) => e.date), ...values.map((v) => v.valid_date)])];
  dates.sort();

  return (
    <div className="stack">
      <ul className="change-list">
        {dates.map((date) => (
          <li key={date}>
            <p className="change-date">{formatDate(date, lang, "day")}</p>
            {events
              .filter((e) => e.date === date)
              .map((e) => (
                <EventLine key={e.event} line={e} before={before} lang={lang} />
              ))}
            {values
              .filter((v) => v.valid_date === date)
              .map((v) => (
                <ValueLine key={v.var} change={v} lang={lang} />
              ))}
          </li>
        ))}
      </ul>
      <ProvenanceNote provenance={changes.provenance} />
    </div>
  );
}

/** "Yesterday: dry (4%). Now: rain possible (54%)." Heavier events name their threshold. */
function EventLine({ line, before, lang }: { line: EventChangeLine; before: string; lang: Lang }) {
  const { t } = useTranslation();
  const isAnyRain = line.event === "rain_ge_1mm";
  const word = (w: EventChangeLine["before"]) =>
    isAnyRain ? t(`rainState.${w}`) : t(`probWords.${w}`);
  return (
    <p>
      {isAnyRain ? null : <span className="change-event">{t(`events.${line.event}`)}. </span>}
      {before}: {word(line.before)} ({formatPercent(line.previousProb, lang)}). {t("panel.now")}:{" "}
      <strong>{word(line.after)}</strong> ({formatPercent(line.currentProb, lang)}).
    </p>
  );
}

function ValueLine({ change, lang }: { change: VarChange; lang: Lang }) {
  const { t } = useTranslation();
  const unit = t(`units.${UNITS[change.var]}`);
  const digits = VAR_DIGITS[change.var];
  return (
    <p>
      {t("panel.changeVar", {
        variable: t(`vars.${change.var}`),
        before: formatValue(change.previous_p50, unit, lang, digits),
        after: formatValue(change.current_p50, unit, lang, digits),
      })}
    </p>
  );
}
