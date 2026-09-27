import { useTranslation } from "react-i18next";
import type { ForecastDay } from "../../api/types";
import { SPRAY_ICON } from "./farmerData";

/** Spray suitability as icon plus word (never colour alone). */
export function SprayWord({ rating }: { rating: ForecastDay["derived"]["spray_rating"] }) {
  const { t } = useTranslation();
  if (!rating) return <span>–</span>;
  const Icon = SPRAY_ICON[rating];
  return (
    <span className={`spray spray-${rating}`}>
      <Icon size={20} aria-hidden="true" />
      <strong>{t(`farmer.sprayWord.${rating}`)}</strong>
      <span className="spray-help">{t(`farmer.sprayHelp.${rating}`)}</span>
    </span>
  );
}
