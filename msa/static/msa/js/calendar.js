(function () {
  const root = document.getElementById("cal-root");
  if (!root) return;
  const loading = document.getElementById("cal-loading");
  const emptyEl = document.getElementById("cal-empty");
  const listEl = document.getElementById("cal-list");
  const selMonth = document.getElementById("month-filter");
  const selTour = document.getElementById("cal-tour");
  const selCat = document.getElementById("cal-cat");
  const btnToday = document.getElementById("cal-today");
  const btnModeMonths = document.getElementById("mode-months");
  const btnModeDays = document.getElementById("mode-days");

  const params = new URLSearchParams(location.search);
  const season =
    params.get("season") || root.getAttribute("data-season") || "";

  const API = "/api/msa/tournaments";
  const FAX_MONTHS_IN_YEAR = 15;
  const FAX_META_CACHE = new Map(); // year -> { monthLengths: Map<number, number> }
  const MODE_KEY = "msa_calendar_mode";
  const initFilters = {
    month: getQS().get("month") || "",
    tour: getQS().get("tour") || "",
    cat: getQS().get("cat") || "",
  };

  let rows = [];
  let view = [];
  let monthSequence = [];
  let seasonMeta = null;
  let mode = "months";

  const BADGE = {
    Diamond: "bg-indigo-600/10 text-indigo-700 border-indigo-200",
    Emerald: "bg-emerald-600/10 text-emerald-700 border-emerald-200",
    Platinum: "bg-slate-700/10 text-slate-800 border-slate-300",
    Gold: "bg-amber-500/10 text-amber-700 border-amber-200",
    Silver: "bg-gray-500/10 text-gray-700 border-gray-300",
    Bronze: "bg-orange-500/10 text-orange-700 border-orange-200",
  };

  const TOUR_BADGE = {
    "World Tour": "bg-blue-600/10 text-blue-700 border-blue-200",
    "Elite Tour": "bg-purple-600/10 text-purple-700 border-purple-200",
    "Challenger Tour": "bg-teal-600/10 text-teal-700 border-teal-200",
    "Development Tour": "bg-lime-600/10 text-lime-700 border-lime-200",
  };

  function getQueryParam(name) {
    const p = new URLSearchParams(location.search);
    return p.get(name);
  }

  function setQueryParam(name, value) {
    const p = new URLSearchParams(location.search);
    if (value == null || value === "") {
      p.delete(name);
    } else {
      p.set(name, value);
    }
    const qs = p.toString();
    const suffix = qs ? `?${qs}` : "";
    history.replaceState(null, "", `${location.pathname}${suffix}`);
  }

  function getQS() {
    return new URLSearchParams(location.search);
  }

  function saveFilterToQS(key, value) {
    const p = getQS();
    if (!value) {
      p.delete(key);
    } else {
      p.set(key, value);
    }
    const qs = p.toString();
    history.replaceState(
      null,
      "",
      `${location.pathname}${qs ? `?${qs}` : ""}`,
    );
  }

  function loadMode() {
    mode = getQueryParam("mode") || localStorage.getItem(MODE_KEY) || "months";
    if (mode !== "days") mode = "months";
  }

  function saveMode() {
    localStorage.setItem(MODE_KEY, mode);
    setQueryParam("mode", mode); // zapisuj jen při explicitní změně (voláme z click handlerů)
  }

  function updateModeButtons() {
    const selMonths = mode === "months";
    btnModeMonths?.setAttribute("aria-selected", selMonths ? "true" : "false");
    btnModeDays?.setAttribute("aria-selected", selMonths ? "false" : "true");
    btnModeMonths?.classList.toggle("bg-slate-100", selMonths);
    btnModeDays?.classList.toggle("bg-slate-100", !selMonths);
    const monthWrap = selMonth?.closest("label");
    if (monthWrap) {
      monthWrap.classList.toggle("hidden", mode === "days");
    }
  }

  function monthFromFaxDateStr(value) {
    const parts = String(value ?? "").split("-");
    if (parts.length < 2) {
      throw new Error(`Invalid FAX date string: ${value}`);
    }
    return parseInt(parts[1], 10);
  }

  function buildMonthOptionsFromSequence(seq) {
    if (!selMonth) return;
    selMonth.innerHTML = "";

    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "Vše";
    selMonth.appendChild(optAll);

    const seen = new Set();
    seq.forEach((value) => {
      const numeric = Number.parseInt(value, 10);
      if (Number.isNaN(numeric) || seen.has(numeric)) {
        return;
      }
      seen.add(numeric);
      const opt = document.createElement("option");
      opt.value = String(numeric);
      opt.textContent = String(numeric);
      selMonth.appendChild(opt);
    });
  }

  function formatYMD(s) {
    const parts = String(s || "").split("-");
    if (parts.length < 3) return s || "";
    const [y, m, d] = parts.map((x) => parseInt(x, 10));
    if (!y || !m || !d) return s || "";
    return `${d}.${m}.${y}`;
  }

  function ymd(d) {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, "0");
    const day = String(d.getDate()).padStart(2, "0");
    return `${year}-${month}-${day}`;
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
      // Silently ignore errors; fall back to empty month lengths.
    }

    const meta = { monthLengths };
    FAX_META_CACHE.set(key, meta);
    return meta;
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

  function compareFaxDates(a, b) {
    if (a.y !== b.y) return a.y - b.y;
    if (a.m !== b.m) return a.m - b.m;
    return a.d - b.d;
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

  function showSeasonRange() {
    const el = document.getElementById("season-range");
    if (!el) return;
    if (seasonMeta?.start_date && seasonMeta?.end_date) {
      el.textContent = `${formatYMD(seasonMeta.start_date)} – ${formatYMD(
        seasonMeta.end_date,
      )}`;
      el.classList.remove("hidden");
    }
  }

  function buildTourOptionsFromRows() {
    if (!selTour) return;
    const set = new Set(
      rows
        .map((r) => (r.tour || "").trim())
        .filter((value) => value.length > 0),
    );
    const options = Array.from(set).sort();
    selTour
      .querySelectorAll("option:not([value=''])")
      .forEach((opt) => opt.remove());
    options.forEach((t) => {
      const opt = document.createElement("option");
      opt.value = t;
      opt.textContent = t;
      selTour.appendChild(opt);
    });
  }

  function buildCategoryOptionsFromRows() {
    if (!selCat) return;
    const set = new Set(
      rows
        .map((r) => (r.category || "").trim())
        .filter((value) => value.length > 0),
    );
    const options = Array.from(set).sort((a, b) =>
      String(a).localeCompare(String(b)),
    );
    selCat
      .querySelectorAll("option:not([value=''])")
      .forEach((opt) => opt.remove());
    options.forEach((v) => {
      const opt = document.createElement("option");
      opt.value = v;
      opt.textContent = v;
      selCat.appendChild(opt);
    });
  }

  function getRowFaxMonth(row) {
    const source = row.start_date || "";
    if (!source) return null;
    try {
      return monthFromFaxDateStr(source);
    } catch (err) {
      return null;
    }
  }

  function compareRows(a, b) {
    const aKey = String(a.start_date || a.end_date || "");
    const bKey = String(b.start_date || b.end_date || "");
    const cmp = aKey.localeCompare(bKey);
    if (cmp !== 0) return cmp;
    return String(a.name || "").localeCompare(String(b.name || ""));
  }

  function renderMonths(filtered) {
    const groups = new Map();
    for (const row of filtered) {
      const faxMonth = getRowFaxMonth(row);
      const key = faxMonth === null ? "Unknown" : String(faxMonth);
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key).push(row);
    }

    const orderedKeys = [];
    const seenKeys = new Set();

    if (monthSequence.length) {
      for (const month of monthSequence) {
        const key = String(month);
        if (!seenKeys.has(key)) {
          orderedKeys.push(key);
          seenKeys.add(key);
        }
      }
    }

    for (const key of groups.keys()) {
      if (!seenKeys.has(key)) {
        orderedKeys.push(key);
        seenKeys.add(key);
      }
    }

    if (!orderedKeys.length && groups.size) {
      for (const key of groups.keys()) {
        orderedKeys.push(key);
      }
    }

    if (!orderedKeys.length) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    const html = orderedKeys
      .map((key) => {
        const data = (groups.get(key) || []).slice().sort(compareRows);
        const first = data[0];
        const base = first ? first.start_date || first.end_date || "" : "";
        const fallbackYear = base ? String(base).split("-")[0] : "";
        const isUnknown = key === "Unknown";
        let title;

        if (isUnknown) {
          title = "Neznámý měsíc";
        } else {
          let titleYearValue = null;
          if (seasonMeta?.start_date && seasonMeta?.end_date) {
            const startParts = String(seasonMeta.start_date).split("-");
            const endParts = String(seasonMeta.end_date).split("-");
            if (startParts.length >= 2 && endParts.length >= 1) {
              const sm = Number.parseInt(startParts[1], 10);
              const sy = Number.parseInt(startParts[0], 10);
              const ey = Number.parseInt(endParts[0], 10);
              const numericKey = Number.parseInt(key, 10);
              if (
                !Number.isNaN(sm) &&
                !Number.isNaN(sy) &&
                !Number.isNaN(ey) &&
                !Number.isNaN(numericKey)
              ) {
                titleYearValue = numericKey >= sm ? sy : ey;
              }
            }
          }

          title =
            titleYearValue !== null
              ? `Měsíc ${key} · ${titleYearValue}`
              : `Měsíc ${key}${fallbackYear ? ` · ${fallbackYear}` : ""}`;
        }

        const items = data
          .map((row) => {
            const badge =
              BADGE[row.category] || "bg-slate-600/10 text-slate-800 border-slate-300";
            const tourBadge =
              TOUR_BADGE[row.tour] || "bg-slate-600/10 text-slate-800 border-slate-300";
            const when = [row.start_date, row.end_date].filter(Boolean).join(" – ");
            const place = [row.city, row.country].filter(Boolean).join(", ");
            const url = row.url || (row.id ? `/msa/tournament/${row.id}/` : "#");
            return `
          <a href="${url}" class="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs ${badge}">
                  ${row.category || "—"}
                </span>
                ${
                  row.tour
                    ? `
                <span class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs ${tourBadge}">
                  ${row.tour}
                </span>`
                    : ""
                }
                <span class="font-medium truncate">${row.name || "Tournament"}</span>
              </div>
              <div class="text-xs text-slate-500 mt-0.5">
                ${when || ""} ${place ? "• " + place : ""}
              </div>
            </div>
            <svg aria-hidden="true" class="w-4 h-4 text-slate-400"><path d="M5 3l6 5-6 5" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </a>
        `;
          })
          .join("");

        const emptyNote = data.length
          ? ""
          : `<div class="px-4 py-3 text-xs text-slate-400">Žádné turnaje v tomto měsíci.</div>`;

        const dataAttr = isUnknown ? "unknown" : key;

        return `
        <div class="bg-white">
          <div class="sticky top-[4rem] z-10 bg-white/90 backdrop-blur px-4 py-2 border-b scroll-mt-24" data-fax-month="${dataAttr}">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-600">${title}</h2>
          </div>
          <div class="divide-y pt-3">
            ${items || ""}${emptyNote}
          </div>
        </div>
      `;
      })
      .join("");

    emptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");
    listEl.classList.add("divide-y");
    listEl.innerHTML = html;
  }

  function renderDays(filtered, { hasMonthFilter, selectedMonth }) {
    if (!seasonMeta?.start_date || !seasonMeta?.end_date) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    const allDays = enumerateFaxDays(seasonMeta.start_date, seasonMeta.end_date);
    if (!allDays.length) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    let visibleDays = allDays;
    if (hasMonthFilter) {
      const matches = allDays.filter((d) => {
        try {
          return monthFromFaxDateStr(d) === selectedMonth;
        } catch (err) {
          return false;
        }
      });
      if (matches.length) {
        visibleDays = matches;
      }
    }

    if (!visibleDays.length) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    const visibleStartIndex = allDays.indexOf(visibleDays[0]);
    const visibleEndIndex = allDays.indexOf(visibleDays[visibleDays.length - 1]);
    if (visibleStartIndex === -1 || visibleEndIndex === -1) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    const intervals = filtered
      .map((t) => {
        const startIso = normalizeFaxDate(t.start_date);
        if (!startIso) {
          return null;
        }
        const startIdx = allDays.indexOf(startIso);
        if (startIdx === -1) {
          return null;
        }
        const endIso = normalizeFaxDate(t.end_date || t.start_date);
        let endIdx = endIso ? allDays.indexOf(endIso) : -1;
        if (endIdx === -1) {
          endIdx = startIdx;
        }
        const start = startIdx;
        const end = Math.max(start, endIdx);
        const clippedStart = Math.max(start, visibleStartIndex);
        const clippedEnd = Math.min(end, visibleEndIndex);
        if (clippedStart > clippedEnd) {
          return null;
        }
        return {
          t,
          s: clippedStart - visibleStartIndex,
          e: clippedEnd - visibleStartIndex,
        };
      })
      .filter(Boolean);

    const DAY_H = 22;
    const GAP_X = 8;
    const lanes = [];
    function placeLane(s, e) {
      for (let i = 0; i < lanes.length; i += 1) {
        if (lanes[i] < s) {
          lanes[i] = e;
          return i;
        }
      }
      lanes.push(e);
      return lanes.length - 1;
    }

    const placed = intervals
      .sort((a, b) => a.s - b.s || a.e - b.e)
      .map((interval) => ({
        ...interval,
        lane: placeLane(interval.s, interval.e),
      }));
    const laneCount = lanes.length;

    const dayCol = visibleDays
      .map((d) => {
        let label = formatYMD(d);
        try {
          const parsed = parseFaxDate(d);
          const dd = String(parsed.d).padStart(2, "0");
          const mm = String(parsed.m).padStart(2, "0");
          label = `${dd}.${mm}.${parsed.y}`;
        } catch (err) {
          // fall back to original label
        }
        return `<div data-day="${d}" class="h-[${DAY_H}px] border-b text-xs text-slate-500 px-3 flex items-center">${label}</div>`;
      })
      .join("");

    const containerH = visibleDays.length * DAY_H;
    const laneW = Math.max(
      140,
      Math.floor((root.clientWidth - 220) / Math.max(1, laneCount)),
    );
    const minWidth = laneCount ? laneCount * (laneW + GAP_X) : laneW;

    const bars = placed
      .map(({ t, s, e, lane }) => {
        const top = s * DAY_H + 2;
        const height = (e - s + 1) * DAY_H - 4;
        const left = lane * (laneW + GAP_X);
        const badge =
          BADGE[t.category] || "bg-slate-600/10 text-slate-800 border-slate-300";
        const tourBadge =
          TOUR_BADGE[t.tour] || "bg-slate-600/10 text-slate-800 border-slate-300";
        const url = t.url || (t.id ? `/msa/tournament/${t.id}/` : "#");
        const endLabel = t.end_date ? ` – ${t.end_date}` : "";
        return `
    <a href="${url}" class="absolute rounded-md border shadow-sm overflow-hidden"
       style="top:${top}px; left:${left}px; height:${height}px; width:${laneW}px; background: white;">
      <div class="px-2 py-1 text-[11px] border-b flex items-center gap-1">
        <span class="inline-flex items-center rounded border px-1 ${badge}">${t.category || "—"}</span>
        ${
          t.tour
            ? `<span class="inline-flex items-center rounded border px-1 ${tourBadge}">${t.tour}</span>`
            : ""
        }
        <span class="font-medium truncate">${t.name || "Tournament"}</span>
      </div>
      <div class="px-2 py-1 text-[11px] text-slate-500">${t.start_date}${endLabel}</div>
    </a>`;
      })
      .join("");

    emptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");
    listEl.classList.remove("divide-y");
    listEl.innerHTML = `
  <div class="grid grid-cols-[200px_1fr]">
    <div class="border-r" style="height:${containerH}px; overflow:hidden">${dayCol}</div>
    <div class="relative" style="height:${containerH}px; overflow:auto">
      <div class="relative" style="height:${containerH}px; min-width:${minWidth}px">
        ${bars}
      </div>
    </div>
  </div>
`;
  }

  function render() {
    const rawValue = selMonth ? selMonth.value : "";
    const selectedMonth = rawValue ? Number.parseInt(rawValue, 10) : NaN;
    const hasMonthFilter = !Number.isNaN(selectedMonth);
    const selectedCategory = (selCat?.value || "").trim();
    const selectedTour = (selTour?.value || "").trim();

    const filtered = rows
      .filter((row) => {
        const faxMonth = getRowFaxMonth(row);
        const okMonth = hasMonthFilter ? faxMonth === selectedMonth : true;
        const okCategory = selectedCategory ? row.category === selectedCategory : true;
        const okTour = selectedTour ? row.tour === selectedTour : true;
        return okMonth && okCategory && okTour;
      })
      .sort(compareRows);

    view = filtered;

    if (mode === "days") {
      renderDays(filtered, { hasMonthFilter, selectedMonth });
      return;
    }

    renderMonths(filtered);
  }

  async function fetchSeason(seasonId) {
    const url = `/api/msa/season?season=${encodeURIComponent(seasonId)}`;
    const resp = await fetch(url);
    if (!resp.ok) {
      return null;
    }
    return resp.json();
  }

  async function prepareSeason() {
    let sequence = [];
    seasonMeta = null;
    if (season) {
      try {
        const meta = await fetchSeason(season);
        if (meta && typeof meta === "object") {
          seasonMeta = {
            start_date: meta.start_date || null,
            end_date: meta.end_date || null,
          };
          if (seasonMeta.start_date && seasonMeta.end_date) {
            try {
              const start = parseFaxDate(seasonMeta.start_date);
              const end = parseFaxDate(seasonMeta.end_date);
              const startYear = Math.min(start.y, end.y);
              const endYear = Math.max(start.y, end.y);
              for (let year = startYear; year <= endYear; year += 1) {
                await getFaxYearMeta(year);
              }
            } catch (err) {
              // Ignore parse errors; missing metadata will fall back to empty view.
            }
          }
          if (Array.isArray(meta.month_sequence)) {
            sequence = meta.month_sequence
              .map((n) => Number.parseInt(n, 10))
              .filter((n) => !Number.isNaN(n));
          }
        }
      } catch (err) {
        console.error(err);
      }
    }

    if (!sequence.length) {
      sequence = Array.from({ length: FAX_MONTHS_IN_YEAR }, (_, idx) => idx + 1);
    }

    monthSequence = sequence;
    buildMonthOptionsFromSequence(monthSequence);
    showSeasonRange();
  }

  async function loadTournaments() {
    const q = new URLSearchParams();
    if (season) q.set("season", season);
    const url = q.toString() ? `${API}?${q}` : API;
    try {
      const r = await fetch(url, { headers: { Accept: "application/json" } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      rows = (data.tournaments || []).map((t) => {
        const nameRaw = String(t.name || t.title || "").trim();
        const city = String(t.city || "").trim();
        const country = String(t.country || "").trim();
        const category = String(t.category || t.tier || "").trim();
        const tour = String(t.tour || "").trim();
        const start = String(t.start_date || t.start || "").trim();
        const end = String(t.end_date || t.end || "").trim();
        const url = String(t.url || "").trim();
        return {
          id: t.id,
          name: nameRaw || "Tournament",
          city,
          country,
          category,
          tour,
          start_date: start,
          end_date: end,
          url,
        };
      });
      buildTourOptionsFromRows();
      buildCategoryOptionsFromRows();
      loading.style.display = "none";
    } catch (err) {
      console.error(err);
      loading.textContent = "Failed to load tournaments.";
    }
  }

  function initEvents() {
    selMonth &&
      selMonth.addEventListener("change", () => {
        saveFilterToQS("month", selMonth.value);
        render();
      });
    selTour &&
      selTour.addEventListener("change", () => {
        saveFilterToQS("tour", selTour.value);
        render();
      });
    selCat &&
      selCat.addEventListener("change", () => {
        saveFilterToQS("cat", selCat.value);
        render();
      });
    btnModeMonths &&
      btnModeMonths.addEventListener("click", () => {
        if (mode !== "months") {
          mode = "months";
          saveMode();
          updateModeButtons();
          render();
        }
      });
    btnModeDays &&
      btnModeDays.addEventListener("click", () => {
        if (mode !== "days") {
          mode = "days";
          saveMode();
          updateModeButtons();
          render();
        }
      });
    btnToday &&
      btnToday.addEventListener("click", () => {
        if (mode === "days") {
          const iso = ymd(new Date());
          const targetDay =
            listEl.querySelector(`[data-day="${iso}"]`) ||
            listEl.querySelector("[data-day]");
          targetDay?.scrollIntoView({ behavior: "smooth", block: "center" });
          return;
        }

        const headings = Array.from(
          listEl.querySelectorAll("[data-fax-month]"),
        );
        if (!headings.length) return;

        const todayFaxMonth = (() => {
          try {
            return monthFromFaxDateStr(ymd(new Date()));
          } catch (err) {
            return null;
          }
        })();

        const keys = monthSequence.map((n) => String(n));
        let targetKey = null;

        if (todayFaxMonth != null) {
          const todayKey = String(todayFaxMonth);
          if (keys.includes(todayKey)) {
            targetKey = todayKey;
          } else {
            const idx = keys.findIndex(
              (k) => parseInt(k, 10) >= todayFaxMonth,
            );
            targetKey = idx >= 0 ? keys[idx] : keys[0] || null;
          }
        } else {
          targetKey = keys[0] || null;
        }

        const filteredKey = selMonth?.value || "";
        if (filteredKey && keys.includes(filteredKey)) {
          targetKey = filteredKey;
        }

        const el =
          headings.find((h) => h.dataset.faxMonth === String(targetKey)) ||
          headings[0];
        el?.scrollIntoView({ behavior: "smooth", block: "start" });
      });
  }

  async function init() {
    loadMode();
    updateModeButtons();
    await prepareSeason();
    if (selMonth && initFilters.month) {
      const has = Array.from(selMonth.options).some(
        (o) => o.value === initFilters.month,
      );
      if (has) {
        selMonth.value = initFilters.month;
      }
    }
    await loadTournaments();
    if (selTour && initFilters.tour) {
      const has = Array.from(selTour.options).some(
        (o) => o.value === initFilters.tour,
      );
      if (has) {
        selTour.value = initFilters.tour;
      }
    }
    if (selCat && initFilters.cat) {
      const has = Array.from(selCat.options).some(
        (o) => o.value === initFilters.cat,
      );
      if (has) {
        selCat.value = initFilters.cat;
      }
    }
    initEvents();
    render(); // první render až po navázání handlerů
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
