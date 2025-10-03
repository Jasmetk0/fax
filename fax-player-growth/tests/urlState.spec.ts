import { describe, expect, it } from "vitest";
import { DEFAULT_STATE } from "../src/constants";
import { parseUrlState, serializeUrlState } from "../src/lib/urlState";
import type { UrlState } from "../src/types";

describe("urlState", () => {
  it("roundtrip serializace zachová hodnoty", () => {
    const state: UrlState = {
      params: {
        ...DEFAULT_STATE.params,
        potential: 96.2,
        floor: 42.5,
        peakAge: 29.4,
        k: 0.47,
        peakRetention: 1.4,
        d1: 0.028,
        d2: 0.052,
        d3: 0.088,
      },
      showFanChart: true,
      showCohort: true,
      preset: "shotmaker",
    };

    const query = serializeUrlState(state);
    const parsed = parseUrlState(query, DEFAULT_STATE);

    expect(parsed.state.showFanChart).toBe(state.showFanChart);
    expect(parsed.state.showCohort).toBe(state.showCohort);
    expect(parsed.state.preset).toBe(state.preset);

    (Object.keys(state.params) as (keyof UrlState["params"])[]).forEach((key) => {
      expect(parsed.state.params[key]).toBeCloseTo(state.params[key], 3);
    });
  });
});
