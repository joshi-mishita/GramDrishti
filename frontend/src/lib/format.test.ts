import { describe, expect, it } from "vitest";
import { addDays, formatDate, formatNumber, isIsoDate } from "./format";

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
