import { DEFAULT_STATE, PARAM_BOUNDS } from "../constants";
import type { CurveParams, GuardrailNotice, UrlState } from "../types";
import { enforceGuardrails } from "./guardrails";

const cloneParams = (params: CurveParams): CurveParams => ({ ...params });

const decimalsForStep = (step: number): number => {
  const precision = Math.ceil(-Math.log10(step));
  return Math.max(0, precision);
};

const roundParam = (value: number, key: keyof CurveParams): number => {
  const { step } = PARAM_BOUNDS[key];
  const decimals = decimalsForStep(step);
  return Number(value.toFixed(decimals));
};

const parseNumber = (value: string | null): number | undefined => {
  if (value === null) return undefined;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
};

const parseBoolean = (value: string | null): boolean | undefined => {
  if (value === null) return undefined;
  return value === "1" || value.toLowerCase() === "true" ? true : value === "0" || value.toLowerCase() === "false" ? false : undefined;
};

const applyBounds = (params: CurveParams): CurveParams => {
  const next: CurveParams = { ...params };
  (Object.keys(PARAM_BOUNDS) as (keyof CurveParams)[]).forEach((key) => {
    const bounds = PARAM_BOUNDS[key];
    if (next[key] < bounds.min) next[key] = bounds.min;
    if (next[key] > bounds.max) next[key] = bounds.max;
  });
  return next;
};

export type ParsedUrlState = {
  state: UrlState;
  notices: GuardrailNotice[];
};

/**
 * Parsuje stav z URL query stringu.
 */
export function parseUrlState(search: string, base: UrlState = DEFAULT_STATE): ParsedUrlState {
  const params = new URLSearchParams(search);
  const initial: UrlState = {
    params: cloneParams(base.params),
    showFanChart: base.showFanChart,
    showCohort: base.showCohort,
    preset: base.preset,
  };

  (Object.keys(PARAM_BOUNDS) as (keyof CurveParams)[]).forEach((key) => {
    const value = parseNumber(params.get(key));
    if (value !== undefined) {
      initial.params[key] = value;
    }
  });

  const fan = parseBoolean(params.get("fan"));
  if (fan !== undefined) initial.showFanChart = fan;

  const cohort = parseBoolean(params.get("cohort"));
  if (cohort !== undefined) initial.showCohort = cohort;

  const preset = params.get("preset");
  if (preset === "shotmaker" || preset === "retriever" || preset === "hybrid") {
    initial.preset = preset;
  }

  const bounded = applyBounds(initial.params);
  const { params: guardedParams, notices } = enforceGuardrails(bounded);

  return {
    state: { ...initial, params: guardedParams },
    notices,
  };
}

/**
 * Serializuje stav aplikace do query stringu.
 */
export function serializeUrlState(state: UrlState): string {
  const search = new URLSearchParams();
  (Object.keys(PARAM_BOUNDS) as (keyof CurveParams)[]).forEach((key) => {
    search.set(key, roundParam(state.params[key], key).toString());
  });
  search.set("fan", state.showFanChart ? "1" : "0");
  search.set("cohort", state.showCohort ? "1" : "0");
  search.set("preset", state.preset);
  const query = search.toString();
  return query ? `?${query}` : "";
}

/**
 * Synchronizuje URL bez reloadu.
 */
export function syncUrlState(state: UrlState) {
  const query = serializeUrlState(state);
  const next = `${window.location.pathname}${query}`;
  if (next !== window.location.href.replace(window.location.origin, "")) {
    window.history.replaceState({}, "fax-player-growth", next);
  }
}
