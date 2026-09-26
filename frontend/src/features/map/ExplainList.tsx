import type { LucideIcon } from "lucide-react";
import {
  CloudRain,
  Droplet,
  Droplets,
  Leaf,
  Scale,
  Sun,
  ThermometerSnowflake,
  ThermometerSun,
  Wind,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { useExplain } from "../../api/hooks";
import type { Effect, Explain } from "../../api/types";
import { ProvenanceNote } from "../../components/ProvenanceNote";
import { QueryBoundary } from "../../components/QueryBoundary";
import { EmptyState } from "../../components/states";
import { VAR_DIGITS, formatSigned } from "../../lib/format";
import { UNITS } from "../../lib/ramps";
import { pickText } from "../../lib/text";
import { useAppStore } from "../../state/store";

/** Small icon per effect; the effect word is always printed next to it. */
const EFFECT_ICONS: Record<Effect, LucideIcon> = {
  warmer: ThermometerSun,
  cooler: ThermometerSnowflake,
  wetter: CloudRain,
  drier: Sun,
  more_humid: Droplets,
  less_humid: Droplet,
  windier: Wind,
  calmer: Leaf,
};

/** "Why is it different from the block?" for the chosen day and variable (/explain). */
export function ExplainList({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const issueDate = useAppStore((s) => s.issueDate);
  const leadDay = useAppStore((s) => s.leadDay);
  const variable = useAppStore((s) => s.variable);
  const explain = useExplain(pid, issueDate, leadDay, variable);

  return (
    <section aria-labelledby="explain-title">
      <h3 id="explain-title" className="section-title">
        {t("panel.explainTitle")}
      </h3>
      <QueryBoundary query={explain} what={t("what.explain")}>
        {(e) => <ExplainBody explain={e} />}
      </QueryBoundary>
    </section>
  );
}

function ExplainBody({ explain }: { explain: Explain }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const variable = t(`vars.${explain.var}`);

  if (explain.reasons.length === 0) {
    return <EmptyState icon={Scale} title={t("panel.explainEmpty", { variable })} />;
  }

  const texts = explain.reasons.map((r) => pickText(r.text, lang));
  const fellBack = texts.some((x) => x.lang !== lang);
  return (
    <div className="stack">
      {explain.delta_vs_block !== null ? (
        <p className="small">
          {t("panel.explainDelta", {
            variable,
            value: formatSigned(explain.delta_vs_block, lang, VAR_DIGITS[explain.var]),
            unit: t(`units.${UNITS[explain.var]}`),
          })}
        </p>
      ) : null}
      <ul className="explain-list">
        {explain.reasons.map((r, i) => {
          const Icon = EFFECT_ICONS[r.effect];
          const text = texts[i];
          return (
            <li key={`${r.feature}-${String(i)}`}>
              <span className={`effect effect-${r.effect}`}>
                <Icon size={16} aria-hidden="true" />
                {t(`effects.${r.effect}`)}
              </span>
              <span lang={text?.lang}>{text?.text}</span>
            </li>
          );
        })}
      </ul>
      {fellBack ? <p className="muted small">{t("panel.explainEnglishOnly")}</p> : null}
      <p className="muted small">{t("panel.explainMethod")}</p>
      <ProvenanceNote provenance={explain.provenance} />
    </div>
  );
}
