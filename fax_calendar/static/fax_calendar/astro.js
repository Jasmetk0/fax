(function(exports){
  const core = window.woorldCore;
  const TROPICAL_YEAR = 428.5646875;

  function yearLength(y){
    return 428 + core.E(y);
  }

  function ordinalAtYearStart(y){
    let n = 1;
    for(let i=1;i<y;i++){
      n += yearLength(i);
    }
    return n;
  }

  function toOrdinal(y,m,d){
    const months = core.monthLengths(y);
    let n = 0;
    for(let i=1;i<m;i++) n += months[i-1];
    return n + d;
  }

  function fromOrdinal(y,doy){
    const months = core.monthLengths(y);
    let m = 1;
    while(doy>months[m-1]){
      doy -= months[m-1];
      m += 1;
    }
    return [y,m,doy];
  }

  function toGlobalOrdinal(y,m,d){
    return ordinalAtYearStart(y) + toOrdinal(y,m,d) - 1;
  }

  function fromGlobalOrdinal(ord){
    let y = 1;
    let start = 1;
    let len = yearLength(y);
    while(ord>start+len-1){
      start += len;
      y += 1;
      len = yearLength(y);
    }
    const doy = ord - start + 1;
    return fromOrdinal(y,doy);
  }

  function eventsForYear(y){
    const start = ordinalAtYearStart(y);
    const end = start + yearLength(y) - 1;
    const phases = {
      spring: 0.25*TROPICAL_YEAR,
      summer: 0.5*TROPICAL_YEAR,
      autumn: 0.75*TROPICAL_YEAR,
      winter: 1.0*TROPICAL_YEAR
    };
    const out = {springs:[], summers:[], autumns:[], winters:[]};
    for(const [name, phase] of Object.entries(phases)){
      const kStart = Math.floor((start-phase)/TROPICAL_YEAR)-1;
      const kEnd = Math.ceil((end-phase)/TROPICAL_YEAR)+1;
      for(let k=kStart;k<=kEnd;k++){
        const ord = Math.round(phase + k*TROPICAL_YEAR);
        if(ord>=start && ord<=end){
          const [yy,mm,dd] = fromGlobalOrdinal(ord);
          out[name+"s"].push({ord:ord,y:yy,m:mm,d:dd});
        }
      }
    }
    return out;
  }

  function seasonOf(y,doy){
    const ev = eventsForYear(y);
    const spring = ev.springs[0] ? toOrdinal(y,ev.springs[0].m, ev.springs[0].d) : null;
    const summer = ev.summers[0] ? toOrdinal(y,ev.summers[0].m, ev.summers[0].d) : null;
    const autumn = ev.autumns[0] ? toOrdinal(y,ev.autumns[0].m, ev.autumns[0].d) : null;
    const winters = ev.winters.map(w=>toOrdinal(y,w.m,w.d));
    if(winters.includes(doy)) return 'Winter II';
    if(spring && doy < spring) return 'Winter I';
    if(spring && (!summer || doy < summer) && doy>=spring) return 'Spring';
    if(summer && (!autumn || doy < autumn) && doy>=summer) return 'Summer';
    if(autumn && doy>=autumn && (!winters[0] || doy < winters[0])) return 'Autumn';
    return 'Winter I';
  }

  exports.TROPICAL_YEAR = TROPICAL_YEAR;
  exports.yearLength = yearLength;
  exports.ordinalAtYearStart = ordinalAtYearStart;
  exports.toOrdinal = toOrdinal;
  exports.fromOrdinal = fromOrdinal;
  exports.toGlobalOrdinal = toGlobalOrdinal;
  exports.fromGlobalOrdinal = fromGlobalOrdinal;
  exports.eventsForYear = eventsForYear;
  exports.seasonOf = seasonOf;
})(window.woorldAstro = window.woorldAstro || {});
