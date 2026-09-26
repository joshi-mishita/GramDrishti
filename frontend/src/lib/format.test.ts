import { describe, expect, it } from "vitest";
import {
  addDays,
  describeRange,
  formatDate,
  formatNumber,
  formatSigned,
  formatValue,
  isIsoDate,
} from "./format";

describe("dates", () => {
  it("validates ISO dates, including impossible days", () => {
    expect(isIsoDate("2024-09-09")).toBe(true);
    expect(isIsoDate("2024-02-30")).toBe(false);
    expect(isIsoDate("09-09-2024")).toBe(false);
  });

  it("adds days across month and year ends without time zone drift", () => {
    expect(addDays("2024-09-09", 1)).toBe("2024-09-10");
    expect(addDays("2024-12-31", 1)).toBe("2025-01-01");
    expect(addDays("2024-02-28", 1)).toBe("2024-02-29");
  });

  it("formats English as the guide shows: Tue 10 Sep", () => {
    expect(formatDate("2024-09-10", "en", "day")).toBe("Tue 10 Sep");
    expect(formatDate("2024-09-10", "en", "short")).toBe("Tue 10");
    expect(formatDate("2024-09-10", "hi", "short")).toBe("मंगल 10");
    expect(formatDate("2024-09-09", "en")).toBe("Mon 9 Sep 2024");
  });

  it("formats Hindi and Punjabi in their script with Western digits", () => {
    expect(formatDate("2024-09-10", "hi")).toBe("मंगल 10 सितंबर 2024");
    expect(formatDate("2024-09-10", "pa")).toBe("ਮੰਗਲ 10 ਸਤੰਬਰ 2024");
    expect(formatDate("2024-12-24", "pa", "day")).toBe("ਮੰਗਲ 24 ਦਸੰਬਰ");
  });

  it("does not depend on the browser's locale data (Chrome lacks Punjabi months)", () => {
    for (const lang of ["en", "hi", "pa"] as const) {
      for (let m = 1; m <= 12; m++) {
        const s = formatDate(`2024-${String(m).padStart(2, "0")}-15`, lang);
        expect(s, `${lang} month ${m}`).not.toMatch(/M\d\d|undefined/);
      }
    }
  });
});

describe("numbers", () => {
  it("shows a dash for missing values instead of NaN", () => {
    expect(formatNumber(null, "en")).toBe("–");
    expect(formatNumber(Number.NaN, "hi")).toBe("–");
  });

  it("keeps Western digits in every language", () => {
    expect(formatNumber(105.84, "en")).toBe("105.8");
    expect(formatNumber(105.84, "hi")).toBe("105.8");
    expect(formatNumber(105.84, "pa")).toBe("105.8");
  });
});

describe("values and ranges", () => {
  it("adds the unit, or a dash when there is no value", () => {
    expect(formatValue(9.84, "mm", "en")).toBe("9.8 mm");
    expect(formatValue(35.67, "°C", "hi")).toBe("35.7 °C");
    expect(formatValue(62.77, "%", "en", 0)).toBe("63 %");
    expect(formatValue(null, "mm", "en")).toBe("–");
    expect(formatValue(Number.NaN, "mm", "en")).toBe("–");
  });

  it("signs differences, with no sign on zero after rounding", () => {
    expect(formatSigned(0.88, "en")).toBe("+0.9");
    expect(formatSigned(-4.5, "en")).toBe("-4.5");
    expect(formatSigned(0.01, "en")).toBe("0");
    expect(formatSigned(null, "en")).toBe("–");
  });

  it("describes a p10..p90 band in plain parts", () => {
    expect(describeRange(2.04, 13.96, "en", 0)).toEqual({ kind: "between", lo: "2", hi: "14" });
    expect(describeRange(0, 0.75, "en")).toEqual({ kind: "between", lo: "0", hi: "0.8" });
    expect(describeRange(0, 0.02, "en")).toEqual({ kind: "about", value: "0" });
    expect(describeRange(null, 3, "en")).toEqual({ kind: "unknown" });
  });

  it("keeps Western digits in Hindi and Punjabi", () => {
    expect(formatValue(1234.5, "mm", "pa")).toMatch(/^1,?234\.5 mm$/);
  });
});
