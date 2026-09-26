import { useTranslation } from "react-i18next";
import type { Level } from "../api/types";

/** Severity colour plus the word, never colour alone (Guide 8). */
export function RiskChip({ level }: { level: Level }) {
  const { t } = useTranslation();
  return (
    <span className="chip">
      <span className={`chip-swatch sev-${level}`} aria-hidden="true" />
      {t(`levels.${level}`)}
    </span>
  );
}
