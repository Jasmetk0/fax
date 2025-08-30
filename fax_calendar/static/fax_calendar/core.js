const PROTO_V3_SET = new Set([689, 1067, 1433, 1657]);
const PROMOTED_START = 303;

export function promoted(y) {
  return y >= PROMOTED_START && (y - PROMOTED_START) % 16 === 0;
}

export function leapBase(y) {
  return y % 2 === 0 || promoted(y);
}

export function E(y) {
  let extra = leapBase(y) ? 1 : 0;
  if (PROTO_V3_SET.has(y)) extra += 1;
  if (y === 297) extra += 19;
  return extra;
}

export function monthLengths(y) {
  const e = E(y);
  const out = [];
  for (let m = 1; m <= 15; m++) {
    if (m === 1) out.push(29 + e);
    else out.push(m % 2 === 1 ? 29 : 28);
  }
  return out;
}

export function yearLength(y) {
  return 428 + E(y);
}

export function toOrdinal(y, m, d) {
  const months = monthLengths(y);
  let n = d;
  for (let i = 1; i < m; i++) n += months[i - 1];
  return n;
}

export function fromOrdinal(y, doy) {
  const months = monthLengths(y);
  let m = 1;
  while (doy > months[m - 1]) {
    doy -= months[m - 1];
    m += 1;
  }
  return [y, m, doy];
}

export function weekday(y, m, d) {
  let total = 0;
  for (let year = 1; year < y; year++) {
    total += yearLength(year);
  }
  total += toOrdinal(y, m, d) - 1;
  return total % 7;
}

export function anchors(y) {
  const e = E(y);
  return {
    vernal: 107 + e,
    solstice_s: 214 + e,
    autumnal: 321 + e,
    solstice_w: 428 + e,
  };
}

export const PROTO_V3 = Array.from(PROTO_V3_SET);

if (typeof window !== "undefined") {
  window.woorldCore = {
    PROTO_V3,
    promoted,
    leapBase,
    E,
    monthLengths,
    yearLength,
    toOrdinal,
    fromOrdinal,
    weekday,
    anchors,
  };
}

