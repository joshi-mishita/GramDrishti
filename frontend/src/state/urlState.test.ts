import { describe, expect, it } from "vitest";
import { readUrlState, writeUrlState } from "./urlState";

describe("URL state", () => {
  it("reads date, var and pid", () => {
    expect(readUrlState("?date=2024-09-09&var=tmax&pid=MP0103")).toEqual({
      issueDate: "2024-09-09",
      variable: "tmax",
      selectedPid: "MP0103",
      leadDay: null,
      viewMode: null,
    });
  });

  it("reads day and view, and rejects days outside the forecast", () => {
    expect(readUrlState("?day=3&view=delta")).toMatchObject({ leadDay: 3, viewMode: "delta" });
    expect(readUrlState("?day=6&view=table")).toMatchObject({ leadDay: null, viewMode: null });
    expect(readUrlState("?day=0")).toMatchObject({ leadDay: null });
  });

  it("leaves day and view out of the URL at their defaults", () => {
    const base = { issueDate: "2024-09-09", variable: "rain" as const, selectedPid: null };
    const plain = new URLSearchParams(
      writeUrlState("?day=4&view=block", { ...base, leadDay: 1, viewMode: "panchayat" }),
    );
    expect(plain.has("day")).toBe(false);
    expect(plain.has("view")).toBe(false);
    const set = new URLSearchParams(writeUrlState("", { ...base, leadDay: 2, viewMode: "block" }));
    expect(set.get("day")).toBe("2");
    expect(set.get("view")).toBe("block");
  });

  it("ignores invalid values", () => {
    expect(readUrlState("?date=2024-13-01&var=snow&pid=<script>")).toEqual({
      issueDate: null,
      variable: null,
      selectedPid: null,
      leadDay: null,
      viewMode: null,
    });
  });

  it("writes state and keeps unrelated params", () => {
    const out = writeUrlState("?lang=hi&pid=MP0101", {
      issueDate: "2024-12-24",
      variable: "rain",
      selectedPid: null,
      leadDay: 1,
      viewMode: "panchayat",
    });
    const q = new URLSearchParams(out);
    expect(q.get("lang")).toBe("hi");
    expect(q.get("date")).toBe("2024-12-24");
    expect(q.get("var")).toBe("rain");
    expect(q.has("pid")).toBe(false);
  });

  it("round-trips", () => {
    const state = {
      issueDate: "2024-07-31",
      variable: "wind" as const,
      selectedPid: "MP0412",
      leadDay: 3,
      viewMode: "delta" as const,
    };
    expect(readUrlState(writeUrlState("", state))).toEqual(state);
  });
});
