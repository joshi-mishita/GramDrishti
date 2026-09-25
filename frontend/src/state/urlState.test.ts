import { describe, expect, it } from "vitest";
import { readUrlState, writeUrlState } from "./urlState";

describe("URL state", () => {
  it("reads date, var and pid", () => {
    expect(readUrlState("?date=2024-09-09&var=tmax&pid=MP0103")).toEqual({
      issueDate: "2024-09-09",
      variable: "tmax",
      selectedPid: "MP0103",
    });
  });

  it("ignores invalid values", () => {
    expect(readUrlState("?date=2024-13-01&var=snow&pid=<script>")).toEqual({
      issueDate: null,
      variable: null,
      selectedPid: null,
    });
  });

  it("writes state and keeps unrelated params", () => {
    const out = writeUrlState("?lang=hi&pid=MP0101", {
      issueDate: "2024-12-24",
      variable: "rain",
      selectedPid: null,
    });
    const q = new URLSearchParams(out);
    expect(q.get("lang")).toBe("hi");
    expect(q.get("date")).toBe("2024-12-24");
    expect(q.get("var")).toBe("rain");
    expect(q.has("pid")).toBe(false);
  });

  it("round-trips", () => {
    const state = { issueDate: "2024-07-31", variable: "wind" as const, selectedPid: "MP0412" };
    expect(readUrlState(writeUrlState("", state))).toEqual(state);
  });
});
