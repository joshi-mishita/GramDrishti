import { useEffect, useRef, useState } from "react";
import { CloudRain, CheckCircle2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import { useSendFeedback } from "../../api/hooks";
import { isApiError } from "../../api/errors";
import type { FeedbackRequest, Intensity } from "../../api/types";
import { formatDate } from "../../lib/format";
import { pickText } from "../../lib/text";
import { useAppStore } from "../../state/store";
import { queueFeedback } from "./outbox";

type Step = "ask" | "amount" | "done";
const AMOUNTS: Intensity[] = ["light", "moderate", "heavy"];

/**
 * "Did it rain today?" (Guide 7): Yes or No; after Yes, light, moderate or heavy. Posts to
 * /feedback. "Today" is the demo issue date, shown next to the question. Without a
 * connection the answer is kept on the phone and sent later (outbox.ts).
 */
export function FeedbackCard({ pid }: { pid: string }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const issueDate = useAppStore((s) => s.issueDate);
  const send = useSendFeedback();
  const [step, setStep] = useState<Step>("ask");
  const [result, setResult] = useState<{
    text: string;
    lang?: string;
    kind: "ok" | "info" | "error";
  }>();
  const stepsRef = useRef<HTMLDivElement>(null);
  const firstRender = useRef(true);

  // Each step replaces the buttons, including the one just pressed; without this a keyboard
  // user's focus falls to the page body. Move it to the new step's first control or message.
  useEffect(() => {
    if (firstRender.current) {
      firstRender.current = false;
      return;
    }
    stepsRef.current?.querySelector<HTMLElement>("[data-step-focus]")?.focus();
  }, [step]);

  if (!issueDate) return null;

  const submit = (reported_rain: boolean, intensity: Intensity) => {
    const body: FeedbackRequest = {
      panchayat_id: pid,
      date: issueDate,
      reported_rain,
      intensity,
      channel: "app",
    };
    send.mutate(body, {
      onSuccess: (res) => {
        const msg = pickText(res.message, lang);
        setResult({ text: msg.text, lang: msg.lang, kind: "ok" });
        setStep("done");
      },
      onError: (e) => {
        if (isApiError(e) && e.code === "read_only") {
          setResult({ text: t("feedback.readOnly"), kind: "info" });
        } else if (isApiError(e) && e.code === "network_error" && queueFeedback(body)) {
          setResult({ text: t("feedback.queued"), kind: "info" });
        } else {
          const detail = isApiError(e) && e.status ? ` (${e.message})` : "";
          setResult({ text: t("feedback.failed") + detail, kind: "error" });
        }
        setStep("done");
      },
    });
  };

  return (
    <section className="panel feedback" aria-labelledby="feedback-q">
      <h2 id="feedback-q" className="feedback-q">
        <CloudRain size={22} aria-hidden="true" />
        {t("feedback.questionDate", { date: formatDate(issueDate, lang, "day") })}
      </h2>
      <div ref={stepsRef}>
        {send.isPending ? (
          <p role="status">{t("feedback.sending")}</p>
        ) : step === "ask" ? (
          <div className="btn-row">
            <button
              type="button"
              className="btn btn-farmer"
              data-step-focus
              onClick={() => setStep("amount")}
            >
              {t("feedback.yes")}
            </button>
            <button type="button" className="btn btn-farmer" onClick={() => submit(false, "none")}>
              {t("feedback.no")}
            </button>
          </div>
        ) : step === "amount" ? (
          <fieldset className="feedback-amount">
            <legend>{t("feedback.howMuch")}</legend>
            <div className="btn-row">
              {AMOUNTS.map((a, i) => (
                <button
                  key={a}
                  type="button"
                  className="btn btn-farmer"
                  data-step-focus={i === 0 ? "" : undefined}
                  onClick={() => submit(true, a)}
                >
                  {t(`feedback.${a}`)}
                </button>
              ))}
            </div>
            <button type="button" className="btn-link" onClick={() => setStep("ask")}>
              {t("feedback.back")}
            </button>
          </fieldset>
        ) : (
          <div className="feedback-done">
            <p
              tabIndex={-1}
              data-step-focus
              role={result?.kind === "error" ? "alert" : "status"}
              lang={result?.lang}
              className={`feedback-result feedback-${result?.kind ?? "ok"}`}
            >
              {result?.kind === "ok" ? <CheckCircle2 size={20} aria-hidden="true" /> : null}
              {result?.text}
            </p>
            <button
              type="button"
              className="btn-link"
              onClick={() => {
                setStep("ask");
                setResult(undefined);
              }}
            >
              {t("feedback.again")}
            </button>
          </div>
        )}
      </div>
    </section>
  );
}
