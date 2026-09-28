import { describe, expect, it } from "vitest";
import {
  bestIndexes,
  formatCount,
  formatFixed,
  formatPercent,
  formatSkill,
  parseStratum,
  readableNote,
  readSkill,
  rowDigits,
  segments,
  splitLossNote,
  splitNotes,
} from "./verify";

describe("bestIndexes", () => {
  it("picks the lowest error", () => {
    // Rain MAE on TEST: model, B0, B1, B2. B1 wins; the model loses and is not best.
    expect(bestIndexes([1.07045, 1.23993, 1.03107, 1.03153], "lower")).toEqual([2]);
  });

  it("picks the value nearest zero for bias, whatever its sign", () => {
    expect(bestIndexes([-0.121389, -1.10445, 0.5, -0.303694], "zero")).toEqual([0]);
  });

  it("lets equal values share the win (model and B1 bias are identical)", () => {
    expect(bestIndexes([0.0201088, 0.356873, 0.0201088, 0.0572351], "zero")).toEqual([0, 2]);
  });

  it("picks the highest for skill-like scores and nearest one for frequency bias", () => {
    expect(bestIndexes([0.141, 0.349, 0.371], "higher")).toEqual([2]);
    expect(bestIndexes([0.72, 2.84, 1.81], "one")).toEqual([0]);
    expect(bestIndexes([1.2, 0.85], "one")).toEqual([1]);
  });

  it("ignores nulls and needs two values to compare", () => {
    expect(bestIndexes([null, 2, 1], "lower")).toEqual([2]);
    expect(bestIndexes([null, 2, null], "lower")).toEqual([]);
    expect(bestIndexes([], "lower")).toEqual([]);
  });

  it("treats values within 1e-9 as equal but a real small difference as a difference", () => {
    expect(bestIndexes([1.0, 1.0 + 1e-12], "lower")).toEqual([0, 1]);
    expect(bestIndexes([1.0, 1.0 + 1e-6], "lower")).toEqual([0]);
  });
});

describe("rowDigits", () => {
  it("keeps the fixed decimals when they show every difference", () => {
    expect(rowDigits([1.07609, 1.15412, 1.1344, 1.13835], 2)).toBe(2);
  });

  it("adds a decimal when two different values would print the same", () => {
    // B1 1.03107 and B2 1.03153 are both "1.03" at 2 decimals.
    expect(rowDigits([1.07045, 1.23993, 1.03107, 1.03153], 2)).toBe(3);
  });

  it("does not add decimals for values that really are equal", () => {
    expect(rowDigits([0.0201088, 0.356873, 0.0201088], 2)).toBe(2);
  });

  it("stops at four decimals", () => {
    expect(rowDigits([1.000001, 1.000002], 2)).toBe(4);
  });

  it("ignores nulls", () => {
    expect(rowDigits([null, 1.5, null], 2)).toBe(2);
  });
});

describe("number formatting", () => {
  it("prints fixed decimals with trailing zeros", () => {
    expect(formatFixed(1.07, "en", 3)).toBe("1.070");
    expect(formatFixed(5.66805, "en", 2)).toBe("5.67");
    expect(formatFixed(-0.0234269, "en", 2)).toBe("-0.02");
    expect(formatFixed(null, "en", 2)).toBe("–");
    expect(formatFixed(Number.NaN, "en", 2)).toBe("–");
  });

  it("uses Western digits in Hindi and Punjabi", () => {
    expect(formatFixed(1.2345, "hi", 2)).toBe("1.23");
    expect(formatFixed(73800, "pa", 0)).toMatch(/^73,?800$/);
  });

  it("writes skill as a signed percent with one decimal", () => {
    expect(formatSkill(0.136683, "en")).toBe("+13.7%");
    expect(formatSkill(-0.0381941, "en")).toBe("-3.8%");
    expect(formatSkill(0, "en")).toBe("0.0%");
    // An interval end just below zero keeps its sign: rounding must not hide it.
    expect(formatSkill(-0.000365054, "en")).toBe("-0.04%");
    expect(formatSkill(0.0000004, "en")).toBe("+0.0000%");
    expect(formatSkill(null, "en")).toBe("–");
  });

  it("writes coverage and shares as a percent and counts with separators", () => {
    expect(formatPercent(0.934485, "en")).toBe("93.4%");
    expect(formatPercent(0.8, "en", 0)).toBe("80%");
    expect(formatCount(73800, "en")).toBe("73,800");
  });
});

