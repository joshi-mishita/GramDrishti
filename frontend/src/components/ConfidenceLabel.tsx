import { useId } from "react";
import { CircleHelp } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Confidence } from "../api/types";
import { confidenceWord } from "../lib/words";

const TIP_KEY = {
  likely: "confidence.tipLikely",
  possible: "confidence.tipPossible",
  uncertain: "confidence.tipUncertain",
} as const;

/**
 * Confidence as a word (Guide 2.7): Likely, Possible or Uncertain, from the contract's
 * high, medium or low. Never a score. The explanation appears on hover and on keyboard
 * focus, and screen readers get it as the description.
 */
export function ConfidenceLabel({ confidence }: { confidence: Confidence | null | undefined }) {
  const { t } = useTranslation();
  const tipId = useId();
  const word = confidenceWord(confidence);
  return (
    <span className="confidence" tabIndex={0} aria-describedby={tipId}>
      <span className={`confidence-word confidence-${word}`}>{t(`confidence.${word}`)}</span>
      <CircleHelp size={14} aria-hidden="true" className="confidence-icon" />
      <span role="tooltip" id={tipId} className="tooltip-bubble">
        {t(TIP_KEY[word])}
      </span>
    </span>
  );
}
