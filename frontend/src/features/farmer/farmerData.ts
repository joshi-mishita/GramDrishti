/** Pure helpers for the farmer app (Frontend Guide 7). */
import type { LucideIcon } from "lucide-react";
import {
  Ban,
  Bug,
  CircleCheck,
  CloudRain,
  Droplets,
  Leaf,
  PawPrint,
  Snowflake,
  SprayCan,
  Sprout,
  Sun,
  Thermometer,
  TriangleAlert,
  Waves,
  Wheat,
} from "lucide-react";
import type { Advisory, Category, Level, SprayRating } from "../../api/types";

/** One icon per advisory category; the category word is always shown next to it. */
export const CATEGORY_ICON: Record<Category, LucideIcon> = {
  sowing: Sprout,
  irrigation: Droplets,
  spray: SprayCan,
  fertilizer: Leaf,
  harvest: Wheat,
  heat_stress: Thermometer,
  frost: Snowflake,
  waterlogging: Waves,
  dry_spell: Sun,
  pest_disease: Bug,
  livestock: PawPrint,
};

/** Spray suitability: icon plus word, never colour alone. */
export const SPRAY_ICON: Record<SprayRating, LucideIcon> = {
  good: CircleCheck,
  caution: TriangleAlert,
  avoid: Ban,
};

export const RAIN_ICON = CloudRain;

const LEVEL_RANK: Record<Level, number> = { severe: 0, high: 1, moderate: 2, low: 3 };

/**
 * Advisories a farmer or a bulletin may see: approved or edited only, most urgent first,
 * then earliest valid day, then id (the API's farmer order, D095).
 */
export function publishedInOrder(items: readonly Advisory[]): Advisory[] {
  return items
    .filter((a) => a.status === "approved" || a.status === "edited")
    .sort(
      (a, b) =>
        LEVEL_RANK[a.priority] - LEVEL_RANK[b.priority] ||
        a.valid_from.localeCompare(b.valid_from) ||
        a.id.localeCompare(b.id),
    );
}

/**
 * The first sentence of an advisory reason, for the one-line reason on Today. Sentences
 * end with ". " in English and with the danda "।" in Hindi and Punjabi. Returns the
 * whole text when there is only one sentence.
 */
export function firstSentence(text: string): string {
  const m = /^(.+?[.।!?])(\s|$)/u.exec(text.trim());
  return (m?.[1] ?? text).trim();
}

/** Builds the https://wa.me/?text= link. No phone number: the farmer picks the chat. */
export function whatsappUrl(text: string): string {
  return `https://wa.me/?text=${encodeURIComponent(text)}`;
}

export interface ShareParts {
  action: string;
  reason: string;
  /** "GramDrishti, Synthetic Panchayat MP0307, Mon 9 Sep 2024" */
  source: string;
  /** The mock notice, when the data are synthetic. */
  notice: string | null;
}

/** The shared message: action, reason, where it came from, and the mock notice. */
export function shareText({ action, reason, source, notice }: ShareParts): string {
  return [action, reason, `- ${source}`, notice].filter(Boolean).join("\n");
}
