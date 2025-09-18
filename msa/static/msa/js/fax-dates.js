(function (global) {
  const FAX_MONTHS_IN_YEAR = 15;
  const FAX_META_CACHE = new Map();

  function monthFromFaxDateStr(value) {
    const parts = String(value ?? "").split("-");
    if (parts.length < 2) {
      throw new Error(`Invalid FAX date string: ${value}`);
    }
    return parseInt(parts[1], 10);
  }

  function parseFaxDate(iso) {
    const parts = String(iso ?? "")
      .trim()
      .split("-")
      .slice(0, 3)
      .map((value) => Number.parseInt(value, 10));
    const [y, m, d] = parts;
    if (!Number.isFinite(y) || !Number.isFinite(m) || !Number.isFinite(d)) {
      throw new Error(`Invalid FAX date: ${iso}`);
    }
    if (m < 1 || m > FAX_MONTHS_IN_YEAR) {
      throw new Error(`Invalid FAX month: ${iso}`);
    }
    if (d < 1) {
      throw new Error(`Invalid FAX day: ${iso}`);
    }
    return { y, m, d };
  }

  function formatFaxDate({ y, m, d }) {
    const year = Number.parseInt(y, 10);
    const month = Number.parseInt(m, 10);
    const day = Number.parseInt(d, 10);
    if (!Number.isFinite(year) || !Number.isFinite(month) || !Number.isFinite(day)) {
      throw new Error("Invalid FAX date parts");
    }
    const mm = String(month).padStart(2, "0");
    const dd = String(day).padStart(2, "0");
    return `${year}-${mm}-${dd}`;
  }

  function normalizeFaxDate(value) {
    try {
      return formatFaxDate(parseFaxDate(value));
    } catch (err) {
      return null;
    }
  }

  async function getFaxYearMeta(year) {
    const numericYear = Number.parseInt(year, 10);
    const key = Number.isFinite(numericYear) ? numericYear : year;
    if (FAX_META_CACHE.has(key)) {
      return FAX_META_CACHE.get(key);
    }

    let monthLengths = new Map();

    try {
      const resp = await fetch(`/api/fax_calendar/year/${key}/meta`, {
        headers: { Accept: "application/json" },
      });
      if (resp.ok) {
        const json = await resp.json();
        const raw = json?.month_lengths ?? json?.months ?? null;
        const map = new Map();
        if (Array.isArray(raw)) {
          raw.forEach((value, index) => {
            const monthIndex = index + 1;
            const length = Number.parseInt(value, 10);
            if (
              Number.isFinite(length) &&
              length > 0 &&
              monthIndex >= 1 &&
              monthIndex <= FAX_MONTHS_IN_YEAR
            ) {
              map.set(monthIndex, length);
            }
          });
        } else if (raw && typeof raw === "object") {
          Object.entries(raw).forEach(([monthKey, value]) => {
            const monthIndex = Number.parseInt(monthKey, 10);
            const length = Number.parseInt(value, 10);
            if (
              Number.isFinite(monthIndex) &&
              Number.isFinite(length) &&
              monthIndex >= 1 &&
              monthIndex <= FAX_MONTHS_IN_YEAR &&
              length > 0
            ) {
              map.set(monthIndex, length);
            }
          });
        }
        if (map.size) {
          monthLengths = map;
        }
      }
    } catch (err) {
      // ignore errors; fall back to empty month lengths
    }

    const meta = { monthLengths };
    FAX_META_CACHE.set(key, meta);
    return meta;
  }

  function compareFaxDates(a, b) {
    if (a.y !== b.y) return a.y - b.y;
    if (a.m !== b.m) return a.m - b.m;
    return a.d - b.d;
  }

  function nextFaxDay(current) {
    const meta = FAX_META_CACHE.get(current.y);
    if (!meta || !(meta.monthLengths instanceof Map) || meta.monthLengths.size === 0) {
      return null;
    }

    const monthLen = meta.monthLengths.get(current.m);
    if (!Number.isFinite(monthLen) || monthLen <= 0 || current.d > monthLen) {
      return null;
    }

    let y = current.y;
    let m = current.m;
    let d = current.d + 1;

    if (d > monthLen) {
      d = 1;
      m += 1;
      if (m > FAX_MONTHS_IN_YEAR) {
        y += 1;
        m = 1;
      }
      const targetMeta = FAX_META_CACHE.get(y);
      if (!targetMeta || !(targetMeta.monthLengths instanceof Map) || targetMeta.monthLengths.size === 0) {
        return null;
      }
      const nextMonthLen = targetMeta.monthLengths.get(m);
      if (!Number.isFinite(nextMonthLen) || nextMonthLen <= 0) {
        return null;
      }
    }

    return { y, m, d };
  }

  function enumerateFaxDays(startISO, endISO, maxSteps = 20000) {
    let start;
    let end;
    try {
      start = parseFaxDate(startISO);
      end = parseFaxDate(endISO);
    } catch (err) {
      return [];
    }

    if (compareFaxDates(start, end) > 0) {
      return [];
    }

    const startMeta = FAX_META_CACHE.get(start.y);
    const startLen = startMeta?.monthLengths?.get(start.m);
    if (!Number.isFinite(startLen) || startLen <= 0 || start.d > startLen) {
      return [];
    }

    const days = [];
    let current = start;
    let steps = 0;
    while (steps < maxSteps) {
      steps += 1;
      days.push(formatFaxDate(current));
      if (current.y === end.y && current.m === end.m && current.d === end.d) {
        return days;
      }
      const next = nextFaxDay(current);
      if (!next) {
        break;
      }
      current = next;
    }

    return [];
  }

  global.MSAFaxDates = Object.assign({}, global.MSAFaxDates || {}, {
    FAX_MONTHS_IN_YEAR,
    monthFromFaxDateStr,
    parseFaxDate,
    formatFaxDate,
    normalizeFaxDate,
    getFaxYearMeta,
    compareFaxDates,
    nextFaxDay,
    enumerateFaxDays,
  });
})(window);
