/**
 * Global UI state (Frontend Guide 5). Server data does not belong here; it lives in the
 * TanStack Query cache. issueDate, variable and selectedPid are mirrored into the URL by
 * useUrlSync so a link reproduces the screen.
 */
import { create } from "zustand";
import { LANGS, type Lang, type Var } from "../api/types";

export type ViewMode = "block" | "panchayat" | "delta";
export type Role = "officer" | "farmer";

export interface AppState {
  issueDate: string | null;
  leadDay: number;
  variable: Var;
  viewMode: ViewMode;
  selectedPid: string | null;
  lang: Lang;
  role: Role;
  setIssueDate: (d: string | null) => void;
  setLeadDay: (n: number) => void;
  setVariable: (v: Var) => void;
  setViewMode: (m: ViewMode) => void;
  setSelectedPid: (pid: string | null) => void;
  setLang: (lang: Lang) => void;
  setRole: (role: Role) => void;
}

export const LANG_STORAGE_KEY = "gramdrishti.lang";

/** Reads the saved language; storage can be missing or blocked, so it never throws. */
export function readStoredLang(): Lang {
  try {
    const v = localStorage.getItem(LANG_STORAGE_KEY);
    return LANGS.includes(v as Lang) ? (v as Lang) : "en";
  } catch {
    return "en";
  }
}

function storeLang(lang: Lang): void {
  try {
    localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // Storage blocked: the choice lasts for this page only.
  }
}

export const useAppStore = create<AppState>()((set) => ({
  issueDate: null,
  leadDay: 1,
  variable: "rain",
  viewMode: "panchayat",
  selectedPid: null,
  lang: readStoredLang(),
  role: "officer",
  setIssueDate: (issueDate) => set({ issueDate }),
  setLeadDay: (leadDay) => set({ leadDay }),
  setVariable: (variable) => set({ variable }),
  setViewMode: (viewMode) => set({ viewMode }),
  setSelectedPid: (selectedPid) => set({ selectedPid }),
  setLang: (lang) => {
    storeLang(lang);
    set({ lang });
  },
  setRole: (role) => set({ role }),
}));
