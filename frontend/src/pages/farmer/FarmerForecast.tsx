import { CloudRain, SprayCan, Thermometer, Wind } from "lucide-react";
import { useTranslation } from "react-i18next";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { FeedbackCard } from "../../features/farmer/FeedbackCard";
import { rainText, tempText } from "../../features/farmer/forecastText";
import { SprayWord } from "../../features/farmer/SprayWord";
import { useFarmerContext } from "../../features/farmer/useFarmerContext";
import { formatDate, formatNumber } from "../../lib/format";
import { useAppStore } from "../../state/store";

/**
 * Forecast (Guide 7): five days, one block per day with rain (words and mm), temperature,
 * wind and spray suitability. Days stack vertically so the words fit at 360 px (D103).
 */
export default function FarmerForecast() {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const { forecast, village, pid } = useFarmerContext();

  return (
    <div className="farmer-page">
      <header className="farmer-head">
        <h1>{t("farmer.forecastTitle")}</h1>
        {village ? <p className="muted">{t("farmer.forecastSub", { village })}</p> : null}
      </header>
      <QueryBoundary
        query={forecast}
        what={t("what.forecastPanchayat")}
        isEmpty={(f) => f.days.length === 0}
        empty={<EmptyState title={t("panel.noDay")} />}
      >
        {(f) => (
          <>
            <ol className="fc-days">
              {f.days.map((day) => (
                <li key={day.date} className="fc-day">
                  <h2 className="fc-date">{formatDate(day.date, lang, "day")}</h2>
                  <dl className="fc-rows">
                    <div>
                      <dt>
                        <CloudRain size={20} aria-hidden="true" />
                        {t("farmer.rain")}
                      </dt>
                      <dd>{rainText(day, lang, t)}</dd>
                    </div>
                    <div>
                      <dt>
                        <Thermometer size={20} aria-hidden="true" />
                        {t("farmer.temp")}
                      </dt>
                      <dd>{tempText(day, lang, t)}</dd>
                    </div>
                    <div>
                      <dt>
                        <Wind size={20} aria-hidden="true" />
                        {t("farmer.wind")}
                      </dt>
                      <dd>
                        {t("farmer.windValue", { value: formatNumber(day.wind.p50, lang, 0) })}
                      </dd>
                    </div>
                    <div>
                      <dt>
                        <SprayCan size={20} aria-hidden="true" />
                        {t("farmer.spray")}
                      </dt>
                      <dd>
                        <SprayWord rating={day.derived.spray_rating ?? null} />
                      </dd>
                    </div>
                  </dl>
                </li>
              ))}
            </ol>
            <p className="muted small">{t("farmer.sprayNote")}</p>
          </>
        )}
      </QueryBoundary>
      {pid ? <FeedbackCard pid={pid} /> : null}
    </div>
  );
}
