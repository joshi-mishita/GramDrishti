import type { SegmentOption } from "../components/SegmentedControl";
import type { Lang } from "../api/types";

/** Each language is written in its own script so a reader finds theirs (Guide 8). */
export const LANG_OPTIONS: readonly SegmentOption<Lang>[] = [
  { value: "en", label: "English", lang: "en" },
  { value: "hi", label: "हिन्दी", lang: "hi" },
  { value: "pa", label: "ਪੰਜਾਬੀ", lang: "pa" },
];
