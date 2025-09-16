(function () {
  const root = document.getElementById("cal-root");
  if (!root) return;
  const loading = document.getElementById("cal-loading");
  const emptyEl = document.getElementById("cal-empty");
  const listEl = document.getElementById("cal-list");
  const selMonth = document.getElementById("month-filter");
  const selCat = document.getElementById("cal-cat");
  const btnToday = document.getElementById("cal-today");

  const params = new URLSearchParams(location.search);
  const season = params.get("season") || "";

  const API = "/api/msa/tournaments";
  const FAX_MONTHS_IN_YEAR = 15;

  let rows = [];
  let view = [];
  let monthSequence = [];
  let seasonMeta = null;

  const BADGE = {
    Diamond: "bg-indigo-600/10 text-indigo-700 border-indigo-200",
    Emerald: "bg-emerald-600/10 text-emerald-700 border-emerald-200",
    Platinum: "bg-slate-700/10 text-slate-800 border-slate-300",
    Gold: "bg-amber-500/10 text-amber-700 border-amber-200",
    Silver: "bg-gray-500/10 text-gray-700 border-gray-300",
    Bronze: "bg-orange-500/10 text-orange-700 border-orange-200",
  };

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

  function getRowFaxMonth(row) {
    const source = row.start_date || row.end_date || "";
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

  function render() {
    const rawValue = selMonth ? selMonth.value : "";
    const selectedMonth = rawValue ? Number.parseInt(rawValue, 10) : NaN;
    const hasMonthFilter = !Number.isNaN(selectedMonth);
    const selectedCategory = (selCat?.value || "").trim();

    const filtered = rows
      .filter((row) => {
        const faxMonth = getRowFaxMonth(row);
        const okMonth = hasMonthFilter ? faxMonth === selectedMonth : true;
        const okCategory = selectedCategory ? row.category === selectedCategory : true;
        return okMonth && okCategory;
      })
      .sort(compareRows);

    view = filtered;

    if (!view.length) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }

    emptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");

    const groups = new Map();
    for (const row of view) {
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
        if (!seenKeys.has(key) && groups.has(key)) {
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

    const html = orderedKeys
      .map((key) => {
        const data = groups.get(key) || [];
        data.sort(compareRows);

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
              const sm = parseInt(startParts[1], 10);
              const sy = parseInt(startParts[0], 10);
              const ey = parseInt(endParts[0], 10);
              const numericKey = Number(key);
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

        const dataAttr = isUnknown ? "unknown" : key;

        return `
        <div class="bg-white">
          <div class="sticky top-[4rem] z-10 bg-white/90 backdrop-blur px-4 py-2 border-b" data-fax-month="${dataAttr}">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-600">${title}</h2>
          </div>
          <div class="divide-y">
            ${items}
          </div>
        </div>
      `;
      })
      .join("");

    listEl.innerHTML = html;
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
  }

  async function loadTournaments() {
    const q = new URLSearchParams();
    if (season) q.set("season", season);
    const url = q.toString() ? `${API}?${q}` : API;
    try {
      const r = await fetch(url, { headers: { Accept: "application/json" } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      rows = (data.tournaments || []).map((t) => ({
        id: t.id,
        name: t.name || t.title || "Tournament",
        city: t.city || "",
        country: t.country || "",
        category: t.category || t.tier || "",
        start_date: t.start_date || t.start || "",
        end_date: t.end_date || t.end || "",
        url: t.url || "",
      }));
      loading.style.display = "none";
      render();
    } catch (err) {
      console.error(err);
      loading.textContent = "Failed to load tournaments.";
    }
  }

  function initEvents() {
    selMonth && selMonth.addEventListener("change", render);
    selCat && selCat.addEventListener("change", render);
    btnToday &&
      btnToday.addEventListener("click", () => {
        const headings = Array.from(listEl.querySelectorAll("[data-fax-month]"));
        if (!headings.length) return;

        const selected = selMonth?.value;
        let target = selected || null;

        if (!target && monthSequence.length) {
          target = String(monthSequence[0]);
        }

        let el = null;
        if (target) {
          el = headings.find((h) => h.dataset.faxMonth === String(target));
        }

        if (!el) {
          el = headings[0];
        }

        if (el) {
          el.scrollIntoView({ behavior: "smooth", block: "start" });
        }
      });
  }

  async function init() {
    await prepareSeason();
    await loadTournaments();
    initEvents();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
