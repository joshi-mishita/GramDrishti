import { describe, expect, it } from "vitest";
import type { EventChange, VarChange } from "../api/types";
import { isPreviousDay, materialChanges, summariseEventChanges } from "./changes";

const ev = (
  valid_date: string,
  event: EventChange["event"],
  previous_prob: number | null,
  current_prob: number | null,
): EventChange => ({ valid_date, event, previous_prob, current_prob });

describe("summariseEventChanges", () => {
  it("orders by date, then from light to heavy rain", () => {
    const lines = summariseEventChanges([
      ev("2024-09-13", "rain_ge_1mm", 0.04, 0.54),
      ev("2024-09-10", "rain_ge_35mm", 0.48, 0.64),
    ]);
    expect(lines.map((l) => [l.date, l.event, l.before, l.after])).toEqual([
      ["2024-09-10", "rain_ge_35mm", "possible", "likely"],
      ["2024-09-13", "rain_ge_1mm", "very_unlikely", "possible"],
    ]);
  });

  it("merges heavier events that tell the same story on the same day", () => {
    // Real example (MP0305, 2024-09-09): three thresholds all jump to 54 %.
    const lines = summariseEventChanges([
      ev("2024-09-13", "rain_ge_10mm", 0.01, 0.54),
      ev("2024-09-13", "rain_ge_2_5mm", 0.02, 0.54),
      ev("2024-09-13", "rain_ge_1mm", 0.04, 0.54),
    ]);
    expect(lines).toHaveLength(1);
    expect(lines[0]?.event).toBe("rain_ge_1mm");
  });

  it("keeps a heavier event when its words differ", () => {
    const lines = summariseEventChanges([
      ev("2024-09-10", "rain_ge_1mm", 0.2, 0.9),
      ev("2024-09-10", "rain_ge_35mm", 0.02, 0.4),
    ]);
    expect(lines.map((l) => l.event)).toEqual(["rain_ge_1mm", "rain_ge_35mm"]);
  });

  it("handles a missing probability", () => {
    const lines = summariseEventChanges([ev("2024-09-10", "rain_ge_1mm", null, 0.7)]);
    expect(lines[0]).toMatchObject({ before: "unknown", after: "likely", previousProb: null });
  });

  it("returns nothing for no changes", () => {
    expect(summariseEventChanges([])).toEqual([]);
  });
});

describe("materialChanges", () => {
  it("keeps only material changes, in date order", () => {
    const c = (valid_date: string, material: boolean): VarChange => ({
      valid_date,
      var: "tmax",
      previous_p50: 30,
      current_p50: 32,
      delta: 2,
      material,
    });
    expect(
      materialChanges([c("2024-09-12", true), c("2024-09-10", false), c("2024-09-11", true)]).map(
        (x) => x.valid_date,
      ),
    ).toEqual(["2024-09-11", "2024-09-12"]);
  });
});

describe("isPreviousDay", () => {
  it("says yesterday only for the day before, across month ends", () => {
    expect(isPreviousDay("2024-09-09", "2024-09-08")).toBe(true);
    expect(isPreviousDay("2024-08-01", "2024-07-31")).toBe(true);
    expect(isPreviousDay("2024-09-09", "2024-09-06")).toBe(false);
    expect(isPreviousDay("2024-09-09", null)).toBe(false);
  });
});
