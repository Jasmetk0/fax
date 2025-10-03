export type CurveParams = {
  potential: number;
  floor: number;
  peakAge: number;
  k: number;
  peakRetention: number; // v letech
  d1: number; // 28–32 (ročně)
  d2: number; // 33–36
  d3: number; // 37+
};

export type Point = { age: number; ovr: number };

const MIN_OVR = 20;
const MAX_OVR = 100;
const EPS = 1e-6;
const SMOOTH_DECLINE_SPAN = 0.75; // roky pro plynulý náběh poklesu

const DECLINE_SEGMENTS = [
  { start: 28, end: 33 },
  { start: 33, end: 37 },
  { start: 37, end: Number.POSITIVE_INFINITY },
] as const;

const clamp = (v: number, min: number, max: number) => Math.min(Math.max(v, min), max);
const getRate = (i: number, p: CurveParams) => (i === 0 ? p.d1 : i === 1 ? p.d2 : p.d3);
const logit = (x: number) => Math.log(x / (1 - x));
const easedDuration = (duration: number, span: number) => {
  if (duration <= EPS) return 0;
  if (span <= EPS) return duration;
  const limited = Math.min(duration, span);
  const eased = (limited * limited) / (span * span) * (2 * span - limited);
  const remainder = Math.max(duration - span, 0);
  return eased + remainder;
};

/** Logistický náběh mapovaný na [floor, potential], nastavený tak,
 * aby byl v peaku (age = peakAge) ~ 99,5 % saturovaný → plateau dělá už jen jemné „cap“. */
const logisticBase = (age: number, params: CurveParams): number => {
  const targetAtPeak = 0.995; // ~99.5 % naplnění v peaku pro velmi ploché plateau
  const center = params.peakAge - logit(targetAtPeak) / params.k;
  const rise = 1 / (1 + Math.exp(-params.k * (age - center)));
  const mapped = params.floor + rise * (params.potential - params.floor);
  return clamp(mapped, params.floor, params.potential);
};

/** Hladké plateau kolem peaku (C¹ spojité) pomocí kosinového vážení (easing).
 * Na hranách má nulovou derivaci → žádné „zuby“. */
const plateauValue = (age: number, params: CurveParams): number => {
  const base = logisticBase(age, params);
  const half = Math.max(params.peakRetention / 2, EPS);
  const d = Math.abs(age - params.peakAge);
  if (d >= half) return clamp(base, MIN_OVR, MAX_OVR);

  // cosine easing 1→0 (derivace 0 na hranách)
  const t = d / half;                      // 0..1
  const w = 0.5 * (1 + Math.cos(Math.PI * t)); // 1..0
  const target = Math.max(params.potential - 0.5, base);
  const val = base * (1 - w) + target * w;
  return clamp(val, MIN_OVR, MAX_OVR);
};

/** Násobič poklesu v čase pro zadaný interval, včetně tří pásů (28–32 / 33–36 / 37+). */
const declineMultiplier = (startAge: number, endAge: number, params: CurveParams): number => {
  let m = 1;
  for (let i = 0; i < DECLINE_SEGMENTS.length; i++) {
    const { start, end } = DECLINE_SEGMENTS[i];
    const segStart = Math.max(startAge, start);
    const segEnd = Math.min(endAge, end);
    if (segEnd - segStart <= EPS) continue;
    const years = segEnd - segStart;
    const rate = clamp(getRate(i, params), 0, 0.5);
    const effectiveYears = easedDuration(years, SMOOTH_DECLINE_SPAN);
    m *= Math.pow(1 - rate, effectiveYears);
  }
  return m;
};

/** Ideální OVR pro daný věk (bez vlivů prostředí – čistá křivka). */
export function idealOVRAtAge(age: number, params: CurveParams): number {
  // defenzivně sjednáme pořadí d1<d2<d3 (guardrails to řeší v UI, tady jen ochrana)
  const p: CurveParams = {
    ...params,
    d1: Math.min(params.d1, params.d2 - 1e-6),
    d2: Math.min(params.d2, params.d3 - 1e-6),
  };

  const a = clamp(age, 0, 100);
  const half = Math.max(p.peakRetention / 2, EPS);
  const declineStart = Math.max(p.peakAge + half, 28); // pokles až po CELÉM plateau, nejdřív v 28

  const valOnPlateau = plateauValue(a, p);
  if (a <= declineStart) return clamp(valOnPlateau, MIN_OVR, MAX_OVR);

  const baseAtStart = plateauValue(declineStart, p);
  const mult = declineMultiplier(declineStart, a, p);
  return clamp(baseAtStart * mult, MIN_OVR, MAX_OVR);
}

/** Celá křivka v rozsahu věků. Výpočet věku přes indexy (méně plovoucích chyb). */
export function idealCurve(
  params: CurveParams,
  ageFrom = 10,
  ageTo = 40,
  step = 0.25,
): Point[] {
  const n = Math.floor((ageTo - ageFrom) / step + EPS) + 1;
  const out: Point[] = [];
  for (let i = 0; i < n; i++) {
    const age = +(ageFrom + i * step).toFixed(2);
    out.push({ age, ovr: idealOVRAtAge(age, params) });
  }
  return out;
}

/** Průměrný sklon mezi dvěma věky (ΔOVR/rok). */
export function slopeBetween(a1: number, a2: number, params: CurveParams): number {
  if (a2 <= a1) return 0;
  return (idealOVRAtAge(a2, params) - idealOVRAtAge(a1, params)) / (a2 - a1);
}
