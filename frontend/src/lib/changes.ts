import { RAIN_EVENTS, type EventChange, type RainEvent, type VarChange } from "../api/types";
import { addDays } from "./format";
import { probWord, type ProbWord } from "./words";

/** One line of the "forecast changed" list for a rain event. */
export interface EventChangeLine {
  date: string;
  event: RainEvent;
  before: ProbWord;
  after: ProbWord;
  previousProb: number | null;
  currentProb: number | null;
}

const EVENT_ORDER = new Map(RAIN_EVENTS.map((e, i) => [e, i]));

/**
 * Turns the API's event changes into lines a reader can follow, one day at a time.
 * Within a day the lightest event comes first. A heavier event is dropped when it tells
 * the same story in words (same "before" and "after" words as a line already kept), so
 * 1 mm, 2.5 mm and 10 mm all moving from "very unlikely" to "possible" is one line.
 */
export function summariseEventChanges(changes: readonly EventChange[]): EventChangeLine[] {
  const sorted = [...changes].sort(
    (a, b) =>
      a.valid_date.localeCompare(b.valid_date) ||
      (EVENT_ORDER.get(a.event) ?? 0) - (EVENT_ORDER.get(b.event) ?? 0),
  );
  const lines: EventChangeLine[] = [];
  for (const c of sorted) {
    const line: EventChangeLine = {
      date: c.valid_date,
      event: c.event,
      before: probWord(c.previous_prob),
      after: probWord(c.current_prob),
      previousProb: c.previous_prob,
      currentProb: c.current_prob,
    };
    const sameStory = lines.some(
      (l) => l.date === line.date && l.before === line.before && l.after === line.after,
    );
    if (!sameStory) lines.push(line);
  }
  return lines;
}

/** Variable changes the API marks as material, in date order. */
export function materialChanges(changes: readonly VarChange[]): VarChange[] {
  return changes.filter((c) => c.material).sort((a, b) => a.valid_date.localeCompare(b.valid_date));
}

/** True when the previous issue is the day before this one, so the UI can say "Yesterday". */
export function isPreviousDay(issueDate: string, previousIssueDate: string | null): boolean {
  return previousIssueDate !== null && addDays(issueDate, -1) === previousIssueDate;
}
