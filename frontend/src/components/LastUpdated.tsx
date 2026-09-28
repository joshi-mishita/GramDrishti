import { History } from "lucide-react";
import { useTranslation } from "react-i18next";
import { formatStamp } from "../lib/format";
import { useLastUpdated } from "../lib/network";
import { useAppStore } from "../state/store";

/**
 * "Saved copy. Last updated Mon 16 Dec, 08:10" while anything on screen came from the
 * service worker's copy instead of the network (Guide 7 and 10.2). Hidden otherwise.
 */
export function LastUpdated() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const stamp = useLastUpdated();
  if (stamp === null) return null;
  const time = formatStamp(stamp, lang);
  return (
    <p className="last-updated" role="status">
      <History size={16} aria-hidden="true" />
      {time ? t("offline.lastUpdated", { time }) : t("offline.lastUpdatedUnknown")}
    </p>
  );
}
