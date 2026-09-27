import { Square, Volume2 } from "lucide-react";
import { useTranslation } from "react-i18next";
import type { Advisory } from "../../api/types";
import { useAppStore } from "../../state/store";
import { useAudioStore } from "./speech";

/**
 * Listen / Stop for one advisory. Shows the playing state in words, and explains when the
 * phone has no voice for the language instead of failing silently (Guide 7).
 */
export function ListenButton({ advisory }: { advisory: Advisory }) {
  const { t } = useTranslation();
  const lang = useAppStore((s) => s.lang);
  const { playingId, state, problem, problemLang, problemId, play, stop } = useAudioStore();
  const active = playingId === advisory.id;
  const busy = active && state !== "idle";

  let message: string | null = null;
  if (problemId === advisory.id && problem) {
    message =
      problem === "no_voice"
        ? t("listen.noVoice", { language: t(`langNames.${problemLang ?? lang}`) })
        : problem === "no_speech"
          ? t("listen.noSpeech")
          : t("listen.failed");
  }

  return (
    <div className="listen">
      <button
        type="button"
        className="btn btn-farmer"
        aria-pressed={busy}
        onClick={() => (busy ? stop() : void play(advisory, lang))}
      >
        {busy ? <Square size={20} aria-hidden="true" /> : <Volume2 size={20} aria-hidden="true" />}
        {busy ? t("listen.stop") : t("listen.listen")}
      </button>
      <p className="listen-status" role="status">
        {busy ? (state === "loading" ? t("listen.loading") : t("listen.playing")) : message}
      </p>
    </div>
  );
}
