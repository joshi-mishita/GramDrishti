import { useSyncExternalStore } from "react";

/**
 * True while the media query matches. Without `matchMedia` (jsdom, very old browsers)
 * it returns `fallback`, so tests and old browsers get the desktop layout.
 */
export function useMediaQuery(query: string, fallback = true): boolean {
  return useSyncExternalStore(
    (onChange) => {
      if (typeof window === "undefined" || !window.matchMedia) return () => undefined;
      const mql = window.matchMedia(query);
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    () =>
      typeof window === "undefined" || !window.matchMedia
        ? fallback
        : window.matchMedia(query).matches,
    () => fallback,
  );
}
