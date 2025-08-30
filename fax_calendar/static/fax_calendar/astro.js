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

export function seasonSegments(y) {
  const start = ordinalAtYearStart(y);
  const yl = yearLength(y);
  const end = start + yl - 1;

  // collect anchors inside year
  const inside = [
    ...anchorsInRange(start, end, PHASES.spring).map((o) => ({ ord: o, kind: "spring" })),
    ...anchorsInRange(start, end, PHASES.summer).map((o) => ({ ord: o, kind: "summer" })),
    ...anchorsInRange(start, end, PHASES.autumn).map((o) => ({ ord: o, kind: "autumn" })),
    ...anchorsInRange(start, end, PHASES.winter).map((o) => ({ ord: o, kind: "winter" })),
  ];

  // nearest anchors just BEFORE start and just AFTER end (to determine start season and final cut)
  const nearestBefore = (phase) =>
    Math.round(phase + Math.floor((start - 0.5 - phase) / TROPICAL_YEAR) * TROPICAL_YEAR);
  const nearestAfter = (phase) =>
    Math.round(phase + Math.ceil((end + 0.5 - phase) / TROPICAL_YEAR) * TROPICAL_YEAR);

  const before = [
    { ord: nearestBefore(PHASES.spring), kind: "spring" },
    { ord: nearestBefore(PHASES.summer), kind: "summer" },
    { ord: nearestBefore(PHASES.autumn), kind: "autumn" },
    { ord: nearestBefore(PHASES.winter), kind: "winter" },
  ].filter((a) => a.ord < start);

  const after = [
    { ord: nearestAfter(PHASES.spring), kind: "spring" },
    { ord: nearestAfter(PHASES.summer), kind: "summer" },
    { ord: nearestAfter(PHASES.autumn), kind: "autumn" },
    { ord: nearestAfter(PHASES.winter), kind: "winter" },
  ].filter((a) => a.ord > end);

  const events = [...before, ...inside, ...after].sort((a, b) => a.ord - b.ord);

  // find last anchor before start → starting season for DOY 1
  let iPrev = -1;
  for (let i = events.length - 1; i >= 0; i--) {
    if (events[i].ord < start) {
      iPrev = i;
      break;
    }
  }
  let currentKind = iPrev >= 0 ? events[iPrev].kind : "winter"; // fallback
  let cursor = 1;

  const segs = [];
  const marks = [];

  for (const e of events) {
    if (e.ord < start || e.ord > end) continue;
    const doy = e.ord - start + 1;
    // close running segment up to day before this anchor
    if (cursor <= doy - 1)
      segs.push({ kind: currentKind, startDoy: cursor, endDoy: doy - 1 });
    // this anchor DAY starts its season
    marks.push({ kind: e.kind, doy });
    currentKind = e.kind;
    cursor = doy; // anchor belongs to the new season
  }
  // close to end of year
  if (cursor <= yl) segs.push({ kind: currentKind, startDoy: cursor, endDoy: yl });

  return { segs, marks };
}

export function seasonOf(y, doy) {
  const { segs } = seasonSegments(y);
  const s = segs.find((s) => doy >= s.startDoy && doy <= s.endDoy);
  const k = s ? s.kind : "winter";
  // Capitalize: "Winter"/"Spring"/"Summer"/"Autumn"
  return k.charAt(0).toUpperCase() + k.slice(1);
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

