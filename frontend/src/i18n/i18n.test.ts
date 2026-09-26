import { describe, expect, it } from "vitest";
import en from "./en.json";
import hi from "./hi.json";
import pa from "./pa.json";

type Tree = { [key: string]: string | Tree };

function flatten(tree: Tree, prefix = ""): Map<string, string> {
  const out = new Map<string, string>();
  for (const [k, v] of Object.entries(tree)) {
    const key = prefix ? `${prefix}.${k}` : k;
    if (typeof v === "string") out.set(key, v);
    else for (const [kk, vv] of flatten(v, key)) out.set(kk, vv);
  }
  return out;
}

const placeholders = (s: string) => [...s.matchAll(/\{\{(\w+)\}\}/g)].map((m) => m[1]).sort();

const EN = flatten(en);
const OTHERS = { hi: flatten(hi), pa: flatten(pa) };

describe("i18n key parity", () => {
  for (const [lang, strings] of Object.entries(OTHERS)) {
    it(`${lang}.json has every key in en.json`, () => {
      const missing = [...EN.keys()].filter((k) => !strings.has(k));
      expect(missing, `missing in ${lang}.json`).toEqual([]);
    });

    it(`${lang}.json has no key that en.json lacks`, () => {
      const extra = [...strings.keys()].filter((k) => !EN.has(k));
      expect(extra, `extra in ${lang}.json`).toEqual([]);
    });

    it(`${lang}.json keeps the same {{placeholders}} and no empty strings`, () => {
      for (const [key, value] of EN) {
        const other = strings.get(key) ?? "";
        expect(other.trim(), `${lang}:${key} is empty`).not.toBe("");
        expect(placeholders(other), `${lang}:${key}`).toEqual(placeholders(value));
      }
    });
  }
});

describe("i18n writing rules", () => {
  it("English strings are sentence case, not all caps", () => {
    for (const [key, value] of EN) {
      const words = value.replace(/\{\{\w+\}\}/g, "").match(/[A-Za-z]{4,}/g) ?? [];
      const shouting = words.filter((w) => w === w.toUpperCase() && !["GramDrishti"].includes(w));
      expect(shouting, key).toEqual([]);
    }
  });

  it("the ribbon wording matches the guide exactly", () => {
    expect(EN.get("shell.ribbon")).toBe("Synthetic demo data. Not real weather.");
  });
});
