import { describe, expect, it } from "vitest";
import { DEFAULT_PARAMS } from "../src/constants";
import { idealCurve, idealOVRAtAge, slopeBetween, type CurveParams } from "../src/lib/curve";

describe("curve", () => {
  it("rise je monotónní před peakem", () => {
    const params = { ...DEFAULT_PARAMS };
    const ages: number[] = [];
    for (let age = 10; age < params.peakAge; age += 0.5) {
      ages.push(age);
    }
    const values = ages.map((age) => idealOVRAtAge(age, params));
    for (let index = 1; index < values.length; index += 1) {
      const diff = values[index] - values[index - 1];
      expect(diff).toBeGreaterThan(-0.2);
    }
  });

  it("prudkost poklesu roste s každou fází", () => {
    const params: CurveParams = { ...DEFAULT_PARAMS, d1: 0.025, d2: 0.05, d3: 0.09 };
    const slopeEarly = slopeBetween(28, 32, params);
    const slopeMid = slopeBetween(33, 36, params);
    const slopeLate = slopeBetween(37, 39, params);
    expect(slopeMid).toBeLessThan(slopeEarly - 0.01);
    expect(slopeLate).toBeLessThan(slopeMid - 0.01);
  });

  it("default profil má vrchol v očekávaném okně", () => {
    const curve = idealCurve(DEFAULT_PARAMS);
    const peak = curve.reduce((best, point) => (point.ovr > best.ovr ? point : best), curve[0]);
    expect(peak.ovr).toBeGreaterThanOrEqual(93);
    expect(peak.ovr).toBeLessThanOrEqual(95);
    expect(peak.age).toBeGreaterThanOrEqual(27);
    expect(peak.age).toBeLessThanOrEqual(28.5);
  });
});
