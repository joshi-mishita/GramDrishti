import { CloudSun } from "lucide-react";
import { useTranslation } from "react-i18next";
import { EmptyState } from "../../components/states";

/** Forecast (Guide 7): the 5-day strip arrives with the farmer app session. */
export default function FarmerForecast() {
  const { t } = useTranslation();
  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.forecastTitle")}</h1>
      </header>
      <EmptyState icon={CloudSun} title={t("farmer.forecastNotBuilt")} />
    </div>
  );
}
