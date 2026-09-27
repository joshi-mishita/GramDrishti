/** Reads a design token from :root; MapLibre paint properties need literal colours. */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}
