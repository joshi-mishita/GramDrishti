import type { TFunction } from "i18next";
import { describe, expect, it } from "vitest";
import type { ForecastDay } from "../../api/types";
import { rainText } from "./forecastText";

// Echoes the key and its values, so the test checks which sentence is chosen and what fills it.
const t = ((key: string, opts?: Record<string, string>) =>
  opts ? `${key} ${JSON.stringify(opts)}` : key) as unknown as TFunction;

function day(p50: number | null, p90: number | null, prob1mm: number): ForecastDay {
  // Only the fields rainText reads; the rest of the day does not matter here.
  return { rain: { p10: 0, p50, p90 }, prob: { rain_ge_1mm: prob1mm } } as unknown as ForecastDay;
}

describe("rainText", () => {
  it("leads with the most likely amount and says how high it could go", () => {
    expect(rainText(day(103.84, 156.24, 0.91), "en", t)).toBe(
      'farmer.rainRange {"word":"farmer.rainWord.likely","mid":"104","hi":"156"}',
    );
  });

  it("says only the chance on a dry day, not '0 mm'", () => {
    expect(rainText(day(0, 0.2, 0.01), "en", t)).toBe(
      'farmer.rainNone {"word":"farmer.rainWord.very_unlikely"}',
    );
  });

  it("gives the upper end when the middle amount is 0 mm", () => {
    expect(rainText(day(0.3, 12, 0.35), "en", t)).toBe(
      'farmer.rainUpTo {"word":"farmer.rainWord.possible","hi":"12"}',
    );
  });

  it("says 'about' when the middle and upper amounts round the same", () => {
    expect(rainText(day(4.6, 5.2, 0.7), "en", t)).toBe(
      'farmer.rainAbout {"word":"farmer.rainWord.likely","value":"5"}',
    );
  });

  it("falls back to the word when amounts are missing", () => {
    expect(rainText(day(null, null, 0.5), "en", t)).toBe(
      'farmer.rainNone {"word":"farmer.rainWord.possible"}',
    );
  });
});
