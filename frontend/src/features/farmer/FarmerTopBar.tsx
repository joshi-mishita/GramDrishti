import { useTranslation } from "react-i18next";
import { LangSwitch } from "../../components/LangSwitch";
import { OfflinePill } from "../../components/OfflinePill";
import { useFarmerContext } from "./useFarmerContext";

/** Farmer top bar (Guide 7): product, Panchayat, offline pill and the three languages. */
export function FarmerTopBar() {
  const { t } = useTranslation();
  const { village } = useFarmerContext();
  return (
    <header className="farmer-top">
      <div className="farmer-top-row">
        <span className="wordmark">{t("app.name")}</span>
        <OfflinePill />
      </div>
      <p className="farmer-village">
        <span className="visually-hidden">{t("farmer.villageLabel")}: </span>
        {village || "…"}
      </p>
      <LangSwitch />
    </header>
  );
}
