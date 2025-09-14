(function () {
  const root = document.getElementById("rankings-root");
  if (!root) return;
  const API = root.dataset.api || "/api/msa/ranking";
  const bodyEl = document.getElementById("rankings-tbody");
  const loading = document.getElementById("rankings-loading");
  const selSeason = document.getElementById("rank-season");
  const inpSearch = document.getElementById("rank-search");
  const thSorts = Array.from(root.querySelectorAll("th[data-sort]"));

  /** state **/
  let rows = [];            // originální data
  let view = [];            // filtrovaný/řazený pohled
  let sortKey = "rank";
  let sortDir = "asc";      // asc | desc

  function arrow(delta) {
    if (delta == null) return "";
    if (delta < 0) return `<span class="text-emerald-600">▲${Math.abs(delta)}</span>`;
    if (delta > 0) return `<span class="text-rose-600">▼${delta}</span>`;
    return `<span class="text-slate-400">—</span>`;
  }

  function normalize(s) { return (s || "").toString().toLowerCase(); }

  function render() {
    const q = normalize(inpSearch?.value);
    const filtered = q
      ? rows.filter(r =>
          normalize(r.player_name).includes(q) ||
          normalize(r.country).includes(q)
        )
      : rows.slice();
    filtered.sort((a,b) => {
      const dir = sortDir === "asc" ? 1 : -1;
      switch (sortKey) {
        case "player":
          return normalize(a.player_name) > normalize(b.player_name) ? dir : -dir;
        case "points":
          return (a.points - b.points) * dir;
        case "rank":
        default:
          return (a.rank - b.rank) * dir;
      }
    });
    view = filtered;
    const html = view.map(r => `
      <tr class="border-b hover:bg-slate-50">
        <td class="px-3 py-2 tabular-nums">${r.rank}</td>
        <td class="px-3 py-2">
          <a class="hover:underline" href="/msa/players/${r.player_id}/">${r.player_name}</a>
        </td>
        <td class="px-3 py-2">${r.country || ""}</td>
        <td class="px-3 py-2 tabular-nums font-medium">${r.points.toLocaleString()}</td>
        <td class="px-3 py-2">${arrow(r.delta)}</td>
      </tr>
    `).join("");
    bodyEl.innerHTML = html || `<tr><td colspan="5" class="px-3 py-6 text-center text-slate-500">Žádná data</td></tr>`;
  }

  async function load() {
    const params = new URLSearchParams();
    const season = selSeason?.value?.trim();
    if (season) params.set("season", season);
    const url = params.toString() ? `${API}?${params}` : API;
    try {
      const r = await fetch(url, { headers: { "Accept": "application/json" } });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const data = await r.json();
      rows = (data.entries || []).map((e, i) => ({
        rank: e.rank ?? (i + 1),
        player_id: e.player_id,
        player_name: e.player_name,
        country: e.country || "",
        points: Number(e.points || 0),
        delta: typeof e.delta === "number" ? e.delta : null,
      }));
      loading && (loading.style.display = "none");
      render();
    } catch (err) {
      console.error(err);
      if (loading) loading.textContent = "Nepodařilo se načíst žebříček.";
    }
  }

  thSorts.forEach(th => {
    th.addEventListener("click", () => {
      const key = th.dataset.sort;
      if (sortKey === key) {
        sortDir = sortDir === "asc" ? "desc" : "asc";
      } else {
        sortKey = key;
        sortDir = key === "rank" ? "asc" : "desc";
      }
      render();
    });
  });
  selSeason && selSeason.addEventListener("change", load);
  inpSearch && inpSearch.addEventListener("input", () => { render(); });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", load);
  } else {
    load();
  }
})();
