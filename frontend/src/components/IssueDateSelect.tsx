import { useId } from "react";
import { useTranslation } from "react-i18next";
import { useMeta } from "../api/hooks";
import { formatDate } from "../lib/format";
import { useAppStore } from "../state/store";

/** Issue date picker fed by /meta.available_issue_dates, with the reason for each date. */
export function IssueDateSelect() {
  const { t } = useTranslation();
  const id = useId();
  const meta = useMeta();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const setIssueDate = useAppStore((s) => s.setIssueDate);

  const labels = new Map((meta.data?.issue_date_info ?? []).map((i) => [i.date, i.label]));
  const dates = meta.data?.available_issue_dates ?? [];

  return (
    <div className="field-inline">
      <label htmlFor={id}>{t("shell.issueDate")}</label>
      <select
        id={id}
        value={issueDate ?? ""}
        disabled={!meta.data}
        onChange={(e) => setIssueDate(e.target.value)}
      >
        {!meta.data ? <option value="">{t("shell.metaLoading")}</option> : null}
        {dates.map((d) => {
          const label = labels.get(d);
          return (
            <option key={d} value={d}>
              {formatDate(d, lang)}
              {label ? ` · ${label}` : ""}
            </option>
          );
        })}
      </select>
    </div>
  );
}
