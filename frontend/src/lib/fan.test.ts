import { describe, expect, it } from "vitest";
import type { ForecastDay, ObservedDay, Quantiles } from "../api/types";
import { fanDomain, hasAnyValue, hasObserved, shapeFanRows } from "./fan";

const q = (p10: number | null, p50: number | null, p90: number | null, block: number | null) =>
  ({ p10, p50, p90, block }) satisfies Quantiles;

function day(date: string, lead: number, rain: Quantiles, tmax = q(30, 31, 32, 31)): ForecastDay {
  return {
    date,
    lead_day: lead,
    rain,
    tmax,
    tmin: q(20, 21, 22, 21),
    rh: q(60, 70, 80, 70),
    wind: q(2, 4, 6, 4),
    prob: { rain_ge_1mm: 0.5, rain_ge_2_5mm: 0.4, rain_ge_10mm: 0.2, rain_ge_35mm: 0.05 },
    derived: { et0_mm: 4, soil_moisture_frac: 0.5, thi: 70, waterlog_risk: "low" },
  };
}

const obs = (date: string, rain: number | null, tmax: number | null = null): ObservedDay => ({
  date,
  rain,
  tmax,
  tmin: null,
  rh: null,
  wind: null,
});

describe("shapeFanRows", () => {
  it("stacks the band on p10 and matches observations by date", () => {
    const rows = shapeFanRows(
      [day("2024-09-11", 2, q(0, 2, 9, 3)), day("2024-09-10", 1, q(1, 10, 31, 12.4))],
      "rain",
      [obs("2024-09-10", 27.5), obs("2024-09-12", 5)],
    );
    expect(rows.map((r) => r.date)).toEqual(["2024-09-10", "2024-09-11"]);
    expect(rows[0]).toEqual({
      date: "2024-09-10",
      p10: 1,
      p50: 10,
      p90: 31,
      base: 1,
      band: 30,
      block: 12.4,
      observed: 27.5,
    });
    expect(rows[1]?.observed).toBeNull();
  });

  it("keeps nulls as gaps instead of zeros", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(null, 3, 9, null))], "rain", [
      obs("2024-09-10", null),
    ]);
    expect(rows[0]).toMatchObject({
      p10: null,
      base: null,
      band: null,
      block: null,
      observed: null,
    });
    expect(rows[0]?.p50).toBe(3);
  });

  it("draws a reversed band with zero height", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(5, 4, 3, 4))], "rain");
    expect(rows[0]?.band).toBe(0);
  });

  it("reads the chosen variable, and a rain-only station gives no temperature points", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(0, 1, 2, 1))], "tmax", [
      obs("2024-09-10", 12),
    ]);
    expect(rows[0]?.p50).toBe(31);
    expect(hasObserved(rows)).toBe(false);
  });
});

describe("hasAnyValue", () => {
  it("is false when every number is missing", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(null, null, null, null))], "rain");
    expect(hasAnyValue(rows)).toBe(false);
  });
});

describe("fanDomain", () => {
  it("covers band, block and observations with round ends", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(0, 103.8, 154.3, 105.8))], "rain", [
      obs("2024-09-10", 127.8),
    ]);
    expect(fanDomain(rows, "rain")).toEqual([0, 200]);
  });

  it("never goes below zero for rain and gives a flat dry series some height", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(0, 0, 0, 0))], "rain");
    const d = fanDomain(rows, "rain");
    expect(d?.[0]).toBe(0);
    expect(d?.[1]).toBeGreaterThan(0);
  });

  it("allows negative temperatures and caps humidity at 100", () => {
    const cold = shapeFanRows(
      [day("2024-01-13", 1, q(0, 0, 0, 0), q(-1.2, 0.5, 2.1, 0.4))],
      "tmax",
    );
    expect(fanDomain(cold, "tmax")?.[0]).toBeLessThan(0);
    const humid = shapeFanRows([day("2024-09-10", 1, q(0, 0, 0, 0))], "rh").map((r) => ({
      ...r,
      p90: 99,
    }));
    expect(fanDomain(humid, "rh")?.[1]).toBe(100);
  });

  it("is null when there is nothing to draw", () => {
    const rows = shapeFanRows([day("2024-09-10", 1, q(null, null, null, null))], "rain");
    expect(fanDomain(rows, "rain")).toBeNull();
  });
});
