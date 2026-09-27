import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { DataMode } from "../api/types";

/** Mock-data notice under the top bar (Guide 5). Not dismissible. Shown only for "mock". */
export function Ribbon({ dataMode }: { dataMode: DataMode | undefined }) {
  const { t } = useTranslation();
  if (dataMode !== "mock") return null;
  return (
    // A named region, so the notice sits in a landmark and screen-reader users can jump to it.
    <section className="ribbon" aria-labelledby="ribbon-text">
      <Info size={16} aria-hidden="true" />
      <span id="ribbon-text">{t("shell.ribbon")}</span>
    </section>
  );
}
