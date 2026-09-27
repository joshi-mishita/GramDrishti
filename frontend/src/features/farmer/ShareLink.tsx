import { Share2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Advisory, DataMode } from "../../api/types";
import { formatDate } from "../../lib/format";
import { pickText } from "../../lib/text";
import { useAppStore } from "../../state/store";
import { shareText, whatsappUrl } from "./farmerData";

interface Props {
  advisory: Advisory;
  village: string;
  dataMode: DataMode | undefined;
}

/**
 * Share on WhatsApp (Guide 7): a wa.me link with the advisory in the current language.
 * The farmer chooses the chat in WhatsApp; no number is asked for or stored.
 */
export function ShareLink({ advisory, village, dataMode }: Props) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const action = pickText(advisory.action, lang);
  const text = shareText({
    action: action.text,
    reason: advisory.reason[action.lang] ?? advisory.reason.en,
    source: t("share.source", { village, date: formatDate(advisory.issue_date, lang) }),
    notice: dataMode === "mock" ? t("shell.ribbon") : null,
  });
  return (
    <a
      className="btn btn-farmer"
      href={whatsappUrl(text)}
      target="_blank"
      rel="noopener noreferrer"
      aria-label={t("share.label")}
    >
      <Share2 size={20} aria-hidden="true" />
      {t("share.share")}
    </a>
  );
}
