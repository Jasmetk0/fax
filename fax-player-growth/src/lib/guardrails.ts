import { PARAM_BOUNDS } from "../constants";
import type { CurveParams, GuardrailNotice } from "../types";

const EPS = 0.0005;

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const clampParam = (value: number, key: keyof CurveParams): number => {
  const bounds = PARAM_BOUNDS[key];
  return clamp(value, bounds.min, bounds.max);
};

export type GuardrailResult = {
  params: CurveParams;
  notices: GuardrailNotice[];
};

/**
 * Upravuje parametry tak, aby respektovaly domluvené guardraily.
 */
export function enforceGuardrails(input: CurveParams): GuardrailResult {
  const adjusted: CurveParams = { ...input };
  const notices: GuardrailNotice[] = [];

  (Object.keys(PARAM_BOUNDS) as (keyof CurveParams)[]).forEach((key) => {
    const next = clampParam(adjusted[key], key);
    if (next !== adjusted[key]) {
      adjusted[key] = next;
      notices.push({ field: key, message: `Parametr ${key} byl srovnán do povoleného rozsahu.` });
    }
  });

  if (adjusted.floor > adjusted.potential - 10) {
    adjusted.floor = adjusted.potential - 10;
    notices.push({ field: "floor", message: "Floor je blízko stropu, snižujeme ho na potenciál minus 10 bodů." });
  }

  if (adjusted.peakRetention > 3) {
    adjusted.peakRetention = 3;
    notices.push({ field: "peakRetention", message: "Plateau nemůže být širší než tři roky. Zkracujeme ho." });
  }

  if (adjusted.d1 >= adjusted.d2) {
    adjusted.d2 = clamp(adjusted.d1 + EPS, PARAM_BOUNDS.d2.min, PARAM_BOUNDS.d2.max);
    notices.push({ field: "decline", message: "d2 muselo být zvýšeno, aby navazovalo na d1." });
  }

  if (adjusted.d2 >= adjusted.d3) {
    adjusted.d3 = clamp(adjusted.d2 + EPS, PARAM_BOUNDS.d3.min, PARAM_BOUNDS.d3.max);
    notices.push({ field: "decline", message: "d3 jsme zvedli, aby zůstalo strmější než d2." });
  }

  return { params: adjusted, notices };
}
