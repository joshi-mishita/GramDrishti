import type { LucideIcon } from "lucide-react";
import { CloudSun, House, Sprout } from "lucide-react";
import { NavLink, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";

const ITEMS: { to: string; key: string; icon: LucideIcon; end?: boolean }[] = [
  { to: "/farmer", key: "today", icon: House, end: true },
  { to: "/farmer/forecast", key: "forecast", icon: CloudSun },
  { to: "/farmer/farm", key: "farm", icon: Sprout },
];

/** Bottom navigation of the farmer app: three items, always visible (Guide 7). */
export function FarmerNav() {
  const { t } = useTranslation();
  const { search } = useLocation();
  return (
    <nav className="farmer-nav" aria-label={t("farmerNav.label")}>
      <ul>
        {ITEMS.map(({ to, key, icon: Icon, end }) => (
          <li key={key}>
            <NavLink to={{ pathname: to, search }} end={end} className="farmer-nav-link">
              <Icon size={22} aria-hidden="true" />
              <span>{t(`farmerNav.${key}`)}</span>
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  );
}
