import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { DataMode } from "../api/types";

/** Mock-data notice under the top bar (Guide 5). Not dismissible. Shown only for "mock". */
export function Ribbon({ dataMode }: { dataMode: DataMode | undefined }) {
  const { t } = useTranslation();
  if (dataMode !== "mock") return null;
  return (
    <div className="ribbon" role="note">
      <Info size={16} aria-hidden="true" />
      <span>{t("shell.ribbon")}</span>
    </div>
  );
}
