import { describe, expect, it } from "vitest";
import { DEFAULT_PARAMS, AGE_RANGE } from "../src/constants";
import { idealCurve } from "../src/lib/curve";
import { buildFanChart } from "../src/lib/fanChart";

const findPoint = (age: number, points: { age: number }[]) =>
  points.find((point) => point.age === age);

describe("buildFanChart", () => {
  it("produces sorted quantiles of expected length", () => {
    const chart = buildFanChart(DEFAULT_PARAMS);
    const expectedLength = Math.floor((AGE_RANGE.max - AGE_RANGE.min) / AGE_RANGE.step + 1.0000001);
    expect(chart).toHaveLength(expectedLength);

    for (const point of chart) {
      expect(point.q05).toBeLessThanOrEqual(point.q25);
      expect(point.q25).toBeLessThanOrEqual(point.median);
      expect(point.median).toBeLessThanOrEqual(point.q75);
      expect(point.q75).toBeLessThanOrEqual(point.q95);
    }
  });

  it("tracks the ideal curve closely at key ages", () => {
    const chart = buildFanChart(DEFAULT_PARAMS);
    const ideal = idealCurve(DEFAULT_PARAMS);
    const checkAges = [18, 24, 30, 34];

    for (const age of checkAges) {
      const chartPoint = findPoint(age, chart);
      const idealPoint = findPoint(age, ideal);
      expect(chartPoint).toBeDefined();
      expect(idealPoint).toBeDefined();
      if (chartPoint && idealPoint) {
        expect(Math.abs(chartPoint.median - idealPoint.ovr)).toBeLessThan(5);
      }
    }
  });

  it("keeps the median within the fan envelopes", () => {
    const chart = buildFanChart(DEFAULT_PARAMS);

    for (const point of chart) {
      expect(point.q05).toBeLessThanOrEqual(point.median);
      expect(point.median).toBeLessThanOrEqual(point.q95);
    }
  });
});
