import { describe, expect, it } from "vitest";
import { sortRows } from "./sort";

describe("sortRows", () => {
  const rows = [
    { id: "a", v: 3 },
    { id: "b", v: null },
    { id: "c", v: 1 },
    { id: "d", v: 3 },
    { id: "e", v: Number.NaN },
  ];

  it("sorts numbers both ways and keeps ties in their original order", () => {
    expect(sortRows(rows, (r) => r.v, "asc").map((r) => r.id)).toEqual(["c", "a", "d", "b", "e"]);
    expect(sortRows(rows, (r) => r.v, "desc").map((r) => r.id)).toEqual(["a", "d", "c", "b", "e"]);
  });

  it("puts missing values last in either direction", () => {
    expect(
      sortRows(rows, (r) => r.v, "desc")
        .slice(-2)
        .map((r) => r.id),
    ).toEqual(["b", "e"]);
  });

  it("sorts names with numbers in natural order", () => {
    const names = ["MP0110", "MP0102", "MP0101"].map((id) => ({ id }));
    expect(sortRows(names, (r) => r.id, "asc").map((r) => r.id)).toEqual([
      "MP0101",
      "MP0102",
      "MP0110",
    ]);
  });

  it("does not change the input", () => {
    const copy = [...rows];
    sortRows(rows, (r) => r.v, "asc");
    expect(rows).toEqual(copy);
  });
});
