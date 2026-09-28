import { Info } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { DataMode } from "../api/types";

/**
 * Mock-data notice under the top bar (Guide 5). Not dismissible. Hidden only once a response
 * has said "real": while loading or with the API down the data mode is unknown, and everything
 * this build can show is synthetic (CLAUDE.md rule 1, known issue L1).
 */
export function Ribbon({ dataMode }: { dataMode: DataMode | undefined }) {
  const { t } = useTranslation();
  if (dataMode === "real") return null;
  return (
    // A named region, so the notice sits in a landmark and screen-reader users can jump to it.
    <section className="ribbon" aria-labelledby="ribbon-text">
      <Info size={16} aria-hidden="true" />
      <span id="ribbon-text">{t("shell.ribbon")}</span>
    </section>
  );
}
