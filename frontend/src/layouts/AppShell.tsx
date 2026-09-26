import { Suspense, useEffect } from "react";
import { Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMeta } from "../api/hooks";
import { setRequestRole } from "../api/client";
import { applyLang } from "../i18n";
import { DEFAULT_ISSUE_DATE } from "../lib/config";
import { useAppStore } from "../state/store";
import { useUrlSync } from "../state/useUrlSync";
import { ErrorBoundary } from "../components/ErrorBoundary";
import { Ribbon } from "../components/Ribbon";
import { Skeleton } from "../components/states";
import { TopBar } from "../components/TopBar";

/** Top bar, mock ribbon and the role layout below them. Owns URL and language sync. */
export function AppShell() {
  const { t } = useTranslation();
  const meta = useMeta();
  const lang = useAppStore((s) => s.lang);
  const role = useAppStore((s) => s.role);
  const issueDate = useAppStore((s) => s.issueDate);
  const setIssueDate = useAppStore((s) => s.setIssueDate);
  useUrlSync();

  useEffect(() => applyLang(lang), [lang]);
  useEffect(() => setRequestRole(role), [role]);

  // Pick an issue date once /meta is known: keep the URL's date if the API offers it.
  useEffect(() => {
    const dates = meta.data?.available_issue_dates;
    if (!dates?.length) return;
    if (issueDate && dates.includes(issueDate)) return;
    setIssueDate(dates.includes(DEFAULT_ISSUE_DATE) ? DEFAULT_ISSUE_DATE : (dates.at(-1) ?? null));
  }, [meta.data, issueDate, setIssueDate]);

  return (
    <div className={`shell shell-${role}`}>
      <a className="skip-link" href="#main">
        {t("shell.skip")}
      </a>
      <TopBar />
      <Ribbon dataMode={meta.data?.data_mode} />
      <ErrorBoundary message={t("states.renderError")}>
        <Suspense fallback={<Skeleton label={t("states.loading", { what: "" })} />}>
          <Outlet />
        </Suspense>
      </ErrorBoundary>
    </div>
  );
}