describe("readSkill", () => {
  it("follows the job's rule: the whole interval must be on one side of zero", () => {
    expect(readSkill([0.0397179, 0.27946])).toBe("better");
    expect(readSkill([-0.120287, -0.000365054])).toBe("worse");
    expect(readSkill([-0.0807198, 0.00790451])).toBe("unclear");
    expect(readSkill(null)).toBe("unknown");
  });
});

describe("segments", () => {
  it("keeps the contract order and turns counts into shares of all decisions", () => {
    const s = segments({ correct: 6511, wasted_wait: 217, washed_off: 112 });
    expect(s.map((x) => x.outcome)).toEqual(["correct", "wasted_wait", "washed_off"]);
    expect(s.map((x) => x.count)).toEqual([6511, 217, 112]);
    expect(s.reduce((a, x) => a + x.share, 0)).toBeCloseTo(1, 12);
    expect(s[2]?.share).toBeCloseTo(112 / 6840, 12);
  });

  it("gives zero shares when there are no decisions", () => {
    expect(segments({ correct: 0, wasted_wait: 0, washed_off: 0 }).map((x) => x.share)).toEqual([
      0, 0, 0,
    ]);
  });
});

describe("parseStratum", () => {
  it("reads the API's strata", () => {
    expect(parseStratum("all")).toEqual({ kind: "all", value: "" });
    expect(parseStratum(null)).toEqual({ kind: "all", value: "" });
    expect(parseStratum("lead_day=3")).toEqual({ kind: "lead_day", value: "3" });
    expect(parseStratum("season=post_monsoon")).toEqual({ kind: "season", value: "post_monsoon" });
    expect(parseStratum("observed_rain>=1mm")).toEqual({ kind: "wet_days", value: "" });
    expect(parseStratum("drainage=poor")).toEqual({ kind: "other", value: "drainage=poor" });
  });
});

describe("splitNotes", () => {
  it("puts the job's loss notes apart and keeps every note", () => {
    const notes = [
      "Synthetic demo data: every number comes from the mock data generator.",
      "Does NOT beat B1 on rain MAE (temporal_holdout): overall: tie (-3.8%).",
      "Worse than or equal to B1 on rain RMSE (temporal_holdout): skill -4.3%.",
      "rain_ge_35mm: model yes/no CSI 0.141 is below B0 (0.349).",
      "rain_ge_35mm: Brier score no better than monthly climatology (skill -1.6%).",
      "B0 = raw block forecast.",
    ];
    const { losses, other } = splitNotes(notes);
    expect(losses).toHaveLength(4);
    expect(other).toEqual([notes[0], notes[5]]);
  });
});

describe("readableNote", () => {
  it("names job terms in plain words and keeps every number", () => {
    const raw =
      "Does NOT beat B0 on rh MAE (temporal_holdout): lead_day 1: tie (+5.1%, 95% CI -1.1% to +19.5%); rain_intensity heavy_ge_35mm: too_few_days (-0.7%, no interval).";
    expect(readableNote(raw)).toBe(
      "Does not beat B0 on humidity mean absolute error (held-out period): lead day 1: tie (+5.1%, 95% interval -1.1% to +19.5%); heavy rain days (35 mm or more): too few days (-0.7%, no interval).",
    );
  });

  it("reads thresholds, seasons and impact outcome names", () => {
    expect(readableNote("rain_ge_2_5mm: model yes/no CSI 0.5 is below B0 (0.6).")).toBe(
      "Rain 2.5 mm or more: model yes/no CSI 0.5 is below B0 (0.6).",
    );
    expect(readableNote("x (station): season post_monsoon: tie")).toBe(
      "X (station): post-monsoon season: tie",
    );
    expect(readableNote("wasted_wait = acted; block_baseline uses B0")).toBe(
      "Wasted wait = acted; block baseline uses B0",
    );
  });
});

describe("splitLossNote", () => {
  it("puts each stratum on its own line", () => {
    expect(
      splitLossNote(
        "Does not beat B1 on rain (held-out period): overall: tie (-3.8%); lead day 1: tie (-3.3%).",
      ),
    ).toEqual({
      head: "Does not beat B1 on rain (held-out period)",
      items: ["overall: tie (-3.8%)", "lead day 1: tie (-3.3%)"],
    });
  });

  it("lists a single stratum too", () => {
    expect(splitLossNote("Does not beat B1 on rain (station): overall: tie (-5.0%).")).toEqual({
      head: "Does not beat B1 on rain (station)",
      items: ["overall: tie (-5.0%)"],
    });
  });

  it("keeps a single-number note whole", () => {
    const n = "Worse than or equal to B1 on rain root mean square error (station): skill -15.5%.";
    expect(splitLossNote(n)).toEqual({ head: n, items: [] });
  });
});
