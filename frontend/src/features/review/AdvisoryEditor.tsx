import { useEffect, useId, useRef, useState, type KeyboardEvent } from "react";
import { Check, CircleAlert, PencilLine, Undo2, X } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useReviewAdvisory } from "../../api/hooks";
import { isApiError } from "../../api/errors";
import { LANGS, type Advisory, type Lang } from "../../api/types";
import { ConfidenceLabel } from "../../components/ConfidenceLabel";
import { RiskChip } from "../../components/RiskChip";
import { useToast } from "../../components/toastContext";
import { formatDate } from "../../lib/format";
import { LANG_OPTIONS } from "../../lib/langs";
import { useAppStore } from "../../state/store";
import { AuditTrail } from "./AuditTrail";
import { StatusChip } from "./StatusChip";
import { advisoryTitle, placeLabel, shortName } from "./labels";
import {
  FIELDS,
  TOAST_KEY,
  blockedReason,
  changedCells,
  droppedTranslations,
  missingEnglish,
  reviewRequest,
  setText,
  shortcutKind,
  textsOf,
  type ReviewKind,
} from "./reviewState";

interface Props {
  advisory: Advisory;
  panchayatName: string;
  reviewer: string;
  /** False when advisories come from the read-only demo files. */
  writable: boolean;
}

/**
 * One advisory under review (Guide 6.3 and 8 DiffEditor): header, evidence, the three
 * texts in three languages with changed-since-draft markers, the review buttons and the
 * audit trail. Mount it with a key that changes when the advisory changes on the server,
 * so the edit state starts again from the saved texts.
 */
