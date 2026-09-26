import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

const css = readFileSync(resolve(__dirname, "tokens.css"), "utf8");

function token(name: string): string {
  const m = new RegExp(`--${name}:\\s*(#[0-9a-fA-F]{6})`).exec(css);
  if (!m?.[1]) throw new Error(`token --${name} not found`);
  return m[1];
}

function luminance(hex: string): number {
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  }) as [number, number, number];
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(a: string, b: string): number {
  const [hi, lo] = [luminance(a), luminance(b)].sort((x, y) => y - x) as [number, number];
  return (hi + 0.05) / (lo + 0.05);
}

describe("design tokens", () => {
  it("keeps the palette of Frontend Guide 2.3", () => {
    expect(token("ink").toLowerCase()).toBe("#18262b");
    expect(token("canvas").toLowerCase()).toBe("#eef1f0");
    expect(token("brand").toLowerCase()).toBe("#24594a");
    expect(token("sev-severe").toLowerCase()).toBe("#c62828");
  });

  // Guide 11.1: text contrast at least 4.5 to 1 on all surfaces.
  const pairs: [string, string][] = [
    ["ink", "surface"],
    ["ink", "canvas"],
    ["muted", "surface"],
    ["muted", "canvas"],
    ["brand", "surface"],
    ["brand", "brand-tint"],
    ["brand-ink", "brand"],
    ["brand-ink-soft", "brand"],
    ["brand-ink", "brand-strong"],
    ["ink", "ribbon-bg"],
    ["muted", "surface-hover"],
  ];
  for (const [fg, bg] of pairs) {
    it(`--${fg} on --${bg} reaches 4.5:1`, () => {
      expect(contrast(token(fg), token(bg))).toBeGreaterThanOrEqual(4.5);
    });
  }

  it("uses no purple or indigo hue", () => {
    for (const [hex] of css.matchAll(/#[0-9a-fA-F]{6}\b/g)) {
      const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16)) as [
        number,
        number,
        number,
      ];
      const purple = b > g + 30 && r > g + 10;
      expect(purple, hex).toBe(false);
    }
  });
});
