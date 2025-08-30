(function (exports) {
  const PROTO_V3 = new Set([689, 1067, 1433, 1657]);
  const PROMOTED_START = 303;

  function promoted(y) {
    return y >= PROMOTED_START && (y - PROMOTED_START) % 16 === 0;
  }

  function leapBase(y) {
    return y % 2 === 0 || promoted(y);
  }

  function E(y) {
    let extra = leapBase(y) ? 1 : 0;
    if (PROTO_V3.has(y)) extra += 1;
    if (y === 297) extra += 19;
    return extra;
  }

  function monthLengths(y) {
    const e = E(y);
    const out = [];
    for (let m = 1; m <= 15; m++) {
      if (m === 1) out.push(29 + e);
      else out.push(m % 2 === 1 ? 29 : 28);
    }
    return out;
  }

  function anchors(y) {
    const e = E(y);
    return {
      vernal: 107 + e,
      solstice_s: 214 + e,
      autumnal: 321 + e,
      solstice_w: 428 + e,
    };
  }

  exports.PROTO_V3 = Array.from(PROTO_V3);
  exports.promoted = promoted;
  exports.leapBase = leapBase;
  exports.E = E;
  exports.monthLengths = monthLengths;
  exports.anchors = anchors;
})(window.woorldCore = window.woorldCore || {});
