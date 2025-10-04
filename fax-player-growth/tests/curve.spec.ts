import { describe, expect, it } from "vitest";
import { DEFAULT_PARAMS } from "../src/constants";
import { idealCurve, idealOVRAtAge, slopeBetween } from "../src/lib/curve";
import type { CurveParams } from "../src/types";

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

const P: CurveParams = {
  potential: 94,
  floor: 38,
  peakAge: 27.5,
  k: 0.41,
  peakRetention: 1.0,
  d1: 0.03,
  d2: 0.055,
  d3: 0.09,
};

describe("ideal curve – continuity & behaviour", () => {
  it("never exceeds potential or 100 and never goes below 20", () => {
    for (let a = 10; a <= 40; a += 0.25) {
      const v = idealOVRAtAge(a, P);
      expect(v).toBeLessThanOrEqual(100);
      expect(v).toBeLessThanOrEqual(P.potential + 1e-6);
      expect(v).toBeGreaterThanOrEqual(20);
    }
  });

  it("plateau has zero-ish slope at its edges (C¹-ish)", () => {
    const half = P.peakRetention / 2;
    const left = P.peakAge - half;
    const right = P.peakAge + half;
    const sLeft = slopeBetween(left - 0.05, left + 0.05, P);
    const sRight = slopeBetween(right - 0.05, right + 0.05, P);
    expect(Math.abs(sLeft)).toBeLessThan(0.15); // téměř ploché
    expect(Math.abs(sRight)).toBeLessThan(0.15);
  });

  it("decline starts after plateau or at 28, whichever is later", () => {
    const half = P.peakRetention / 2;
    const declineStart = Math.max(P.peakAge + half, 28);
    const sBefore = slopeBetween(declineStart - 0.2, declineStart - 0.01, P);
    const sAfter = slopeBetween(declineStart + 0.01, declineStart + 0.2, P);
    expect(sBefore).toBeGreaterThanOrEqual(-0.2); // neklesá výrazně
    expect(sAfter).toBeLessThan(0); // po startu už klesá
  });

  it("late segments decline faster: |33–36| > |28–32| and |37+| ≥ |33–36|", () => {
    const s1 = slopeBetween(29, 32, P); // ~ d1
    const s2 = slopeBetween(33, 36, P); // ~ d2
    const s3 = slopeBetween(37.5, 39.5, P); // ~ d3
    expect(Math.abs(s2)).toBeGreaterThan(Math.abs(s1));
    expect(Math.abs(s3)).toBeGreaterThanOrEqual(Math.abs(s2));
  });
});
