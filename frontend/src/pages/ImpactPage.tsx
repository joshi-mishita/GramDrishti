import { useState } from "react";
import { Scale } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useImpact } from "../api/hooks";
import type { Decision, LocalizedText } from "../api/types";
import { PageHeader } from "../components/PageHeader";
import { ProvenanceNote } from "../components/ProvenanceNote";
import { QueryBoundary } from "../components/QueryBoundary";
import { SegmentedControl } from "../components/SegmentedControl";
import { EmptyState } from "../components/states";
import { useAppStore } from "../state/store";
import { pickText } from "../lib/text";

const DECISIONS: readonly Decision[] = ["spray", "heat_alert", "irrigation_wait"];

/** Decision replay (Guide 6.5). Counts wait for the verification job; rules are shown now. */
export default function ImpactPage() {
  const { t } = useTranslation();
  const [decision, setDecision] = useState<Decision>("spray");
  const impact = useImpact(decision);

  return (
    <div className="page">
      <PageHeader title={t("impact.title")} />
      <div className="toolbar">
        <SegmentedControl<Decision>
          legend={t("impact.decision")}
          showLegend
          name="decision"
          variant="wrap"
          value={decision}
          options={DECISIONS.map((d) => ({ value: d, label: t(`impact.decisions.${d}`) }))}
          onChange={setDecision}
        />
      </div>
      <QueryBoundary query={impact} what={t("what.impact")}>
        {(i) => (
          <div className="panel panel-pad stack">
            {i.rule ? (
              <dl className="rules">
                <RuleRow label={t("impact.ruleModel")} text={i.rule.model} />
                <RuleRow label={t("impact.ruleBlock")} text={i.rule.block} />
              </dl>
            ) : null}
            <ProvenanceNote provenance={i.provenance} />
            <EmptyState icon={Scale} title={t("impact.notBuilt")} />
          </div>
        )}
      </QueryBoundary>
    </div>
  );
}

function RuleRow({ label, text }: { label: string; text: LocalizedText }) {
  const lang = useAppStore((s) => s.lang);
  const picked = pickText(text, lang);
  return (
    <div>
      <dt>{label}</dt>
      <dd lang={picked.lang}>{picked.text}</dd>
    </div>
  );
}
