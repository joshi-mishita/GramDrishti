import type { LucideIcon } from "lucide-react";
import { ChartScatter, ClipboardCheck, ListOrdered, Map, Scale } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const ITEMS: { to: string; key: string; icon: LucideIcon }[] = [
  { to: "/map", key: "map", icon: Map },
  { to: "/priority", key: "priority", icon: ListOrdered },
  { to: "/review", key: "review", icon: ClipboardCheck },
  { to: "/verification", key: "verification", icon: ChartScatter },
  { to: "/impact", key: "impact", icon: Scale },
];

/** Left icon-plus-label navigation of the officer console; a bottom bar on phones. */
export function SideNav() {
  const { t } = useTranslation();
  const { search } = useLocation();
  return (
    <nav className="sidenav" aria-label={t("nav.label")}>
      <ul>
        {ITEMS.map(({ to, key, icon: Icon }) => (
          <li key={key}>
            <NavLink to={{ pathname: to, search }} className="sidenav-link">
              <Icon size={18} aria-hidden="true" />
              <span>{t(`nav.${key}`)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
      <p className="sidenav-note">{t("shell.noLogin")}</p>
    </nav>
  );
}
