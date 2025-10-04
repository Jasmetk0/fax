import { describe, expect, it } from "vitest";
import { PARAM_BOUNDS, DEFAULT_PARAMS } from "../src/constants";
import { enforceGuardrails } from "../src/lib/guardrails";

describe("enforceGuardrails", () => {
  it("clamps parameters to declared bounds", () => {
    const { params } = enforceGuardrails({
      ...DEFAULT_PARAMS,
      potential: PARAM_BOUNDS.potential.max + 5,
      floor: PARAM_BOUNDS.floor.min - 5,
      k: PARAM_BOUNDS.k.max + 0.1,
    });

    expect(params.potential).toBe(PARAM_BOUNDS.potential.max);
    expect(params.floor).toBe(PARAM_BOUNDS.floor.min);
    expect(params.k).toBeCloseTo(PARAM_BOUNDS.k.max, 6);
  });

  it("keeps floor at least 10 points below potential", () => {
    const { params } = enforceGuardrails({
      ...DEFAULT_PARAMS,
      potential: 90,
      floor: 85,
    });

    expect(params.floor).toBeLessThanOrEqual(params.potential - 10);
    expect(params.floor).toBe(PARAM_BOUNDS.floor.max);
  });

  it("enforces monotonic decline rates", () => {
    const { params } = enforceGuardrails({
      ...DEFAULT_PARAMS,
      d1: 0.06,
      d2: 0.05,
      d3: 0.05,
    });

    expect(params.d1).toBeCloseTo(0.04, 3);
    expect(params.d1).toBeLessThan(params.d2);
    expect(params.d2).toBeLessThan(params.d3);
  });

  it("limits plateau duration", () => {
    const { params } = enforceGuardrails({
      ...DEFAULT_PARAMS,
      peakRetention: 5,
    });

    expect(params.peakRetention).toBeLessThanOrEqual(3);
  });
});
