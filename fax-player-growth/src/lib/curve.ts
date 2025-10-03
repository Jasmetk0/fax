/**
 * Matematické funkce pro ideální kariérní křivku squashového hráče.
 */
export type CurveParams = {
  potential: number;
  floor: number;
  peakAge: number;
  k: number;
  peakRetention: number;
  d1: number;
  d2: number;
  d3: number;
};

export type Point = { age: number; ovr: number };

const MIN_OVR = 20;
const MAX_OVR = 100;
const EPS = 1e-6;

const DECLINE_SEGMENTS = [
  { start: 28, end: 33 },
  { start: 33, end: 37 },
  { start: 37, end: Number.POSITIVE_INFINITY },
] as const;

const getRate = (segmentIndex: number, params: CurveParams): number => {
  if (segmentIndex === 0) return params.d1;
  if (segmentIndex === 1) return params.d2;
  return params.d3;
};

const clamp = (value: number, min: number, max: number) => Math.min(Math.max(value, min), max);

const logisticBase = (age: number, params: CurveParams): number => {
  const x = age - 8;
  const center = params.peakAge - 8;
  const rise = 1 / (1 + Math.exp(-params.k * (x - center)));
  const mapped = params.floor + rise * (params.potential - params.floor);
  return clamp(mapped, params.floor, params.potential);
};

const plateauValue = (age: number, params: CurveParams): number => {
  const base = logisticBase(age, params);
  const plateauHalf = Math.max(params.peakRetention / 2, EPS);
  const distance = Math.abs(age - params.peakAge);
  if (distance >= plateauHalf) {
    return clamp(base, MIN_OVR, MAX_OVR);
  }
  const blend = 1 - distance / plateauHalf;
  const plateauTarget = Math.max(params.potential - 0.5, base);
  const value = base * (1 - blend) + plateauTarget * blend;
  return clamp(value, MIN_OVR, MAX_OVR);
};

const declineMultiplier = (startAge: number, endAge: number, params: CurveParams): number => {
  let multiplier = 1;
  for (let i = 0; i < DECLINE_SEGMENTS.length; i += 1) {
    const { start, end } = DECLINE_SEGMENTS[i];
    const segStart = Math.max(startAge, start);
    const segEnd = Math.min(endAge, end);
    if (segEnd - segStart <= EPS) continue;
    const years = segEnd - segStart;
    const rate = clamp(getRate(i, params), 0, 0.5);
    multiplier *= Math.pow(1 - rate, years);
  }
  return multiplier;
};

/**
 * Vrací ideální OVR pro daný věk.
 */
export function idealOVRAtAge(age: number, params: CurveParams): number {
  const clampedAge = clamp(age, 0, 100);
  const plateau = plateauValue(clampedAge, params);
  const declineStart = Math.max(params.peakAge, 28);
  if (clampedAge <= declineStart) {
    return clamp(plateau, MIN_OVR, MAX_OVR);
  }
  const baseValue = plateauValue(declineStart, params);
  const multiplier = declineMultiplier(declineStart, clampedAge, params);
  const value = baseValue * multiplier;
  return clamp(value, MIN_OVR, MAX_OVR);
}

/**
 * Generuje celou křivku v daném rozsahu věku.
 */
export function idealCurve(
  params: CurveParams,
  ageFrom = 10,
  ageTo = 40,
  step = 0.25,
): Point[] {
  const points: Point[] = [];
  for (let age = ageFrom; age <= ageTo + EPS; age += step) {
    const roundedAge = Math.round(age * 100) / 100;
    points.push({ age: roundedAge, ovr: idealOVRAtAge(roundedAge, params) });
  }
  return points;
}

/**
 * Průměrný sklon křivky mezi dvěma věky (ΔOVR na rok).
 */
export function slopeBetween(a1: number, a2: number, params: CurveParams): number {
  if (a2 <= a1) return 0;
  const v1 = idealOVRAtAge(a1, params);
  const v2 = idealOVRAtAge(a2, params);
  return (v2 - v1) / (a2 - a1);
}
