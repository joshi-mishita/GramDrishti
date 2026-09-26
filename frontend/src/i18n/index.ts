import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import type { Lang } from "../api/types";
import en from "./en.json";
import hi from "./hi.json";
import pa from "./pa.json";

/**
 * UI strings only. Advisory text arrives translated from the API; never translate it here.
 * hi.json and pa.json are drafts that need native review (see src/i18n/README.md).
 */
export const resources = {
  en: { translation: en },
  hi: { translation: hi },
  pa: { translation: pa },
} as const;

export function initI18n(lang: Lang): typeof i18n {
  void i18n.use(initReactI18next).init({
    resources,
    lng: lang,
    fallbackLng: "en",
    interpolation: { escapeValue: false },
    returnNull: false,
  });
  document.documentElement.lang = lang;
  return i18n;
}

/** Switches UI language and the document lang, which switches fonts and line height. */
export function applyLang(lang: Lang): void {
  void i18n.changeLanguage(lang);
  document.documentElement.lang = lang;
}
