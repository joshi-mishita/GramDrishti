import { useTranslation } from "react-i18next";
import { LEVELS, type RiskType } from "../../api/types";
import { RiskChip } from "../../components/RiskChip";

interface Props {
  type: RiskType;
  placeholder: boolean;
}

/**
 * Key for the risk layer: the four severity chips, each with its word (Guide 8: colour and
 * word always together), plus the "no value" grey.
 */
export function RiskLegend({ type, placeholder }: Props) {
  const { t } = useTranslation();
  return (
    <figure className="legend">
      <figcaption className="legend-title">
        {t("risk.legendTitle", { risk: t(`risks.${type}`) })}
      </figcaption>
      <ul className="risk-legend">
        {[...LEVELS].reverse().map((l) => (
          <li key={l}>
            <RiskChip level={l} />
          </li>
        ))}
      </ul>
      <p className="legend-novalue">
        <span className="legend-swatch" aria-hidden="true" />
        {t("legend.noValue")}
      </p>
      {placeholder ? <p className="legend-caption muted">{t("thresholds.placeholder")}</p> : null}
    </figure>
  );
}
