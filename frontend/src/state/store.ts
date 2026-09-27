/**
 * Global UI state (Frontend Guide 5). Server data does not belong here; it lives in the
 * TanStack Query cache. issueDate, variable, selectedPid, leadDay, viewMode and riskType are mirrored into the URL by
 * useUrlSync so a link reproduces the screen.
 */
import { create } from "zustand";
import { LANGS, type Lang, type RiskType, type Var } from "../api/types";
import { DEMO_FARMER_ID, DEMO_FARMER_IDS } from "../lib/config";

export type ViewMode = "block" | "panchayat" | "delta";
export type Role = "officer" | "farmer";

export interface AppState {
  issueDate: string | null;
  leadDay: number;
  variable: Var;
  viewMode: ViewMode;
  selectedPid: string | null;
  /** Hazard painted on the map instead of the variable; null paints the forecast. */
  riskType: RiskType | null;
  lang: Lang;
  role: Role;
  /** Demo farmer shown in the farmer app (developer control, no login). */
  farmerId: string;
  setIssueDate: (d: string | null) => void;
  setLeadDay: (n: number) => void;
  setVariable: (v: Var) => void;
  setViewMode: (m: ViewMode) => void;
  setSelectedPid: (pid: string | null) => void;
  setRiskType: (type: RiskType | null) => void;
  setLang: (lang: Lang) => void;
  setRole: (role: Role) => void;
  setFarmerId: (id: string) => void;
}

export const LANG_STORAGE_KEY = "gramdrishti.lang";
export const FARMER_STORAGE_KEY = "gramdrishti.farmer";

/** Reads the saved language; storage can be missing or blocked, so it never throws. */
export function readStoredLang(): Lang {
  try {
    const v = localStorage.getItem(LANG_STORAGE_KEY);
    return LANGS.includes(v as Lang) ? (v as Lang) : "en";
  } catch {
    return "en";
  }
}

/** Reads the saved demo farmer; falls back to the default profile. */
export function readStoredFarmer(): string {
  try {
    const v = localStorage.getItem(FARMER_STORAGE_KEY);
    return (DEMO_FARMER_IDS as readonly string[]).includes(v ?? "")
      ? (v as string)
      : DEMO_FARMER_ID;
  } catch {
    return DEMO_FARMER_ID;
  }
}

function store(key: string, value: string): void {
  try {
    localStorage.setItem(key, value);
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
  riskType: null,
  lang: readStoredLang(),
  role: "officer",
  farmerId: readStoredFarmer(),
  setIssueDate: (issueDate) => set({ issueDate }),
  setLeadDay: (leadDay) => set({ leadDay }),
  setVariable: (variable) => set({ variable }),
  setViewMode: (viewMode) => set({ viewMode }),
  setSelectedPid: (selectedPid) => set({ selectedPid }),
  setRiskType: (riskType) => set({ riskType }),
  setLang: (lang) => {
    store(LANG_STORAGE_KEY, lang);
    set({ lang });
  },
  setRole: (role) => set({ role }),
  setFarmerId: (farmerId) => {
    store(FARMER_STORAGE_KEY, farmerId);
    set({ farmerId });
  },
}));
