import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMeta } from "../api/hooks";
import { IssueDateSelect } from "./IssueDateSelect";
import { LangSwitch } from "./LangSwitch";
import { RoleSwitch } from "./RoleSwitch";

/** Product name, district, issue date, role and language (Guide 2.5 and 6.1). */
export function TopBar() {
  const { t } = useTranslation();
  const meta = useMeta();
  const { search } = useLocation();
  return (
    <header className="topbar">
      <div className="topbar-id">
        <Link to={{ pathname: "/map", search }} className="wordmark">
          {t("app.name")}
        </Link>
        <span className="topbar-district">
          <span className="visually-hidden">{t("shell.district")}: </span>
          {meta.data?.district ?? (meta.isError ? t("shell.metaFailed") : "…")}
        </span>
      </div>
      <IssueDateSelect />
      <div className="topbar-switches">
        <RoleSwitch />
        <LangSwitch />
      </div>
    </header>
  );
}
