(function () {
  const root = document.getElementById("prog-root");
  if (!root) return;

  const matchesUrl = root.dataset.matchesUrl || "";
  const courtsUrl = root.dataset.courtsUrl || "";
  const rangeStart = root.dataset.start || "";
  const rangeEnd = root.dataset.end || "";

  const orderContainer = document.getElementById("prog-order");
  const tableContainer = document.getElementById("prog-table");
  const tableBody = document.getElementById("prog-table-body");
  const countEl = document.getElementById("prog-count");
  const emptyEl = document.getElementById("prog-empty");
  const loadingEl = document.getElementById("prog-loading");
  const loadMoreBtn = document.getElementById("prog-load-more");

  const filterMonth = document.getElementById("filter-fax-month");
  const filterDay = document.getElementById("filter-fax-day");
  const filterCourt = document.getElementById("filter-court");
  const filterPhase = document.getElementById("filter-phase");
  const filterStatus = document.getElementById("filter-status");
  const filterBestOf = document.getElementById("filter-best-of");
  const filterSearch = document.getElementById("filter-q");
  const filterLiveOnly = document.getElementById("filter-live-only");
  const modeOrderBtn = document.getElementById("prog-mode-order");
  const modeTableBtn = document.getElementById("prog-mode-table");

  let liveAnnouncer = document.getElementById("prog-live-status");
  if (!liveAnnouncer && root) {
    liveAnnouncer = document.createElement("div");
    liveAnnouncer.id = "prog-live-status";
    liveAnnouncer.className = "sr-only";
    liveAnnouncer.setAttribute("role", "status");
    liveAnnouncer.setAttribute("aria-live", "polite");
    root.appendChild(liveAnnouncer);
  }

  const STORAGE_KEY = "msa_program_mode";
  const params = new URLSearchParams(location.search);
  const DEFAULT_LIMIT = 50;
  const datasetLimitRaw = Number.parseInt(root.dataset.limit || "", 10);
  const datasetOffsetRaw = Number.parseInt(root.dataset.offset || "", 10);

  function clampLimit(value) {
    if (!Number.isFinite(value)) return DEFAULT_LIMIT;
    return Math.min(Math.max(value, 1), 500);
  }

  function readStoredMode() {
    try {
      return window.localStorage.getItem(STORAGE_KEY);
    } catch (err) {
      return null;
    }
  }

  const storedMode = readStoredMode();
  const initialMode = params.get("mode") === "table" ? "table" : storedMode === "table" ? "table" : "order";

  const rawLimit = Number.parseInt(params.get("limit") || "", 10);
  const initialLimit = Number.isFinite(rawLimit)
    ? clampLimit(rawLimit)
    : clampLimit(datasetLimitRaw);

  const rawOffset = Number.parseInt(params.get("offset") || "", 10);
  const datasetOffset = Number.isFinite(datasetOffsetRaw) && datasetOffsetRaw > 0 ? datasetOffsetRaw : 0;
  const initialOffset = Number.isFinite(rawOffset) && rawOffset > 0 ? rawOffset : datasetOffset;

  const state = {
    month: params.get("fax_month") || "",
    day: params.get("fax_day") || "",
    court: params.get("court") || "",
    phase: params.get("phase") || "all",
    status: params.get("status") || "all",
    best_of: params.get("best_of") || "",
    q: params.get("q") || "",
    mode: initialMode,
    limit: initialLimit,
    offset: initialOffset,
    next_offset: null,
  };

  let matches = [];
  let courts = [];
  let faxDays = [];
  let isLoading = false;
  let isAppending = false;
  let totalCount = null;
  let currentController = null;
  let requestCounter = 0;

  if (countEl) {
    countEl.classList.add("hidden");
  }

  const FaxDates = window.MSAFaxDates || {};
  const { parseFaxDate, getFaxYearMeta, enumerateFaxDays } = FaxDates;

  function padMonth(value) {
    if (!value) return "";
    const numeric = Number.parseInt(value, 10);
    if (!Number.isFinite(numeric)) return String(value);
    return String(numeric).padStart(2, "0");
  }

  function updateQueryString() {
    const search = new URLSearchParams(location.search);
    if (state.month) search.set("fax_month", state.month);
    else search.delete("fax_month");

    if (state.day) search.set("fax_day", state.day);
    else search.delete("fax_day");

    if (state.court) search.set("court", state.court);
    else search.delete("court");

    if (state.phase && state.phase !== "all") search.set("phase", state.phase);
    else search.delete("phase");

    if (state.status && state.status !== "all") search.set("status", state.status);
    else search.delete("status");

    if (state.best_of) search.set("best_of", state.best_of);
    else search.delete("best_of");

    if (state.q) search.set("q", state.q);
    else search.delete("q");

    if (state.mode === "table") search.set("mode", "table");
    else search.delete("mode");

    const qs = search.toString();
    history.replaceState(null, "", `${location.pathname}${qs ? `?${qs}` : ""}`);
  }

  function showLoading() {
    isLoading = true;
    loadingEl?.classList.remove("hidden");
    emptyEl?.classList.add("hidden");
    orderContainer?.classList.add("hidden");
    tableContainer?.classList.add("hidden");
    loadMoreBtn?.classList.add("hidden");
    if (loadMoreBtn) loadMoreBtn.disabled = true;
    if (countEl) countEl.classList.add("hidden");
  }

  function hideLoading() {
    isLoading = false;
    loadingEl?.classList.add("hidden");
  }

  function updateCounter() {
    if (!countEl) return;
    if (typeof totalCount === "number" && Number.isFinite(totalCount)) {
      countEl.textContent = `Zobrazeno ${matches.length} z ${totalCount}`;
      countEl.classList.remove("hidden");
    } else {
      countEl.textContent = "";
      countEl.classList.add("hidden");
    }
  }

  function formatScore(sets) {
    if (!Array.isArray(sets) || sets.length === 0) {
      return "";
    }
    const parts = sets
      .map((set) => {
        if (!set) return "";
        const a = set.a ?? (Array.isArray(set) ? set[0] : null);
        const b = set.b ?? (Array.isArray(set) ? set[1] : null);
        if (a == null || b == null) return "";
        return `${a}–${b}`;
      })
      .filter(Boolean);
    return parts.join(", ");
  }

  function statusLabel(status) {
    switch (status) {
      case "live":
        return "Živě";
      case "finished":
        return "Dokončeno";
      case "scheduled":
        return "Naplánováno";
      default:
        return status || "";
    }
  }

  function buildMonthOptions() {
    if (!filterMonth) return;
    const existingValue = filterMonth.value;
    filterMonth.querySelectorAll("option:not([value=''])").forEach((opt) => opt.remove());
    const seen = new Set();
    faxDays.forEach((day) => {
      const parts = String(day).split("-");
      if (parts.length < 2) return;
      const month = parts[1];
      const numeric = Number.parseInt(month, 10);
      if (!Number.isFinite(numeric)) return;
      if (seen.has(numeric)) return;
      seen.add(numeric);
      const opt = document.createElement("option");
      opt.value = String(numeric);
      opt.textContent = String(numeric);
      filterMonth.appendChild(opt);
    });
    const desired = state.month || existingValue;
    if (desired) filterMonth.value = desired;
  }

  function updateDayOptions() {
    if (!filterDay) return;
    const activeMonth = padMonth(state.month);
    const previous = state.day;
    filterDay.innerHTML = "";
    const optAll = document.createElement("option");
    optAll.value = "";
    optAll.textContent = "Vše";
    filterDay.appendChild(optAll);

    const validDays = faxDays.filter((day) => !activeMonth || String(day).split("-")[1] === activeMonth);
    validDays.forEach((day) => {
      const opt = document.createElement("option");
      opt.value = day;
      opt.textContent = day;
      filterDay.appendChild(opt);
    });
    if (previous && !validDays.includes(previous)) {
      state.day = "";
    }
    filterDay.value = state.day;
  }

  function populateCourts() {
    if (!filterCourt) return;
    filterCourt.querySelectorAll("option:not([value=''])").forEach((opt) => opt.remove());
    courts.forEach((court) => {
      const identifier = court?.id ?? court?.name;
      const label = court?.name || (typeof court === "string" ? court : identifier);
      if (!identifier && !label) return;
      const opt = document.createElement("option");
      opt.value = String(identifier || label);
      opt.textContent = label || String(identifier);
      filterCourt.appendChild(opt);
    });
    if (state.court) {
      filterCourt.value = state.court;
      if (filterCourt.value !== state.court) {
        state.court = "";
      }
    }
  }

  function updateModeButtons() {
    const isTable = state.mode === "table";
    modeOrderBtn?.setAttribute("aria-selected", isTable ? "false" : "true");
    modeTableBtn?.setAttribute("aria-selected", isTable ? "true" : "false");
    modeOrderBtn?.classList.toggle("bg-slate-100", !isTable);
    modeTableBtn?.classList.toggle("bg-slate-100", isTable);
    if (modeOrderBtn) modeOrderBtn.tabIndex = isTable ? -1 : 0;
    if (modeTableBtn) modeTableBtn.tabIndex = isTable ? 0 : -1;
  }

  function renderOrder(hasData) {
    if (!orderContainer) return;
    orderContainer.innerHTML = "";
    if (!hasData) return;

    const dayMap = new Map();
    matches.forEach((match) => {
      const dayKey = match.fax_day || "TBD";
      if (!dayMap.has(dayKey)) dayMap.set(dayKey, []);
      dayMap.get(dayKey).push(match);
    });

    const sortedDays = Array.from(dayMap.keys()).sort((a, b) => String(a).localeCompare(String(b)));
    sortedDays.forEach((dayKey) => {
      const dayMatches = dayMap.get(dayKey) || [];
      const dayEl = document.createElement("div");
      dayEl.className = "rounded-lg border border-slate-200 p-4";

      const heading = document.createElement("h3");
      heading.className = "text-base font-semibold text-slate-800";
      heading.textContent = dayKey;
      dayEl.appendChild(heading);

      const courtsMap = new Map();
      dayMatches.forEach((match) => {
        const courtData = match.court;
        const name = courtData?.name || courtData || "Neurčeno";
        if (!courtsMap.has(name)) courtsMap.set(name, []);
        courtsMap.get(name).push(match);
      });

      const courtsWrapper = document.createElement("div");
      courtsWrapper.className = "mt-3 grid gap-3 md:grid-cols-2 xl:grid-cols-3";

      Array.from(courtsMap.keys()).sort((a, b) => String(a).localeCompare(String(b))).forEach((courtName) => {
        const courtEl = document.createElement("div");
        courtEl.className = "rounded-md border border-dashed border-slate-200 p-3";

        const courtHeading = document.createElement("h4");
        courtHeading.className = "text-sm font-semibold text-slate-700";
        courtHeading.textContent = courtName;
        courtEl.appendChild(courtHeading);

        const list = document.createElement("div");
        list.className = "mt-2 space-y-2";

        courtsMap.get(courtName).sort((a, b) => {
          const orderA = Number.parseInt(a.order, 10);
          const orderB = Number.parseInt(b.order, 10);
          if (Number.isFinite(orderA) && Number.isFinite(orderB)) {
            return orderA - orderB;
          }
          return String(a.round_label || "").localeCompare(String(b.round_label || ""));
        }).forEach((match) => {
          const item = document.createElement("div");
          item.className = "rounded border border-slate-200 px-3 py-2 text-sm bg-white";

          const title = document.createElement("div");
          title.className = "flex items-center justify-between gap-2";

          const round = document.createElement("span");
          round.className = "text-xs uppercase tracking-wide text-slate-500";
          round.textContent = match.round_label || match.phase || "";
          title.appendChild(round);

          if (match.status === "live") {
            const badge = document.createElement("span");
            badge.className = "inline-flex items-center rounded bg-rose-500/10 px-2 py-0.5 text-[11px] font-semibold uppercase text-rose-600";
            badge.textContent = "LIVE";
            title.appendChild(badge);
          }
          if (match.needs_review) {
            const review = document.createElement("span");
            review.className = "text-xs text-amber-600";
            review.textContent = "⚠ kontrola";
            title.appendChild(review);
          }

          item.appendChild(title);

          const playersWrap = document.createElement("div");
          playersWrap.className = "mt-1 text-sm font-medium text-slate-900";
          const playerA = match.players?.[0]?.name || "TBD";
          const playerB = match.players?.[1]?.name || "TBD";
          playersWrap.textContent = `${playerA} vs ${playerB}`;
          item.appendChild(playersWrap);

          const scoreText = formatScore(match.sets);
          if (scoreText) {
            const scoreEl = document.createElement("div");
            scoreEl.className = "text-xs text-slate-500";
            scoreEl.textContent = scoreText;
            item.appendChild(scoreEl);
          }

          const statusEl = document.createElement("div");
          statusEl.className = "text-xs text-slate-400";
          statusEl.textContent = statusLabel(match.status);
          item.appendChild(statusEl);

          list.appendChild(item);
        });

        courtEl.appendChild(list);
        courtsWrapper.appendChild(courtEl);
      });

      dayEl.appendChild(courtsWrapper);
      orderContainer.appendChild(dayEl);
    });
  }

  function renderTable(hasData) {
    if (!tableBody || !tableContainer) return;
    tableBody.innerHTML = "";
    if (!hasData) return;

    matches.forEach((match) => {
      const row = document.createElement("tr");
      row.className = "hover:bg-slate-50";

      const cells = [
        match.fax_day || "—",
        match.court?.name || match.court || "—",
        match.round_label || match.phase || "—",
        match.players?.[0]?.name || "TBD",
        match.players?.[1]?.name || "TBD",
        formatScore(match.sets) || "",
        statusLabel(match.status) || "",
      ];

      cells.forEach((text) => {
        const cell = document.createElement("td");
        cell.className = "px-4 py-2 text-left text-sm text-slate-700";
        cell.textContent = text;
        row.appendChild(cell);
      });

      tableBody.appendChild(row);
    });
  }

  function updateLoadMoreButton() {
    if (!loadMoreBtn) return;
    const hasNext = state.next_offset !== null && state.next_offset !== undefined;
    const shouldShow = !isLoading && !isAppending && hasNext && matches.length > 0;
    if (shouldShow) {
      loadMoreBtn.classList.remove("hidden");
      loadMoreBtn.disabled = false;
      loadMoreBtn.removeAttribute("aria-busy");
    } else {
      loadMoreBtn.classList.add("hidden");
      loadMoreBtn.disabled = true;
    }
  }

  function renderMatches() {
    updateCounter();
    if (isLoading) {
      updateLoadMoreButton();
      return;
    }
    const hasData = matches.length > 0;
    if (hasData) emptyEl?.classList.add("hidden");
    else emptyEl?.classList.remove("hidden");

    const showOrder = state.mode !== "table" && hasData;
    const showTable = state.mode === "table" && hasData;
    orderContainer?.classList.toggle("hidden", !showOrder);
    tableContainer?.classList.toggle("hidden", !showTable);

    if (state.mode === "table") {
      renderTable(hasData);
    } else {
      renderOrder(hasData);
    }

    updateLoadMoreButton();
  }

  function setMode(mode, options = {}) {
    const { force = false, persist = true } = options;
    const nextMode = mode === "table" ? "table" : "order";
    if (!force && state.mode === nextMode) {
      return;
    }
    state.mode = nextMode;
    updateModeButtons();
    updateQueryString();
    if (persist) {
      try {
        window.localStorage.setItem(STORAGE_KEY, state.mode);
      } catch (err) {
        /* ignore */
      }
    }
    renderMatches();
  }

  async function prepareFaxDays() {
    if (!rangeStart || !rangeEnd || !parseFaxDate || !getFaxYearMeta || !enumerateFaxDays) {
      faxDays = [];
      if (rangeStart) faxDays.push(rangeStart);
      if (rangeEnd && rangeEnd !== rangeStart) faxDays.push(rangeEnd);
      return;
    }

    let start;
    let end;
    try {
      start = parseFaxDate(rangeStart);
      end = parseFaxDate(rangeEnd);
    } catch (err) {
      faxDays = [];
      return;
    }

    const minYear = Math.min(start.y, end.y);
    const maxYear = Math.max(start.y, end.y);
    const requests = [];
    for (let y = minYear; y <= maxYear; y += 1) {
      requests.push(getFaxYearMeta(y));
    }
    await Promise.all(requests);
    faxDays = enumerateFaxDays(rangeStart, rangeEnd) || [];
    if (!Array.isArray(faxDays) || faxDays.length === 0) {
      faxDays = [rangeStart];
      if (rangeEnd && rangeEnd !== rangeStart) {
        faxDays.push(rangeEnd);
      }
    }
  }

  async function fetchCourts() {
    if (!courtsUrl) return;
    try {
      const resp = await fetch(courtsUrl, { headers: { Accept: "application/json" } });
      if (!resp.ok) return;
      const json = await resp.json();
      courts = Array.isArray(json?.courts) ? json.courts : [];
      populateCourts();
    } catch (err) {
      courts = [];
    }
  }

  function buildMatchesUrl() {
    if (!matchesUrl) return "";
    const search = new URLSearchParams();
    if (state.month) search.set("fax_month", state.month);
    if (state.day) search.set("fax_day", state.day);
    if (state.court) search.set("court", state.court);
    if (state.phase && state.phase !== "all") search.set("phase", state.phase);
    if (state.status && state.status !== "all") search.set("status", state.status);
    if (state.best_of) search.set("best_of", state.best_of);
    if (state.q) search.set("q", state.q);
    const limitValue = clampLimit(state.limit || DEFAULT_LIMIT);
    search.set("limit", String(limitValue));
    search.set("offset", String(state.offset || 0));
    const qs = search.toString();
    return `${matchesUrl}${qs ? `?${qs}` : ""}`;
  }

  function isAbortError(error) {
    if (!error) return false;
    if (error.name === "AbortError") return true;
    if (typeof DOMException !== "undefined" && error instanceof DOMException) {
      return error.name === "AbortError";
    }
    return false;
  }

  function announce(message) {
    if (!liveAnnouncer) return;
    liveAnnouncer.textContent = message || "";
  }

  async function fetchMatches(options = {}) {
    if (!matchesUrl) return;
    const {
      append = false,
      previousOffset = state.offset,
      previousNext = state.next_offset,
      previousCount = totalCount,
    } = options;

    const priorMatches = matches.slice();

    if (currentController) {
      currentController.abort();
    }
    const controller = new AbortController();
    currentController = controller;
    const requestId = ++requestCounter;

    let appendedCount = 0;
    let aborted = false;
    let failed = false;

    if (!append) {
      showLoading();
      announce("");
    } else {
      isAppending = true;
      if (loadMoreBtn) {
        loadMoreBtn.disabled = true;
        loadMoreBtn.setAttribute("aria-busy", "true");
      }
      updateLoadMoreButton();
    }

    try {
      const resp = await fetch(buildMatchesUrl(), {
        headers: { Accept: "application/json" },
        signal: controller.signal,
      });
      if (!resp.ok) {
        failed = true;
      } else {
        const json = await resp.json();
        if (requestId !== requestCounter) {
          return;
        }
        const fetched = Array.isArray(json?.matches) ? json.matches : [];
        appendedCount = append ? fetched.length : 0;
        matches = append ? priorMatches.concat(fetched) : fetched;

        if (typeof json?.count === "number") {
          totalCount = json.count;
        } else if (append && typeof previousCount === "number") {
          totalCount = previousCount;
        } else if (!append) {
          totalCount = matches.length;
        } else {
          totalCount = null;
        }

        const limitFromJson = Number.parseInt(json?.limit, 10);
        if (Number.isFinite(limitFromJson)) {
          state.limit = clampLimit(limitFromJson);
        }

        const offsetFromJson = Number.parseInt(json?.offset, 10);
        if (Number.isFinite(offsetFromJson) && offsetFromJson >= 0) {
          state.offset = offsetFromJson;
        } else if (!append) {
          state.offset = 0;
        } else {
          state.offset = previousOffset;
        }

        const rawNext = json?.next_offset;
        if (typeof rawNext === "number") {
          state.next_offset = rawNext;
        } else if (rawNext === 0) {
          state.next_offset = 0;
        } else {
          state.next_offset = null;
        }
      }
    } catch (err) {
      if (isAbortError(err)) {
        aborted = true;
      } else {
        failed = true;
      }
    } finally {
      if (requestId !== requestCounter) {
        if (append) {
          isAppending = false;
          if (loadMoreBtn) {
            loadMoreBtn.removeAttribute("aria-busy");
            loadMoreBtn.disabled = false;
          }
          updateLoadMoreButton();
        }
        return;
      }

      if (currentController === controller) {
        currentController = null;
      }

      if (failed) {
        matches = priorMatches;
        state.offset = previousOffset;
        state.next_offset = previousNext;
        totalCount = typeof previousCount === "number" ? previousCount : totalCount;
      } else if (append && aborted) {
        matches = priorMatches;
        state.offset = previousOffset;
        state.next_offset = previousNext;
        totalCount = typeof previousCount === "number" ? previousCount : totalCount;
      }

      if (!append) {
        hideLoading();
      } else {
        isAppending = false;
        if (loadMoreBtn) {
          loadMoreBtn.removeAttribute("aria-busy");
        }
      }

      renderMatches();

      if (append) {
        if (!failed && !aborted && appendedCount > 0) {
          announce(`Načteno ${appendedCount} nových zápasů.`);
        } else {
          announce("");
        }
      } else {
        announce("");
      }
    }
  }

  function resetPagination() {
    state.offset = 0;
    state.next_offset = null;
    matches = [];
    totalCount = null;
  }

  function debounce(fn, delay = 250) {
    let timer = null;
    return function debounced(...args) {
      clearTimeout(timer);
      timer = setTimeout(() => fn.apply(this, args), delay);
    };
  }

  function bindEvents() {
    filterMonth?.addEventListener("change", () => {
      state.month = filterMonth.value || "";
      if (!state.month) state.day = "";
      updateDayOptions();
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterDay?.addEventListener("change", () => {
      state.day = filterDay.value || "";
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterCourt?.addEventListener("change", () => {
      state.court = filterCourt.value || "";
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterPhase?.addEventListener("change", () => {
      state.phase = filterPhase.value || "all";
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterStatus?.addEventListener("change", () => {
      state.status = filterStatus.value || "all";
      if (filterLiveOnly) {
        filterLiveOnly.checked = state.status === "live";
      }
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterBestOf?.addEventListener("change", () => {
      state.best_of = filterBestOf.value || "";
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    filterLiveOnly?.addEventListener("change", () => {
      if (filterLiveOnly.checked) {
        state.status = "live";
        if (filterStatus) filterStatus.value = "live";
      } else {
        state.status = "all";
        if (filterStatus) filterStatus.value = "all";
      }
      resetPagination();
      updateQueryString();
      fetchMatches();
    });

    if (filterSearch) {
      const handler = debounce(() => {
        state.q = filterSearch.value.trim();
        resetPagination();
        updateQueryString();
        fetchMatches();
      }, 350);
      filterSearch.addEventListener("input", handler);
    }

    modeOrderBtn?.addEventListener("click", () => setMode("order"));
    modeTableBtn?.addEventListener("click", () => setMode("table"));

    loadMoreBtn?.addEventListener("click", () => {
      if (
        isLoading ||
        isAppending ||
        matches.length === 0 ||
        state.next_offset === null ||
        state.next_offset === undefined
      ) {
        return;
      }
      const nextOffset = state.next_offset;
      const previousOffset = state.offset;
      const previousNext = state.next_offset;
      const previousCount = totalCount;
      state.offset = nextOffset;
      fetchMatches({ append: true, previousOffset, previousNext, previousCount });
    });
  }

  function setInitialFilterValues() {
    if (filterMonth && state.month) filterMonth.value = state.month;
    if (filterDay && state.day) filterDay.value = state.day;
    if (filterCourt && state.court) filterCourt.value = state.court;
    if (filterPhase) filterPhase.value = state.phase || "all";
    if (filterStatus) filterStatus.value = state.status || "all";
    if (filterBestOf) filterBestOf.value = state.best_of || "";
    if (filterSearch) filterSearch.value = state.q || "";
    if (filterLiveOnly) filterLiveOnly.checked = state.status === "live";
  }

  (async function init() {
    await prepareFaxDays();
    buildMonthOptions();
    updateDayOptions();
    setInitialFilterValues();
    updateModeButtons();
    bindEvents();
    await fetchCourts();
    await fetchMatches();
    setMode(state.mode, { force: true });
  })();
})();
