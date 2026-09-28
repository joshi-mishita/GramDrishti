import { describe, expect, it } from "vitest";
import { formatStamp } from "./format";
import {
  FETCHED_AT_HEADER,
  FROM_CACHE_HEADER,
  noteResponse,
  oldestCached,
  useCacheStore,
} from "./network";

describe("offline copy bookkeeping", () => {
  it("reports the oldest stored time among responses served from cache", () => {
    useCacheStore.setState({ cached: {} });
    const cached = (at: string) =>
      new Headers({ [FROM_CACHE_HEADER]: "1", [FETCHED_AT_HEADER]: at });
    noteResponse("/a", cached("2024-12-16T02:40:00.000Z"));
    noteResponse("/b", cached("2024-12-15T10:00:00.000Z"));
    expect(oldestCached(useCacheStore.getState().cached)).toBe("2024-12-15T10:00:00.000Z");
    // A fresh network answer for /b removes it; only /a is still an offline copy.
    noteResponse("/b", new Headers());
    expect(oldestCached(useCacheStore.getState().cached)).toBe("2024-12-16T02:40:00.000Z");
    noteResponse("/a", new Headers());
    expect(oldestCached(useCacheStore.getState().cached)).toBeNull();
  });

  it("says 'from cache, time unknown' when the stamp is missing", () => {
    expect(oldestCached({ "/a": "" })).toBe("");
  });
});

describe("formatStamp", () => {
  it("formats in local time with weekday, day, month and minutes", () => {
    const d = new Date(2024, 11, 16, 8, 10);
    expect(formatStamp(d.toISOString(), "en")).toBe("Mon 16 Dec, 08:10");
    expect(formatStamp(d.toISOString(), "hi")).toBe("सोम 16 दिसंबर, 08:10");
  });
  it("returns null for anything that is not a timestamp", () => {
    expect(formatStamp("", "en")).toBeNull();
    expect(formatStamp("yesterday", "en")).toBeNull();
  });
});
