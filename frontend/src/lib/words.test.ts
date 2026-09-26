import { describe, expect, it } from "vitest";
import { confidenceWord, formatPercent, probWord, toPercent } from "./words";

describe("probWord", () => {
  it("uses the documented bands", () => {
    expect(probWord(0)).toBe("very_unlikely");
    expect(probWord(0.09)).toBe("very_unlikely");
    expect(probWord(0.1)).toBe("unlikely");
    expect(probWord(0.29)).toBe("unlikely");
    expect(probWord(0.3)).toBe("possible");
    expect(probWord(0.59)).toBe("possible");
    expect(probWord(0.6)).toBe("likely");
    expect(probWord(0.71)).toBe("likely");
    expect(probWord(1)).toBe("likely");
  });

  it("decides on the rounded percent, so word and number agree", () => {
    // 0.596 is shown as 60%, so it must read "likely", not "possible".
    expect(formatPercent(0.596, "en")).toBe("60%");
    expect(probWord(0.596)).toBe("likely");
    expect(probWord(0.0949)).toBe("very_unlikely");
  });

  it("treats missing values as unknown", () => {
    expect(probWord(null)).toBe("unknown");
    expect(probWord(undefined)).toBe("unknown");
    expect(probWord(Number.NaN)).toBe("unknown");
  });
});

describe("formatPercent", () => {
  it("formats whole percents with Western digits in every language", () => {
    expect(formatPercent(0.71, "en")).toBe("71%");
    expect(formatPercent(0.71, "hi")).toBe("71%");
    expect(formatPercent(0.71, "pa")).toBe("71%");
  });

  it("never claims certainty at the ends", () => {
    expect(formatPercent(0, "en")).toBe("<1%");
    expect(formatPercent(0.004, "en")).toBe("<1%");
    expect(formatPercent(1, "en")).toBe(">99%");
    expect(formatPercent(0.996, "en")).toBe(">99%");
    expect(formatPercent(0.01, "en")).toBe("1%");
    expect(formatPercent(0.99, "en")).toBe("99%");
  });

  it("shows a dash for missing values and clamps out-of-range input", () => {
    expect(formatPercent(null, "en")).toBe("–");
    expect(formatPercent(Number.POSITIVE_INFINITY, "en")).toBe("–");
    expect(toPercent(1.2)).toBe(100);
    expect(toPercent(-0.1)).toBe(0);
  });
});

describe("confidenceWord", () => {
  it("maps the contract enum to Guide 2.7 words", () => {
    expect(confidenceWord("high")).toBe("likely");
    expect(confidenceWord("medium")).toBe("possible");
    expect(confidenceWord("low")).toBe("uncertain");
  });

  it("reads a missing value as uncertain", () => {
    expect(confidenceWord(null)).toBe("uncertain");
    expect(confidenceWord(undefined)).toBe("uncertain");
  });
});