export function AdvisoryEditor({ advisory: a, panchayatName, reviewer, writable }: Props) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const toast = useToast();
  const review = useReviewAdvisory();
  const id = useId();
  const [original] = useState(() => textsOf(a));
  const [texts, setTexts] = useState(original);
  const [tab, setTab] = useState<Lang>("en");
  const [rejecting, setRejecting] = useState(false);
  const [note, setNote] = useState("");
  const tabRefs = useRef<Record<Lang, HTMLButtonElement | null>>({ en: null, hi: null, pa: null });

  const changed = changedCells(original, texts);
  const dirty = changed.length > 0;
  const dropped = droppedTranslations(original, texts);
  const missing = missingEnglish(texts);
  const state = { dirty, missing, reviewer, note, writable, status: a.status };
  const isChanged = (field: string, l: Lang) =>
    changed.some((c) => c.field === field && c.lang === l);

  const submit = (kind: ReviewKind) => {
    if (review.isPending || blockedReason(kind, state)) return;
    const body = reviewRequest(kind, { reviewer, note, original, current: texts });
    // mutateAsync, not mutate(..., { onSuccess }): a successful review changes the cached
    // advisory, which remounts this editor, and per-call callbacks of an unmounted
    // component never run. The promise still resolves. Errors show through review.error.
    review
      .mutateAsync({ id: a.id, body })
      .then((updated) =>
        toast(
          t("review.toastLine", { word: t(TOAST_KEY[body.action]), what: shortName(t, updated) }),
        ),
      )
      .catch(() => undefined);
  };

  // Ctrl+Enter (Cmd+Enter on a Mac) approves from anywhere on the screen, also while typing.
  const submitRef = useRef(submit);
  const dirtyRef = useRef(dirty);
  useEffect(() => {
    submitRef.current = submit;
    dirtyRef.current = dirty;
  });
  useEffect(() => {
    const onKey = (e: globalThis.KeyboardEvent) => {
      if (e.key === "Enter" && (e.ctrlKey || e.metaKey) && !rejecting) {
        e.preventDefault();
        submitRef.current(shortcutKind(dirtyRef.current));
      }
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [rejecting]);

  const onTabKey = (e: KeyboardEvent<HTMLButtonElement>) => {
    const i = LANGS.indexOf(tab);
    const next =
      e.key === "ArrowRight"
        ? LANGS[(i + 1) % LANGS.length]
        : e.key === "ArrowLeft"
          ? LANGS[(i + LANGS.length - 1) % LANGS.length]
          : e.key === "Home"
            ? LANGS[0]
            : e.key === "End"
              ? LANGS[LANGS.length - 1]
              : undefined;
    if (!next) return;
    e.preventDefault();
    setTab(next);
    tabRefs.current[next]?.focus();
  };

  const reason = (kind: ReviewKind) => blockedReason(kind, state);
  const hint = [reason("approve"), reason("edit")].find(
    (r) =>
      r === "readOnly" || r === "noReviewer" || r === "missingEnglish" || r === "alreadyApproved",
  );
  const error = review.error;

  return (
    <article className="editor" aria-labelledby={`${id}-title`}>
      <header className="editor-head">
        <h2 id={`${id}-title`}>{advisoryTitle(t, a)}</h2>
        <p className="muted">
          {placeLabel(panchayatName, a.panchayat_id).id
            ? t("review.where", { name: panchayatName, pid: a.panchayat_id, block: a.block_id })
            : t("review.whereNamed", { name: panchayatName, block: a.block_id })}
        </p>
        <dl className="editor-meta">
          <div>
            <dt>{t("review.status")}</dt>
            <dd>
              <StatusChip status={a.status} />
            </dd>
          </div>
          <div>
            <dt>{t("review.priority")}</dt>
            <dd>
              <RiskChip level={a.priority} />
            </dd>
          </div>
          <div>
            <dt>{t("review.confidence")}</dt>
            <dd>
              <ConfidenceLabel confidence={a.confidence} />
            </dd>
          </div>
          <div>
            <dt>{t("review.valid")}</dt>
            <dd>
              {a.valid_from === a.valid_to
                ? formatDate(a.valid_from, lang, "day")
                : t("review.validRange", {
                    from: formatDate(a.valid_from, lang, "day"),
                    to: formatDate(a.valid_to, lang, "day"),
                  })}
            </dd>
          </div>
        </dl>
        {a.thresholds_status === "placeholder" ? (
          <p className="editor-note">{t("review.thresholdsPending")}</p>
        ) : null}
        {a.translation_status === "needs_native_review" ? (
          <p className="editor-note">{t("review.translationPending")}</p>
        ) : null}
      </header>

      <section aria-labelledby={`${id}-texts`}>
        <h3 id={`${id}-texts`} className="visually-hidden">
          {t("review.texts")}
        </h3>
        <div className="tabs" role="tablist" aria-label={t("review.languages")}>
          {LANG_OPTIONS.map((o) => {
            const edited = changed.some((c) => c.lang === o.value);
            return (
              <button
                key={o.value}
                ref={(el) => {
                  tabRefs.current[o.value] = el;
                }}
                type="button"
                role="tab"
                id={`${id}-tab-${o.value}`}
                aria-selected={tab === o.value}
                aria-controls={`${id}-panel`}
                tabIndex={tab === o.value ? 0 : -1}
                className="tab"
                onClick={() => setTab(o.value)}
                onKeyDown={onTabKey}
              >
                <span lang={o.lang}>{o.label}</span>
                {edited ? (
                  <span className="changed-mark">
                    <PencilLine size={12} aria-hidden="true" />
                    {t("review.changed")}
                  </span>
                ) : null}
              </button>
            );
          })}
        </div>
        <div
          className="tab-panel"
          role="tabpanel"
          id={`${id}-panel`}
          aria-labelledby={`${id}-tab-${tab}`}
        >
          {FIELDS.map((field) => {
            const fieldId = `${id}-${field}-${tab}`;
            const empty = tab !== "en" && original[field][tab].trim() === "";
            const willDrop = dropped.some((d) => d.field === field && d.lang === tab);
            return (
              <div key={field} className="text-field">
                <label htmlFor={fieldId}>
                  {t(`review.field.${field}`)}
                  {isChanged(field, tab) ? (
                    <span className="changed-mark">
                      <PencilLine size={12} aria-hidden="true" />
                      {t("review.changedSinceDraft")}
                    </span>
                  ) : null}
                </label>
                <textarea
                  id={fieldId}
                  lang={tab}
                  rows={field === "fallback" ? 2 : 3}
                  value={texts[field][tab]}
                  placeholder={empty ? t("review.noTranslation") : undefined}
                  aria-invalid={tab === "en" && missing.includes(field) ? true : undefined}
                  className={isChanged(field, tab) ? "is-changed" : undefined}
                  onChange={(e) => setTexts((x) => setText(x, field, tab, e.target.value))}
                />
                {willDrop ? <p className="field-warn">{t("review.willDrop")}</p> : null}
                {tab === "en" && missing.includes(field) ? (
                  <p className="field-warn">{t("review.needEnglish")}</p>
                ) : null}
              </div>
            );
          })}
        </div>
      </section>

      <section aria-labelledby={`${id}-evidence`}>
        <h3 id={`${id}-evidence`}>{t("review.evidence")}</h3>
        {a.evidence.length ? (
          <dl className="evidence">
            {a.evidence.map((e) => (
              <div key={e.label}>
                <dt lang="en">{e.label}</dt>
                <dd lang="en" className={e.value.length <= 16 ? "num nowrap" : "num"}>
                  {e.value}
                </dd>
              </div>
            ))}
          </dl>
        ) : (
          <p className="muted">{t("review.noEvidence")}</p>
        )}
        {lang !== "en" && a.evidence.length ? (
          <p className="muted small">{t("review.evidenceEnglish")}</p>
        ) : null}
      </section>

      <section className="review-actions" aria-label={t("review.actions")}>
        {rejecting ? (
          <div className="reject-form">
            <label htmlFor={`${id}-note`}>{t("review.rejectReason")}</label>
            <textarea
              id={`${id}-note`}
              rows={2}
              value={note}
              onChange={(e) => setNote(e.target.value)}
              autoFocus
            />
            <div className="button-row">
              <button
                type="button"
                className="btn btn-danger"
                disabled={!!reason("reject") || review.isPending}
                onClick={() => submit("reject")}
              >
                <X size={16} aria-hidden="true" />
                {t("review.reject")}
              </button>
              <button
                type="button"
                className="btn"
                onClick={() => {
                  setRejecting(false);
                  setNote("");
                }}
              >
                {t("review.cancel")}
              </button>
            </div>
          </div>
        ) : (
          <div className="button-row">
            <button
              type="button"
              className="btn btn-primary"
              disabled={!!reason("approve") || review.isPending}
              onClick={() => submit("approve")}
            >
              <Check size={16} aria-hidden="true" />
              {t("review.approve")}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              disabled={!!reason("edit") || review.isPending}
              onClick={() => submit("edit")}
            >
              <PencilLine size={16} aria-hidden="true" />
              {t("review.saveApprove")}
            </button>
            <button
              type="button"
              className="btn"
              disabled={
                !writable || !reviewer.trim() || a.status === "rejected" || review.isPending
              }
              onClick={() => setRejecting(true)}
            >
              <X size={16} aria-hidden="true" />
              {t("review.reject")}
            </button>
            {dirty ? (
              <button type="button" className="btn" onClick={() => setTexts(original)}>
                <Undo2 size={16} aria-hidden="true" />
                {t("review.undo")}
              </button>
            ) : null}
          </div>
        )}
        {hint ? <p className="muted small">{t(`review.blocked.${hint}`)}</p> : null}
        {dirty && !hint ? <p className="muted small">{t("review.blocked.hasEdits")}</p> : null}
        <p className="muted small keys-hint">{t("review.keys")}</p>
        {error ? (
          <p className="inline-error" role="alert">
            <CircleAlert size={16} aria-hidden="true" />
            <span>
              {t("review.saveFailed")}{" "}
              <span className="muted">
                {isApiError(error) && error.status
                  ? `${error.status} ${error.code}: ${error.message}`
                  : error.message}
              </span>
            </span>
          </p>
        ) : null}
      </section>

      <section aria-labelledby={`${id}-audit`}>
        <h3 id={`${id}-audit`}>{t("review.history")}</h3>
        <AuditTrail audit={a.audit} />
      </section>
    </article>
  );
}
