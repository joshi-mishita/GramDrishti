import type { Lang, LocalizedText } from "../api/types";

/**
 * Picks API text in the UI language. Falls back to English when the translation is
 * missing, and reports which language was used so the element gets the right lang.
 */
export function pickText(text: LocalizedText, lang: Lang): { text: string; lang: Lang } {
  const value = text[lang];
  if (value) return { text: value, lang };
  return { text: text.en, lang: "en" };
}
