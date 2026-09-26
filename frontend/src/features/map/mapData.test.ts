import { describe, expect, it } from "vitest";
import type { ForecastMap, PanchayatCollection, PanchayatMapValue } from "../../api/types";
import { valueRamp } from "../../lib/ramps";
import {
  boundsOf,
  isFlatWithinBlocks,
  legendTicks,
  rampForMode,
  tableRows,
  valueForMode,
  valuesForMode,
} from "./mapData";

const row = (
  pid: string,
  block: string,
  p50: number | null,
  blockValue: number | null,
): PanchayatMapValue => ({
  panchayat_id: pid,
  block_id: block,
  p10: p50 === null ? null : p50 - 1,
  p50,
  p90: p50 === null ? null : p50 + 1,
  block_value: blockValue,
  delta: p50 === null || blockValue === null ? null : p50 - blockValue,
  prob_event: null,
  event: null,
});

const forecast = (v: ForecastMap["var"], rows: PanchayatMapValue[]): ForecastMap => ({
  issue_date: "2024-09-09",
  valid_date: "2024-09-10",
  lead_day: 1,
  var: v,
  unit: "C",
  data_mode: "mock",
  provenance: "provisional",
  block_layer: [],
  panchayat_layer: rows,
});

describe("view modes", () => {
  const r = row("P1", "B1", 30, 32);

  it("paints block value, p50 or the difference", () => {
    expect(valueForMode(r, "block")).toBe(32);
    expect(valueForMode(r, "panchayat")).toBe(30);
    expect(valueForMode(r, "delta")).toBe(-2);
  });

  it("maps every Panchayat, keeping missing values as null", () => {
    const m = valuesForMode([r, row("P2", "B1", null, null)], "panchayat");
    expect([...m]).toEqual([
      ["P1", 30],
      ["P2", null],
    ]);
  });

  it("shares one ramp between block and Panchayat views", () => {
    const f = forecast("tmax", [row("P1", "B1", 26.6, 36.1)]);
    expect(rampForMode(f, "block")).toEqual(rampForMode(f, "panchayat"));
    expect(rampForMode(f, "block").stops[0]?.value).toBe(24);
    expect(rampForMode(f, "delta").kind).toBe("diverging");
  });
});

describe("isFlatWithinBlocks", () => {
  it("is true when each block's Panchayats share one p50", () => {
    expect(
      isFlatWithinBlocks([row("P1", "B1", 3, 3), row("P2", "B1", 3, 3), row("P3", "B2", 5, 4)]),
    ).toBe(true);
  });
  it("is false as soon as one block varies, and for no rows", () => {
    expect(isFlatWithinBlocks([row("P1", "B1", 3, 3), row("P2", "B1", 4, 3)])).toBe(false);
    expect(isFlatWithinBlocks([])).toBe(false);
  });
});

describe("tableRows", () => {
  it("adds names from the boundaries and falls back to the id", () => {
    const geo = {
      type: "FeatureCollection",
      data_mode: "mock",
      features: [
        {
          type: "Feature",
          properties: { panchayat_id: "P1", name: "Alpha", block_id: "B1" },
          geometry: { type: "Polygon", coordinates: [] },
        },
      ],
    } as unknown as PanchayatCollection;
    const rows = tableRows(forecast("rain", [row("P1", "B1", 1, 1), row("P9", "B1", 1, 1)]), geo);
    expect(rows.map((r) => r.name)).toEqual(["Alpha", "P9"]);
  });
});

describe("legendTicks", () => {
  it("prints rain breaks plainly", () => {
    expect(legendTicks(valueRamp("rain"), "en")).toEqual(["0", "1", "5", "15", "35", "65"]);
  });
  it("signs differences and keeps round halves", () => {
    const ramp = rampForMode(forecast("rain", [row("P1", "B1", 0, 4.5)]), "delta");
    expect(legendTicks(ramp, "en")).toEqual(["-5", "-2.5", "0", "+2.5", "+5"]);
  });
});

describe("boundsOf", () => {
  it("returns [west, south, east, north] over nested rings", () => {
    const fc = {
      features: [
        {
          geometry: {
            coordinates: [
              [
                [75.4, 28.9],
                [75.9, 29.3],
                [75.5, 29.0],
              ],
            ],
          },
        },
        {
          geometry: {
            coordinates: [
              [
                [
                  [75.3, 29.1],
                  [75.6, 29.2],
                ],
              ],
            ],
          },
        },
      ],
    };
    expect(boundsOf(fc)).toEqual([75.3, 28.9, 75.9, 29.3]);
    expect(boundsOf({ features: [] })).toBeNull();
  });
});
