import { describe, expect, it } from "vitest";
import type { CoverageItem, RegionItem } from "../../api/types";
import { binEnds, chartItems, diffVsB0, reliabilityDots, tableItems } from "./verifyData";

const cov = (v: CoverageItem["var"], stratum: string, empirical = 0.8): CoverageItem => ({
  var: v,
  unit: "mm",
  nominal: 0.8,
  empirical,
  mean_width: 1,
  n: 10,
  stratum,
});

describe("reliabilityDots", () => {
  it("places dots at the mean forecast chance and skips bins with no observed frequency", () => {
    const dots = reliabilityDots([
      { forecast_prob: 0.05, observed_freq: 0.01, n: 10000, mean_forecast_prob: 0.007 },
      { forecast_prob: 0.15, observed_freq: 0.33, n: 100, mean_forecast_prob: null },
      { forecast_prob: 0.25, observed_freq: null, n: 0 },
    ]);
    expect(dots.map((d) => d.x)).toEqual([0.007, 0.15]);
    expect(dots.map((d) => d.y)).toEqual([0.01, 0.33]);
  });

  it("grows the radius with the square root of the count", () => {
    const [big, small] = reliabilityDots([
      { forecast_prob: 0.05, observed_freq: 0.1, n: 10000 },
      { forecast_prob: 0.15, observed_freq: 0.1, n: 100 },
    ]);
    expect(big?.r).toBe(14);
    expect(small?.r).toBeCloseTo(4 + 10 * 0.1, 10);
  });
});

describe("binEnds", () => {
  it("returns the ends of a 10 % bin, clamped to 0..1", () => {
    expect(binEnds(0.15)).toEqual([expect.closeTo(0.1, 10), expect.closeTo(0.2, 10)]);
    expect(binEnds(0.95)[1]).toBe(1);
    expect(binEnds(0.05)[0]).toBe(0);
  });
});

describe("coverage rows", () => {
  const items = [
    cov("rain", "all"),
    cov("rain", "lead_day=1"),
    cov("rain", "season=winter"),
    cov("tmax", "all"),
    cov("rain", "observed_rain>=1mm", 0.509),
  ];

  it("charts every variable over all days, with rain on wet days right after rain", () => {
    expect(chartItems(items).map((i) => `${i.var}:${i.stratum}`)).toEqual([
      "rain:all",
      "rain:observed_rain>=1mm",
      "tmax:all",
    ]);
  });

  it("lists the chosen strata group in the table", () => {
    expect(tableItems(items, "lead_day").map((i) => i.stratum)).toEqual(["lead_day=1"]);
    expect(tableItems(items, "season").map((i) => i.stratum)).toEqual(["season=winter"]);
    expect(tableItems(items, "all")).toHaveLength(3);
  });
});

describe("diffVsB0", () => {
  const item: RegionItem = {
    region_type: "block",
    region_id: "MB01",
    var: "rain",
    metric: "MAE",
    unit: "mm",
    model: 0.940999,
    b0: 1.03265,
    n: 10660,
  };

  it("is model minus B0, null when either is missing", () => {
    expect(diffVsB0(item)).toBeCloseTo(-0.091651, 9);
    expect(diffVsB0({ ...item, b0: null })).toBeNull();
  });
});
