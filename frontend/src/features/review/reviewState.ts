/**
 * Pure state logic of the review screen (Guide 6.3): editable texts, what changed, the
 * review request sent to the API, keyboard movement through the queue and the filters.
 * Components stay thin; everything here is unit-tested.
 */
import type {
  Advisory,
  EditedFields,
  Lang,
  LocalizedText,
  ReviewAction,
  ReviewRequest,
  Status,
} from "../../api/types";
import { LANGS, STATUSES } from "../../api/types";
import { LEVEL_INDEX } from "../../lib/ramps";

export const FIELDS = ["action", "reason", "fallback"] as const;
export type Field = (typeof FIELDS)[number];

/** Editable text of one advisory: every field in every language, "" where the API has null. */
export type Texts = Record<Field, Record<Lang, string>>;

export interface Cell {
  field: Field;
  lang: Lang;
}

function fromLocalized(t: LocalizedText): Record<Lang, string> {
  return { en: t.en, hi: t.hi ?? "", pa: t.pa ?? "" };
}

/** The texts of an advisory as the editor starts them. */
export function textsOf(a: Advisory): Texts {
  return {
    action: fromLocalized(a.action),
    reason: fromLocalized(a.reason),
    fallback: fromLocalized(a.fallback),
  };
}

/** Returns a copy with one cell replaced. */
export function setText(texts: Texts, field: Field, lang: Lang, value: string): Texts {
  return { ...texts, [field]: { ...texts[field], [lang]: value } };
}

const same = (a: string, b: string) => a.trim() === b.trim();

/** Cells whose text differs from the draft, ignoring leading and trailing spaces. */
export function changedCells(original: Texts, current: Texts): Cell[] {
  return FIELDS.flatMap((field) =>
    LANGS.filter((lang) => !same(original[field][lang], current[field][lang])).map((lang) => ({
      field,
      lang,
    })),
  );
}

export function isDirty(original: Texts, current: Texts): boolean {
  return changedCells(original, current).length > 0;
}

/**
 * Translations that saving would clear: the English of that field changed but this
 * language was not edited. The API drops a language left out of an edited text so an old
 * translation never survives new English (contract v0.2.0, D063); the editor says so first.
 */
export function droppedTranslations(original: Texts, current: Texts): Cell[] {
  return FIELDS.flatMap((field) => {
    if (same(original[field].en, current[field].en)) return [];
    return LANGS.filter(
      (lang) =>
        lang !== "en" &&
        original[field][lang].trim() !== "" &&
        same(original[field][lang], current[field][lang]),
    ).map((lang) => ({ field, lang }));
  });
}

/** Fields whose English text is empty; English is required (the fallback language). */
export function missingEnglish(current: Texts): Field[] {
  return FIELDS.filter((f) => current[f].en.trim() === "");
}

/**
 * The `edited` part of an edit request: only fields with a change. Within a changed field,
 * English is always sent. Another language is sent when it has text, unless the English
 * changed and that language was not edited (then it is left out and becomes null).
 */
export function buildEdited(original: Texts, current: Texts): EditedFields | null {
  const out: EditedFields = {};
  for (const field of FIELDS) {
    const changed = LANGS.some((l) => !same(original[field][l], current[field][l]));
    if (!changed) continue;
    const enChanged = !same(original[field].en, current[field].en);
    const text: LocalizedText = { en: current[field].en.trim() };
    for (const lang of ["hi", "pa"] as const) {
      const value = current[field][lang].trim();
      const edited = !same(original[field][lang], current[field][lang]);
      text[lang] = value && (edited || !enChanged) ? value : null;
    }
    out[field] = text;
  }
  return Object.keys(out).length ? out : null;
}

export type ReviewKind = "approve" | "edit" | "reject";

interface RequestInput {
  reviewer: string;
  note?: string;
  original: Texts;
  current: Texts;
}

/** The body of POST /advisories/{id}/review for one of the three buttons. */
export function reviewRequest(kind: ReviewKind, input: RequestInput): ReviewRequest {
  const base = { action: kind, reviewer: input.reviewer.trim(), note: input.note?.trim() ?? "" };
  if (kind !== "edit") return base;
  const edited = buildEdited(input.original, input.current);
  if (!edited) throw new Error("Nothing was edited");
  return { ...base, edited };
}

/**
 * Why a button cannot be used right now, or null when it can. Keeps the three buttons and
 * Ctrl+Enter on one rule set.
 */
