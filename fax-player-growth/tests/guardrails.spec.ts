import { describe, expect, it } from "vitest";
import { DEFAULT_PARAMS } from "../src/constants";
import { enforceGuardrails } from "../src/lib/guardrails";

describe("guardrails", () => {
  it("upravený floor respektuje odstup od potenciálu", () => {
    const params = { ...DEFAULT_PARAMS, potential: 90, floor: 85 };
    const result = enforceGuardrails(params);
    expect(result.params.floor).toBeLessThanOrEqual(result.params.potential - 10);
    expect(result.notices.some((notice) => notice.field === "floor")).toBe(true);
  });

  it("zvyšuje d3 při kolizi s d2", () => {
    const params = { ...DEFAULT_PARAMS, d1: 0.03, d2: 0.07, d3: 0.07 };
    const result = enforceGuardrails(params);
    expect(result.params.d2).toBeGreaterThan(result.params.d1);
    expect(result.params.d3).toBeGreaterThan(result.params.d2);
    expect(result.notices.some((notice) => notice.field === "decline")).toBe(true);
  });
});
