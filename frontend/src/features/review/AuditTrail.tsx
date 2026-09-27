import { useTranslation } from "react-i18next";
import { LANGS, type AuditEntry, type Lang } from "../../api/types";
import { formatDateTime } from "../../lib/format";
import { useAppStore } from "../../state/store";
import { FIELDS, type Field } from "./reviewState";

const ACTION_KEY: Record<string, string> = {
  created: "review.auditCreated",
  approved: "review.auditApproved",
  edited: "review.auditEdited",
  rejected: "review.auditRejected",
};

type Texts = Partial<Record<Lang, string | null>>;

/** Text fields an audit entry changed, with the before and after text per language. */
function textChanges(e: AuditEntry): { field: Field; lang: Lang; before: string; after: string }[] {
  const before = (e.before ?? {}) as Record<string, Texts | undefined>;
  const after = (e.after ?? {}) as Record<string, Texts | undefined>;
  return FIELDS.flatMap((field) => {
    const b = before[field];
    const a = after[field];
    if (!a) return [];
    return LANGS.filter((l) => (b?.[l] ?? "") !== (a[l] ?? "")).map((lang) => ({
      field,
      lang,
      before: b?.[lang] ?? "",
      after: a[lang] ?? "",
    }));
  });
}

/**
 * Every step of an advisory, oldest first (Guide 6.3: a trust feature). Edits show the
 * text before and after, per field and language.
 */
export function AuditTrail({ audit }: { audit: readonly AuditEntry[] }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  if (audit.length === 0) return <p className="muted">{t("review.auditEmpty")}</p>;
  return (
    <ol className="audit">
      {audit.map((e, i) => {
        const changes = textChanges(e);
        const actor = e.actor === "system" ? t("review.auditSystem") : e.actor;
        return (
          <li key={`${e.at}-${i}`}>
            <p className="audit-line">
              <time dateTime={e.at} className="num">
                {formatDateTime(e.at, lang)}
              </time>
              <span>
                <strong>
                  {t(ACTION_KEY[e.action] ?? "review.auditOther", { action: e.action })}
                </strong>{" "}
                {t("review.auditBy", { actor })}
              </span>
            </p>
            {e.note ? <p className="audit-note">{e.note}</p> : null}
            {changes.length ? (
              <details className="audit-changes">
                <summary>
                  {t("review.auditChanged", {
                    fields: changes
                      .map((c) => `${t(`review.field.${c.field}`)} (${t(`langNames.${c.lang}`)})`)
                      .join(", "),
                  })}
                </summary>
                <dl>
                  {changes.map((c) => (
                    <div key={`${c.field}-${c.lang}`}>
                      <dt>
                        {t(`review.field.${c.field}`)} ({t(`langNames.${c.lang}`)})
                      </dt>
                      <dd>
                        <span className="muted">{t("review.auditBefore")}</span>{" "}
                        <span lang={c.lang}>{c.before || t("review.auditNone")}</span>
                      </dd>
                      <dd>
                        <span className="muted">{t("review.auditAfter")}</span>{" "}
                        <span lang={c.lang}>{c.after || t("review.auditNone")}</span>
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            ) : null}
          </li>
        );
      })}
    </ol>
  );
}
