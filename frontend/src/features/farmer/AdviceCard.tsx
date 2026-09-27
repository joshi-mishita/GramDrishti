import { useTranslation } from "react-i18next";
import type { Advisory, DataMode } from "../../api/types";
import { ConfidenceLabel } from "../../components/ConfidenceLabel";
import { formatDate } from "../../lib/format";
import { confidenceWord } from "../../lib/words";
import { pickText } from "../../lib/text";
import { useAppStore } from "../../state/store";
import { CATEGORY_ICON, firstSentence } from "./farmerData";
import { ListenButton } from "./ListenButton";
import { ShareLink } from "./ShareLink";

interface Props {
  advisory: Advisory;
  village: string;
  dataMode: DataMode | undefined;
  /** The top advisory: full-width block with the action in 24 px (Guide 7). */
  hero?: boolean;
}

/** Days an advisory is for, in words. */
function useValidity(a: Advisory): string {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const from = formatDate(a.valid_from, lang, "day");
  return a.valid_to && a.valid_to !== a.valid_from
    ? t("farmer.validDays", { from, to: formatDate(a.valid_to, lang, "day") })
    : t("farmer.validDay", { date: from });
}

/** The whole reason and the fallback ("if things change"). */
function FullReason({ advisory }: { advisory: Advisory }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const reason = pickText(advisory.reason, lang);
  const fallback = advisory.fallback ? pickText(advisory.fallback, lang) : null;
  return (
    <>
      <p lang={reason.lang}>{reason.text}</p>
      {fallback?.text ? (
        <p lang={fallback.lang}>
          <strong>{t("farmer.fallbackLabel")}: </strong>
          {fallback.text}
        </p>
      ) : null}
    </>
  );
}

/** Reason in full, the fallback, and the Listen and Share buttons. */
function AdviceBody({ advisory, village, dataMode }: Props) {
  return (
    <>
      <FullReason advisory={advisory} />
      <div className="btn-row">
        <ListenButton advisory={advisory} />
        <ShareLink advisory={advisory} village={village} dataMode={dataMode} />
      </div>
    </>
  );
}

/**
 * One approved advisory. The hero shows icon, action, one-line reason, confidence word,
 * Listen and Share; the full reason and fallback are one tap away. List items show the
 * action and open to the same details.
 */
export function AdviceCard(props: Props) {
  const { advisory, hero } = props;
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const action = pickText(advisory.action, lang);
  const reason = pickText(advisory.reason, lang);
  const Icon = CATEGORY_ICON[advisory.category];
  const validity = useValidity(advisory);
  const category = t(`categories.${advisory.category}`);
  const crop =
    advisory.crop === "livestock"
      ? null
      : t(`crops.${advisory.crop}`, { defaultValue: advisory.crop });

  if (hero) {
    return (
      <article className="advice-hero" aria-labelledby={`act-${advisory.id}`}>
        <p className="advice-meta">
          <Icon size={28} aria-hidden="true" />
          <span>{[category, crop, validity].filter(Boolean).join(" · ")}</span>
        </p>
        <h2 id={`act-${advisory.id}`} className="advice-action" lang={action.lang}>
          {action.text}
        </h2>
        <p className="advice-reason" lang={reason.lang}>
          {firstSentence(reason.text)}
        </p>
        <p className="advice-confidence">
          <ConfidenceLabel confidence={advisory.confidence} />
        </p>
        <div className="btn-row">
          <ListenButton advisory={advisory} />
          <ShareLink advisory={advisory} village={props.village} dataMode={props.dataMode} />
        </div>
        <details className="advice-more">
          <summary>{t("farmer.more")}</summary>
          <FullReason advisory={advisory} />
        </details>
      </article>
    );
  }

  return (
    <details className="advice-item">
      <summary>
        <Icon size={22} aria-hidden="true" className="advice-item-icon" />
        <span className="advice-item-text">
          <span lang={action.lang}>{action.text}</span>
          <span className="advice-item-meta">
            {[category, crop, validity, t(`confidence.${confidenceWord(advisory.confidence)}`)]
              .filter(Boolean)
              .join(" · ")}
          </span>
        </span>
      </summary>
      <div className="advice-item-body">
        <AdviceBody {...props} />
      </div>
    </details>
  );
}