export function blockedReason(
  kind: ReviewKind,
  s: {
    dirty: boolean;
    missing: Field[];
    reviewer: string;
    note: string;
    writable: boolean;
    status: Status;
  },
):
  | "readOnly"
  | "noReviewer"
  | "alreadyApproved"
  | "alreadyRejected"
  | "hasEdits"
  | "noEdits"
  | "missingEnglish"
  | "noReason"
  | null {
  if (!s.writable) return "readOnly";
  if (!s.reviewer.trim()) return "noReviewer";
  // Approving an approved text again would only add a duplicate row to the history.
  if (kind === "approve" && !s.dirty && (s.status === "approved" || s.status === "edited")) {
    return "alreadyApproved";
  }
  if (kind === "reject" && s.status === "rejected") return "alreadyRejected";
  if (kind === "approve" && s.dirty) return "hasEdits";
  if (kind === "edit" && !s.dirty) return "noEdits";
  if (kind === "edit" && s.missing.length) return "missingEnglish";
  if (kind === "reject" && !s.note.trim()) return "noReason";
  return null;
}

/** Ctrl+Enter approves; with unsaved edits it saves them and approves (both approve). */
export function shortcutKind(dirty: boolean): ReviewKind {
  return dirty ? "edit" : "approve";
}

/** Toast key for a finished review: the same word as the button (Guide 2.7). */
export const TOAST_KEY: Record<ReviewAction, string> = {
  approve: "review.toastApproved",
  edit: "review.toastEdited",
  reject: "review.toastRejected",
};

/** Status filter values: one per status, plus every status. */
export type StatusFilter = Status | "all";
export const DEFAULT_STATUS: StatusFilter = "draft";

export interface QueueFilters {
  status: StatusFilter;
  block: string | null;
  crop: string | null;
}

export const QUEUE_KEYS = { status: "status", block: "block", crop: "crop", adv: "adv" } as const;

const SAFE = /^[A-Za-z0-9_.-]{1,64}$/;

/** Reads the queue filters and the open advisory from the query string. */
export function readQueue(search: string): QueueFilters & { adv: string | null } {
  const q = new URLSearchParams(search);
  const status = q.get(QUEUE_KEYS.status);
  const block = q.get(QUEUE_KEYS.block);
  const crop = q.get(QUEUE_KEYS.crop);
  const adv = q.get(QUEUE_KEYS.adv);
  return {
    status:
      status === "all" || STATUSES.includes(status as Status)
        ? (status as StatusFilter)
        : DEFAULT_STATUS,
    block: block && SAFE.test(block) ? block : null,
    crop: crop && SAFE.test(crop) ? crop : null,
    adv: adv && SAFE.test(adv) ? adv : null,
  };
}

/** Writes filters and the open advisory; defaults are left out, other keys kept. */
export function writeQueue(
  search: string,
  s: Partial<QueueFilters & { adv: string | null }>,
): string {
  const q = new URLSearchParams(search);
  const put = (key: string, value: string | null | undefined) => {
    if (value === undefined) return;
    if (value) q.set(key, value);
    else q.delete(key);
  };
  if (s.status !== undefined) put(QUEUE_KEYS.status, s.status === DEFAULT_STATUS ? null : s.status);
  put(QUEUE_KEYS.block, s.block);
  put(QUEUE_KEYS.crop, s.crop);
  put(QUEUE_KEYS.adv, s.adv);
  const out = q.toString();
  return out ? `?${out}` : "";
}

/**
 * Queue order: highest priority first, then Panchayat, crop and category, so the officer
 * works down from what matters most and the order is stable between refetches.
 */
export function sortQueue(items: readonly Advisory[]): Advisory[] {
  return [...items].sort(
    (a, b) =>
      LEVEL_INDEX[b.priority] - LEVEL_INDEX[a.priority] ||
      a.panchayat_id.localeCompare(b.panchayat_id) ||
      a.crop.localeCompare(b.crop) ||
      a.category.localeCompare(b.category),
  );
}

/** Applies the block and crop filters (status is filtered by the API). */
export function filterQueue(
  items: readonly Advisory[],
  f: Pick<QueueFilters, "block" | "crop">,
): Advisory[] {
  return items.filter(
    (a) => (!f.block || a.block_id === f.block) && (!f.crop || a.crop === f.crop),
  );
}

/**
 * New list position for a navigation key, or null for other keys. From no position,
 * ArrowDown and Home go to the first item and ArrowUp and End to the last.
 */
export function moveIndex(current: number, key: string, length: number): number | null {
  if (length === 0) return null;
  const has = current >= 0 && current < length;
  switch (key) {
    case "ArrowDown":
      return has ? Math.min(current + 1, length - 1) : 0;
    case "ArrowUp":
      return has ? Math.max(current - 1, 0) : length - 1;
    case "Home":
      return 0;
    case "End":
      return length - 1;
    default:
      return null;
  }
}

/** Distinct sorted values of a field, for filter options. */
export function optionsOf(items: readonly Advisory[], key: "block_id" | "crop"): string[] {
  return [...new Set(items.map((a) => a[key]))].sort();
}
