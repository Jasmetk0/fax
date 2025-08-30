import { E, monthLengths, yearLength, toOrdinal, fromOrdinal } from "/static/fax_calendar/core.js";

export const TROPICAL_YEAR = 428.5646875;

// Start ordinal of year y (global 1-based ordinal of 1/1/y)
export function ordinalAtYearStart(y) {
  let n = 1;
  for (let yy = 1; yy < y; yy++) n += 428 + E(yy);
  return n;
}

export function toGlobalOrdinal(y, m, d) {
  return ordinalAtYearStart(y) + (toOrdinal(y, m, d) - 1);
}

export function fromGlobalOrdinal(ord) {
  let y = 1,
    start = 1;
  // simple walk; admin scale is fine
  for (;;) {
    const yl = 428 + E(y);
    const end = start + yl - 1;
    if (ord >= start && ord <= end) {
      const doy = ord - start + 1;
      const [_, m, d] = fromOrdinal(y, doy);
      return { y, m, d, doy };
    }
    start = end + 1;
    y++;
  }
}

// global phase offsets (rounded to whole days)
const PHASES = {
  spring: 0.25 * TROPICAL_YEAR,
  summer: 0.5 * TROPICAL_YEAR,
  autumn: 0.75 * TROPICAL_YEAR,
  winter: 1.0 * TROPICAL_YEAR,
};

// all k such that round(phase + k*TY) ∈ [start,end]
function anchorsInRange(start, end, phase) {
  const kMin = Math.ceil((start - phase - 0.5) / TROPICAL_YEAR);
  const kMax = Math.floor((end - phase + 0.5) / TROPICAL_YEAR);
  const out = [];
  for (let k = kMin; k <= kMax; k++) {
    const ord = Math.round(phase + k * TROPICAL_YEAR);
    if (ord >= start && ord <= end) out.push(ord);
  }
  return out;
}

// Return anchors that actually occur inside year y (0..2 winters possible)
export function eventsForYear(y) {
  const start = ordinalAtYearStart(y);
  const end = start + yearLength(y) - 1;

  const springs = anchorsInRange(start, end, PHASES.spring).map((ord) => ({
    ord,
    ...fromGlobalOrdinal(ord),
  }));
  const summers = anchorsInRange(start, end, PHASES.summer).map((ord) => ({
    ord,
    ...fromGlobalOrdinal(ord),
  }));
  const autumns = anchorsInRange(start, end, PHASES.autumn).map((ord) => ({
    ord,
    ...fromGlobalOrdinal(ord),
  }));
  const winters = anchorsInRange(start, end, PHASES.winter).map((ord) => ({
    ord,
    ...fromGlobalOrdinal(ord),
  }));

  return { springs, summers, autumns, winters };
}

// Compute season segments for season bar, using real anchors present in y.
// Returns [{kind:"winter_i|spring|summer|autumn", startDoy, endDoy}] and an array of winter marks [{doy}]
export function seasonSegments(y) {
  const start = ordinalAtYearStart(y);
  const { springs, summers, autumns, winters } = eventsForYear(y);
  const yl = yearLength(y);

  // Helper to get DOY arrays
  const sDOY = springs.map((a) => a.doy).sort((a, b) => a - b);
  const uDOY = summers.map((a) => a.doy).sort((a, b) => a - b);
  const aDOY = autumns.map((a) => a.doy).sort((a, b) => a - b);
  const wDOY = winters.map((a) => a.doy).sort((a, b) => a - b); // 0..2

  const segs = [];
  // Winter I: from 1 to day before first Spring (if any); else to before Summer; else before Autumn; else until before Winter; else to yl (no anchors at all)
  const firstSpring = sDOY[0],
    firstSummer = uDOY[0],
    firstAutumn = aDOY[0],
    firstWinter = wDOY[0];
  let cut = yl; // default cut at end
  if (firstSpring) cut = Math.min(cut, firstSpring - 1);
  if (!firstSpring && firstSummer) cut = Math.min(cut, firstSummer - 1);
  if (!firstSpring && !firstSummer && firstAutumn) cut = Math.min(cut, firstAutumn - 1);
  if (!firstSpring && !firstSummer && !firstAutumn && firstWinter)
    cut = Math.min(cut, firstWinter - 1);
  segs.push({ kind: "winter_i", startDoy: 1, endDoy: Math.max(1, cut) });

  // Spring segment if Spring and Summer exist (use first occurrences)
  if (firstSpring && firstSummer)
    segs.push({ kind: "spring", startDoy: firstSpring, endDoy: firstSummer - 1 });
  // Summer segment if Summer and Autumn exist
  if (firstSummer && firstAutumn)
    segs.push({ kind: "summer", startDoy: firstSummer, endDoy: firstAutumn - 1 });
  // Autumn segment: from Autumn to day before first Winter if exists, else to yl
  if (firstAutumn) {
    const endA = firstWinter ? firstWinter - 1 : yl;
    segs.push({ kind: "autumn", startDoy: firstAutumn, endDoy: endA });
  }

  const winterMarks = wDOY.map((d) => ({ doy: d }));
  return { segs, winterMarks };
}

// Which season a given DOY belongs to, using segments computed above
export function seasonOf(y, doy) {
  const { segs, winterMarks } = seasonSegments(y);
  if (winterMarks.some((w) => w.doy === doy)) return "Zima II";
  for (const s of segs) {
    if (doy >= s.startDoy && doy <= s.endDoy) {
      if (s.kind === "winter_i") return "Zima I";
      if (s.kind === "spring") return "Jaro";
      if (s.kind === "summer") return "Léto";
      if (s.kind === "autumn") return "Podzim";
    }
  }
  // fallback
  return "Zima I";
}

if (typeof window !== "undefined") {
  window.woorldAstro = {
    TROPICAL_YEAR,
    ordinalAtYearStart,
    toGlobalOrdinal,
    fromGlobalOrdinal,
    eventsForYear,
    seasonSegments,
    seasonOf,
  };
}

