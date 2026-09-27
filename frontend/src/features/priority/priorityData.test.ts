import { describe, expect, it } from "vitest";
import type { PriorityItem } from "../../api/types";
import {
  leadDayOf,
  levelSortValue,
  mapLinkFor,
  rankAndFilter,
  readFilters,
  writeFilters,
} from "./priorityData";

const item = (
  pid: string,
  block: string,
  risk: PriorityItem["top_risk"],
  level: PriorityItem["level"],
  score: number,
  valid: string | null = "2024-09-10",
): PriorityItem => ({
  panchayat_id: pid,
  block_id: block,
  top_risk: risk,
  level,
  score,
  crops_affected: [],
  headline: { en: "x", hi: null, pa: null },
  valid_date: valid,
});

const items = [
  item("MP0301", "MB03", "heavy_rain", "severe", 0.64),
  item("MP0507", "MB05", "waterlogging", "high", 0.5),
  item("MP0302", "MB03", "heavy_rain", "high", 0.4),
  item("MP0110", "MB01", "dry_spell", "moderate", 0.3),
];

describe("priority filters", () => {
  it("reads defaults and valid values from the URL", () => {
    expect(readFilters("")).toEqual({ horizon: 2, type: null, block: null });
    expect(readFilters("?horizon=3&type=heat&block=MB02")).toEqual({
      horizon: 3,
      type: "heat",
      block: "MB02",
    });
    expect(readFilters("?horizon=5&type=flood&block=<b>")).toEqual({
      horizon: 2,
      type: null,
      block: null,
    });
  });

  it("writes only what differs from the default and keeps other keys", () => {
    const q = new URLSearchParams(
      writeFilters("?date=2024-09-09&block=MB01", { horizon: 2, type: "frost", block: null }),
    );
    expect(q.get("date")).toBe("2024-09-09");
    expect(q.has("horizon")).toBe(false);
    expect(q.get("type")).toBe("frost");
    expect(q.has("block")).toBe(false);
  });

  it("keeps the API rank when filtering by risk type and block", () => {
    const rain = rankAndFilter(items, { type: "heavy_rain", block: null });
    expect(rain.map((r) => [r.panchayat_id, r.rank])).toEqual([
      ["MP0301", 1],
      ["MP0302", 3],
    ]);
    const mb03 = rankAndFilter(items, { type: null, block: "MB03" });
    expect(mb03).toHaveLength(2);
    expect(rankAndFilter(items, { type: "frost", block: null })).toEqual([]);
  });

  it("sorts levels before scores", () => {
    const [severe, high1, high2, moderate] = items.map(levelSortValue) as number[];
    expect(severe).toBeGreaterThan(high1 as number);
    expect(high1).toBeGreaterThan(high2 as number);
    expect(high2).toBeGreaterThan(moderate as number);
  });
});

describe("map link for a priority row", () => {
  it("opens the Panchayat with its risk layer and the variable behind it", () => {
    const url = new URL(mapLinkFor(items[1] as PriorityItem, "2024-09-09"), "http://x");
    expect(url.pathname).toBe("/map");
    expect(Object.fromEntries(url.searchParams)).toEqual({
      date: "2024-09-09",
      var: "rain",
      pid: "MP0507",
      risk: "waterlogging",
    });
  });

  it("sets the day of the risk when it is not tomorrow", () => {
    const later = item("MP0412", "MB04", "heat", "high", 0.7, "2024-03-02");
    // Across the leap day: 29 Feb to 2 Mar is 2 days.
    const url = new URL(mapLinkFor(later, "2024-02-29"), "http://x");
    expect(url.searchParams.get("var")).toBe("tmax");
    expect(url.searchParams.get("day")).toBe("2");
  });

  it("works out the lead day, falling back to 1", () => {
    expect(leadDayOf("2024-09-09", "2024-09-10")).toBe(1);
    expect(leadDayOf("2024-09-09", "2024-09-11")).toBe(2);
    expect(leadDayOf("2024-09-09", null)).toBe(1);
    expect(leadDayOf("2024-09-09", "2024-09-30")).toBe(1);
  });
});
