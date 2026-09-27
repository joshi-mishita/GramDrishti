/**
 * Listen (Frontend Guide 7): play the API's audio for an advisory, or fall back to the
 * phone's own speech (speechSynthesis) when the file is missing (404), the app runs on
 * demo files, or the phone is offline. Only one advisory plays at a time.
 */
import { create } from "zustand";
import { isReal } from "../../api/client";
import type { Advisory, Lang } from "../../api/types";
import { config } from "../../lib/config";
import { pickText } from "../../lib/text";

/** BCP 47 tags asked of speechSynthesis (Guide 7). */
export const SPEECH_TAG: Record<Lang, string> = { en: "en-IN", hi: "hi-IN", pa: "pa-IN" };

const norm = (tag: string) => tag.replace("_", "-").toLowerCase();

/**
 * The best installed voice for a language: the exact Indian tag first, then any voice of
 * that language. Never a voice of another language: English voices cannot read Hindi or
 * Punjabi script, so the caller explains instead.
 */
export function pickVoice(
  voices: readonly SpeechSynthesisVoice[],
  lang: Lang,
): SpeechSynthesisVoice | null {
  const tag = norm(SPEECH_TAG[lang]);
  return (
    voices.find((v) => norm(v.lang) === tag) ??
    voices.find((v) => norm(v.lang).split("-")[0] === lang) ??
    null
  );
}

/** What is read aloud: action, reason and the fallback, in one language. */
export function spokenText(a: Advisory, lang: Lang): { text: string; lang: Lang } {
  const action = pickText(a.action, lang);
  // Keep all three parts in the same language, or the voice would read the wrong script.
  const parts = [a.action, a.reason, a.fallback].map((t) => t[action.lang] ?? t.en);
  return { text: parts.filter(Boolean).join(" "), lang: action.lang };
}

export type PlayState = "idle" | "loading" | "playing";
/** Why nothing is playing, for the message under the button. */
export type PlayProblem = "no_speech" | "no_voice" | "failed" | null;

interface AudioState {
  playingId: string | null;
  state: PlayState;
  problem: PlayProblem;
  /** Language the problem is about (no voice for Punjabi, and so on). */
  problemLang: Lang | null;
  problemId: string | null;
  play: (a: Advisory, lang: Lang) => Promise<void>;
  stop: () => void;
}

let current: HTMLAudioElement | null = null;
let run = 0;

function speechAvailable(): boolean {
  return typeof window !== "undefined" && "speechSynthesis" in window;
}

/** Voices load late on some phones; wait for them up to one second. */
async function loadVoices(): Promise<SpeechSynthesisVoice[]> {
  const synth = window.speechSynthesis;
  const now = synth.getVoices();
  if (now.length) return now;
  return new Promise((resolve) => {
    const done = () => {
      synth.removeEventListener("voiceschanged", done);
      resolve(synth.getVoices());
    };
    synth.addEventListener("voiceschanged", done);
    setTimeout(done, 1000);
  });
}

/** The server's MP3 as an object URL, or null when it is missing or unreachable. */
async function fetchAudio(a: Advisory, lang: Lang): Promise<string | null> {
  const path = a.audio?.[lang];
  if (!path || !isReal("audio") || !navigator.onLine) return null;
  const url = config.apiBase + path.replace(/^\/api\/v1/, "");
  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return URL.createObjectURL(await res.blob());
  } catch {
    return null;
  }
}

export const useAudioStore = create<AudioState>()((set, get) => {
  const finish = (id: number) => {
    if (id === run) set({ playingId: null, state: "idle" });
  };
  const fail = (a: Advisory, problem: PlayProblem, lang: Lang | null) =>
    set({ playingId: null, state: "idle", problem, problemLang: lang, problemId: a.id });

  return {
    playingId: null,
    state: "idle",
    problem: null,
    problemLang: null,
    problemId: null,

    stop: () => {
      run += 1;
      current?.pause();
      current = null;
      if (speechAvailable()) window.speechSynthesis.cancel();
      set({ playingId: null, state: "idle" });
    },

    play: async (a, lang) => {
      get().stop();
      const id = ++run;
      set({ playingId: a.id, state: "loading", problem: null, problemLang: null, problemId: null });

      const spoken = spokenText(a, lang);
      const src = await fetchAudio(a, spoken.lang);
      if (id !== run) return;
      if (src) {
        const el = new Audio(src);
        current = el;
        el.onended = () => finish(id);
        el.onerror = () => finish(id);
        try {
          await el.play();
          if (id === run) set({ state: "playing" });
          return;
        } catch {
          // Autoplay blocked or bad file: try the phone's speech below.
        }
      }

      if (!speechAvailable()) return fail(a, "no_speech", spoken.lang);
      const voice = pickVoice(await loadVoices(), spoken.lang);
      if (id !== run) return;
      if (!voice) return fail(a, "no_voice", spoken.lang);
      const u = new SpeechSynthesisUtterance(spoken.text);
      u.lang = SPEECH_TAG[spoken.lang];
      u.voice = voice;
      u.onend = () => finish(id);
      u.onerror = () => (id === run ? fail(a, "failed", spoken.lang) : undefined);
      window.speechSynthesis.speak(u);
      set({ state: "playing" });
    },
  };
});
