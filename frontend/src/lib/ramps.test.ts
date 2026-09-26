import { describe, expect, it } from "vitest";
import {
  colorFor,
  deltaRamp,
  fillColorExpression,
  mixColors,
  niceCeil,
  sampleColors,
  temperatureBreaks,
  valueRamp,
} from "./ramps";

describe("sampleColors", () => {
  const pal = ["#000000", "#ffffff"];

  it("returns the ends and blends between them", () => {
    expect(sampleColors(pal, 3)).toEqual(["#000000", "#808080", "#ffffff"]);
  });

  it("returns exactly n colours and the palette itself when n matches", () => {
    const five = ["#000000", "#404040", "#808080", "#c0c0c0", "#ffffff"];
    expect(sampleColors(five, 5)).toEqual(five);
    expect(sampleColors(five, 9)).toHaveLength(9);
    expect(sampleColors(five, 0)).toEqual([]);
  });

  it("mixes colours in RGB", () => {
    expect(mixColors("#000000", "#ff0000", 0.5)).toBe("#800000");
  });
});

describe("value ramps (Guide 8.2)", () => {
  it("uses the guide's fixed rain breaks, light to dark blue", () => {
    const r = valueRamp("rain");
    expect(r.stops.map((s) => s.value)).toEqual([0, 1, 5, 15, 35, 65]);
    expect(r.unit).toBe("mm");
    expect(r.stops[0]?.color).toBe("#f7fbff");
    expect(r.stops[5]?.color).toBe("#08519c");
  });

  it("uses fixed breaks for humidity and wind", () => {
    expect(valueRamp("rh").stops.map((s) => s.value)).toEqual([20, 40, 60, 80, 100]);
    expect(valueRamp("wind").stops.map((s) => s.value)).toEqual([0, 5, 10, 15, 20, 30]);
    expect(valueRamp("wind").unit).toBe("km/h");
  });

  it("gives temperatures 3 C breaks that cover the data", () => {
    expect(temperatureBreaks([26.6, 36.1])).toEqual([24, 27, 30, 33, 36, 39]);
    expect(valueRamp("tmax", [26.6, 36.1]).stops.map((s) => s.value)).toEqual([
      24, 27, 30, 33, 36, 39,
    ]);
  });

  it("keeps at least two temperature steps, also for one value or none", () => {
    expect(temperatureBreaks([24])).toEqual([24, 27, 30]);
    expect(temperatureBreaks([23.1, 23.4])).toEqual([21, 24, 27]);
    expect(temperatureBreaks([])).toEqual([0, 3, 6]);
    expect(temperatureBreaks([-4.2, 1])).toEqual([-6, -3, 0, 3]);
  });

  it("colours cold Tmin dark blue and warm Tmin pale (YlGnBu reversed)", () => {
    const r = valueRamp("tmin", [3, 20]);
    expect(r.stops[0]?.color).toBe("#253494");
    expect(r.stops[r.stops.length - 1]?.color).toBe("#ffffd9");
  });
});

describe("difference ramp", () => {
  it("is symmetric around zero with a nice half-width", () => {
    const r = deltaRamp("rain", [-4.5, 0.88]);
    expect(r.kind).toBe("diverging");
    expect(r.stops.map((s) => s.value)).toEqual([-5, -2.5, 0, 2.5, 5]);
    expect(r.stops[2]?.color).toBe("#f7f7f7");
  });

  it("never shrinks below the floor for the variable", () => {
    expect(deltaRamp("tmax", [-0.1, 0.05]).stops.map((s) => s.value)).toEqual([
      -0.5, -0.25, 0, 0.25, 0.5,
    ]);
    expect(deltaRamp("rain", []).stops.map((s) => s.value)).toEqual([-1, -0.5, 0, 0.5, 1]);
  });

  it("paints more rain blue and warmer red", () => {
    const rain = deltaRamp("rain", [2]);
    const tmax = deltaRamp("tmax", [2]);
    expect(rain.stops[4]?.color).toBe("#2166ac");
    expect(tmax.stops[4]?.color).toBe("#b2182b");
  });
});

describe("niceCeil", () => {
  it("rounds up to 1, 2, 2.5 or 5 times a power of ten", () => {
    expect(niceCeil(0.42)).toBe(0.5);
    expect(niceCeil(1)).toBe(1);
    expect(niceCeil(1.1)).toBe(2);
    expect(niceCeil(2.2)).toBe(2.5);
    expect(niceCeil(4.5)).toBe(5);
    expect(niceCeil(7)).toBe(10);
    expect(niceCeil(0)).toBe(0);
    expect(niceCeil(Number.NaN)).toBe(0);
  });
});

describe("colorFor and the map expression", () => {
  const r = valueRamp("rain");

  it("interpolates like the map and clamps at the ends", () => {
    expect(colorFor(r, 0)).toBe(r.stops[0]?.color);
    expect(colorFor(r, -3)).toBe(r.stops[0]?.color);
    expect(colorFor(r, 500)).toBe(r.stops[5]?.color);
    expect(colorFor(r, 65)).toBe(r.stops[5]?.color);
    expect(colorFor(r, 3)).toBe(mixColors(r.stops[1]!.color, r.stops[2]!.color, 0.5)); // eslint-disable-line @typescript-eslint/no-non-null-assertion
  });

  it("returns null for missing values", () => {
    expect(colorFor(r, null)).toBeNull();
    expect(colorFor(r, Number.NaN)).toBeNull();
  });

  it("builds a feature-state expression with a no-value case and every stop", () => {
    const expr = fillColorExpression(r, "#e3e8e6");
    expect(expr[0]).toBe("case");
    expect(expr[1]).toEqual(["==", ["feature-state", "v"], null]);
    expect(expr[2]).toBe("#e3e8e6");
    const interp = expr[3] as unknown[];
    expect(interp.slice(0, 3)).toEqual([
      "interpolate",
      ["linear"],
      ["to-number", ["feature-state", "v"]],
    ]);
    expect(interp.slice(3)).toEqual(r.stops.flatMap((s) => [s.value, s.color]));
  });
});
