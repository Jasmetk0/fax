(function () {
  const root = document.getElementById("cal-root");
  if (!root) return;
  const loading = document.getElementById("cal-loading");
  const emptyEl  = document.getElementById("cal-empty");
  const listEl   = document.getElementById("cal-list");
  const selMonth = document.getElementById("cal-month");
  const selCat   = document.getElementById("cal-cat");
  const btnToday = document.getElementById("cal-today");

  // Season id je v URL dotazu ?season=<id>
  const params = new URLSearchParams(location.search);
  const season = params.get("season") || "";

  const API = "/api/msa/tournaments";
  let rows = [];
  let view = [];

  const BADGE = {
    Diamond: "bg-indigo-600/10 text-indigo-700 border-indigo-200",
    Emerald: "bg-emerald-600/10 text-emerald-700 border-emerald-200",
    Platinum: "bg-slate-700/10 text-slate-800 border-slate-300",
    Gold: "bg-amber-500/10 text-amber-700 border-amber-200",
    Silver: "bg-gray-500/10 text-gray-700 border-gray-300",
    Bronze: "bg-orange-500/10 text-orange-700 border-orange-200",
  };

  function toDate(s) {
    // očekává se YYYY-MM-DD; fallbacky neházejí chybu
    const d = new Date(s || "");
    return isNaN(d.getTime()) ? null : d;
  }

  function monthKey(d) {
    return d ? `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,"0")}` : "Unknown";
  }
  function monthLabel(d) {
    return d ? d.toLocaleString(undefined, { month: "long", year: "numeric" }) : "Unknown";
  }

  function render() {
    const m = Number(selMonth?.value || "") || null;
    const cat = (selCat?.value || "").trim();
    const filtered = rows.filter(r => {
      const d = toDate(r.start_date) || toDate(r.end_date);
      const okM = m ? (d && (d.getMonth()+1) === m) : true;
      const okC = cat ? (r.category === cat) : true;
      return okM && okC;
    }).sort((a,b) => {
      const ad = toDate(a.start_date) || toDate(a.end_date);
      const bd = toDate(b.start_date) || toDate(b.end_date);
      return (ad?.getTime() || 0) - (bd?.getTime() || 0);
    });
    view = filtered;

    if (!view.length) {
      listEl.classList.add("hidden");
      emptyEl.classList.remove("hidden");
      return;
    }
    emptyEl.classList.add("hidden");
    listEl.classList.remove("hidden");

    // group by month
    const groups = new Map();
    for (const r of view) {
      const d = toDate(r.start_date) || toDate(r.end_date);
      const k = monthKey(d);
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(r);
    }
    const ordered = Array.from(groups.entries()).sort(([a],[b]) => a.localeCompare(b));

    const html = ordered.map(([k, arr]) => {
      const d = toDate(arr[0]?.start_date) || toDate(arr[0]?.end_date);
      const title = monthLabel(d);
      const items = arr.map(r => {
        const badge = BADGE[r.category] || "bg-slate-600/10 text-slate-800 border-slate-300";
        const when = [r.start_date, r.end_date].filter(Boolean).join(" – ");
        const place = [r.city, r.country].filter(Boolean).join(", ");
        const url = r.url || (r.id ? `/msa/tournament/${r.id}/` : "#");
        return `
          <a href="${url}" class="flex items-center justify-between gap-4 px-4 py-3 hover:bg-slate-50">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <span class="inline-flex items-center rounded-md border px-2 py-0.5 text-xs ${badge}">
                  ${r.category || "—"}
                </span>
                <span class="font-medium truncate">${r.name || "Tournament"}</span>
              </div>
              <div class="text-xs text-slate-500 mt-0.5">
                ${when || ""} ${place ? "• " + place : ""}
              </div>
            </div>
            <svg aria-hidden="true" class="w-4 h-4 text-slate-400"><path d="M5 3l6 5-6 5" fill="none" stroke="currentColor" stroke-width="2"/></svg>
          </a>
        `;
      }).join("");
      return `
        <div class="bg-white">
          <div class="sticky top-[4rem] z-10 bg-white/90 backdrop-blur px-4 py-2 border-b">
            <h2 class="text-sm font-semibold uppercase tracking-wider text-slate-600">${title}</h2>
          </div>
          <div class="divide-y">
            ${items}
          </div>
        </div>
      `;
    }).join("");
    listEl.innerHTML = html;
  }

  async function load() {
    const q = new URLSearchParams();
    if (season) q.set("season", season);
    const url = q.toString() ? `${API}?${q}` : API;
    try {
      const r = await fetch(url, { headers: { "Accept": "application/json" } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      rows = (data.tournaments || []).map(t => ({
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

  // ovládání
  selMonth && selMonth.addEventListener("change", render);
  selCat && selCat.addEventListener("change", render);
  btnToday && btnToday.addEventListener("click", () => {
    // přeroluje na blok s aktuálním měsícem (pokud existuje)
    const now = new Date();
    const key = `${now.getFullYear()}-${String(now.getMonth()+1).padStart(2,"0")}`;
    const headings = Array.from(listEl.querySelectorAll("h2"));
    const el = headings.find(h => h.textContent?.toLowerCase().includes(now.toLocaleString(undefined, { month: "long" }).toLowerCase()));
    if (el) el.scrollIntoView({ behavior: "smooth", block: "start" });
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
