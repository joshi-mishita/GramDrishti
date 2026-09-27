import { WifiOff } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useOnline } from "../lib/network";

/** "Offline" in the top bar while the browser has no connection (Guide 10.2). */
export function OfflinePill() {
  const { t } = useTranslation();
  const online = useOnline();
  if (online) return null;
  return (
    <span className="offline-pill" role="status" aria-label={t("offline.pillLabel")}>
      <WifiOff size={14} aria-hidden="true" />
      {t("offline.pill")}
    </span>
  );
}
