import { AGE_RANGE, FAN_RANGES, FAN_SAMPLES } from "../constants";
import type { CurveParams } from "../types";
import { idealCurve } from "./curve";

export type FanChartPoint = {
  age: number;
  median: number;
  q05: number;
  q25: number;
  q75: number;
  q95: number;
};

const EPS = 1e-9;

const linspace = (min: number, max: number, count: number): number[] => {
  if (count <= 1 || Math.abs(max - min) <= EPS) return [min];
  const step = (max - min) / (count - 1);
  const values = new Array<number>(count);
  for (let i = 0; i < count; i++) {
    values[i] = min + step * i;
  }
  return values;
};

const quantile = (values: number[], q: number): number => {
  if (values.length === 0) return 0;
  const sorted = [...values].sort((a, b) => a - b);
  const pos = (sorted.length - 1) * q;
  const base = Math.floor(pos);
  const rest = pos - base;
  const next = sorted[base + 1];
  if (next === undefined) return sorted[base];
  return sorted[base] + rest * (next - sorted[base]);
};

export type FanChartResult = FanChartPoint[];

/**
 * Deterministicky počítá fan chart (50 % a 90 %) pro dané parametry.
 */
export function buildFanChart(params: CurveParams): FanChartResult {
  const ages: number[] = [];
  for (let age = AGE_RANGE.min; age <= AGE_RANGE.max + EPS; age += AGE_RANGE.step) {
    ages.push(Math.round(age * 100) / 100);
  }

  const potentialSamples = linspace(FAN_RANGES.potential[0], FAN_RANGES.potential[1], FAN_SAMPLES.potential);
  const peakAgeSamples = linspace(FAN_RANGES.peakAge[0], FAN_RANGES.peakAge[1], FAN_SAMPLES.peakAge);
  const kSamples = linspace(FAN_RANGES.k[0], FAN_RANGES.k[1], FAN_SAMPLES.k);

  const valueMatrix: number[][] = ages.map(() => []);

  for (const potential of potentialSamples) {
    for (const peakAge of peakAgeSamples) {
      for (const k of kSamples) {
        const curve = idealCurve({ ...params, potential, peakAge, k });
        curve.forEach((point, index) => {
          valueMatrix[index].push(point.ovr);
        });
      }
    }
  }

  return ages.map((age, index) => {
    const values = valueMatrix[index];
    return {
      age,
      median: quantile(values, 0.5),
      q05: quantile(values, 0.05),
      q25: quantile(values, 0.25),
      q75: quantile(values, 0.75),
      q95: quantile(values, 0.95),
    };
  });
}
