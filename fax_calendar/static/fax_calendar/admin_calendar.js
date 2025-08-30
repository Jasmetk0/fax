(function (exports) {
  const core = window.woorldCore;
  const astro = window.woorldAstro;

  const WEEKDAY_NAMES = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday",
  ];

  function format(day, month, year) {
    return (
      String(day).padStart(2, "0") +
      "-" +
      String(month).padStart(2, "0") +
      "-" +
      String(year).padStart(4, "0")
    );
  }

  function startWeekdays(year, months) {
    let w = 0;
    for (let y = 1; y < year; y++) {
      w = (w + astro.yearLength(y)) % 7;
    }
    const out = [];
    for (let i = 0; i < months.length; i++) {
      out.push(w);
      w = (w + months[i]) % 7;
    }
    return out;
  }

  function toDoy(month, day, months) {
    let n = day;
    for (let i = 1; i < month; i++) n += months[i - 1];
    return n;
  }

  function buildBtn(label, handler, cls = "") {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = `wc-btn ${cls}`.trim();
    btn.textContent = label;
    if (handler) btn.addEventListener("click", handler);
    return btn;
  }

  function createThemeToggle(overlay) {
    const wrap = document.createElement("div");
    wrap.className = "wc-switch";
    const thumb = document.createElement("div");
    thumb.className = "wc-switch__thumb";
    wrap.appendChild(thumb);
    function apply(state) {
      if (state === "dark") {
        overlay.classList.add("wc-dark");
        wrap.classList.add("is-on");
      } else {
        overlay.classList.remove("wc-dark");
        wrap.classList.remove("is-on");
      }
    }
    let theme = localStorage.getItem("wc-theme") || "light";
    apply(theme);
    wrap.addEventListener("click", () => {
      theme = theme === "dark" ? "light" : "dark";
      localStorage.setItem("wc-theme", theme);
      apply(theme);
    });
    return wrap;
  }

  function attachWoorldCalendar(input) {
    if (input.dataset.woorldDateEnhanced) return;
    input.dataset.woorldDateEnhanced = "1";

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "wc-iconbtn";
    btn.innerHTML = "&#x1F4C5;"; // calendar icon
    input.insertAdjacentElement("afterend", btn);

    function open() {
      const overlay = document.createElement("div");
      overlay.className = "wc-overlay";
      const card = document.createElement("div");
      card.className = "wc-card";
      overlay.appendChild(card);
      document.body.appendChild(overlay);

      const yearMatch = input.value.match(/\d{1,2}[-.]\d{1,2}[-.](\d{1,4})/);
      let year = yearMatch ? parseInt(yearMatch[1], 10) : 1;
      if (!yearMatch && Array.isArray(window.WOORLD_TODAY)) {
        year = window.WOORLD_TODAY[0];
      }

      function close() {
        overlay.remove();
      }

      overlay.addEventListener("click", (e) => {
        if (e.target === overlay) close();
      });
      window.addEventListener("keydown", function esc(e) {
        if (e.key === "Escape") {
          close();
          window.removeEventListener("keydown", esc);
        }
      });

      function build(y) {
        card.innerHTML = "";
        const months = core.monthLengths(y);
        const starts = startWeekdays(y, months);
        const yearDays = astro.yearLength(y);

        const header = document.createElement("div");
        header.className = "wc-header";
        const prev = document.createElement("button");
        prev.type = "button";
        prev.className = "wc-iconbtn";
        prev.textContent = "‹";
        const next = document.createElement("button");
        next.type = "button";
        next.className = "wc-iconbtn";
        next.textContent = "›";
        const yearInput = document.createElement("input");
        yearInput.type = "number";
        yearInput.className = "wc-input";
        yearInput.value = y;
        const meta = document.createElement("div");
        meta.className = "wc-meta";
        const pill = document.createElement("span");
        pill.className = "wc-meta__pill";
        pill.textContent = `${yearDays} days`;
        meta.appendChild(pill);
        const themeToggle = createThemeToggle(overlay);
        header.append(prev, yearInput, next, meta, themeToggle);
        card.appendChild(header);

        const toolbar = document.createElement("div");
        toolbar.className = "wc-toolbar";
        function choose(yy, mm, dd) {
          input.value = format(dd, mm, yy);
          close();
        }
        const firstBtn = buildBtn("1st day", () => choose(y, 1, 1));
        const lastOrd = yearDays;
        const [yL, mL, dL] = astro.fromOrdinal(y, lastOrd);
        const lastBtn = buildBtn("Last day", () => choose(yL, mL, dL));
        const resetBtn = buildBtn("Reset", () => choose(2020, 1, 1));
        toolbar.append(firstBtn, lastBtn, resetBtn);
        card.appendChild(toolbar);

        const anchorRow = document.createElement("div");
        anchorRow.className = "wc-anchors";
        anchorRow.style.flexDirection = "column";
        const anchorBtns = document.createElement("div");
        anchorBtns.style.display = "flex";
        anchorBtns.style.gap = "8px";
        anchorRow.appendChild(anchorBtns);
        const events = astro.eventsForYear(y);
        const cfg = [
          ["Winter", events.winters, "winter"],
          ["Spring", events.springs, "spring"],
          ["Summer", events.summers, "summer"],
          ["Autumn", events.autumns, "autumn"],
        ];
        cfg.forEach(([label, arr, season]) => {
          const btn = buildBtn(label, () => arr.length && choose(arr[0].y, arr[0].m, arr[0].d));
          btn.dataset.season = season;
          if (!arr.length) {
            btn.disabled = true;
            btn.title = "Anchor not present in this year";
          }
          anchorBtns.appendChild(btn);
          if (label === "Winter" && arr.length > 1) {
            const btn2 = buildBtn("Winter II", () => choose(arr[1].y, arr[1].m, arr[1].d));
            btn2.dataset.season = season;
            anchorBtns.appendChild(btn2);
          }
        });

        const seasonbar = document.createElement("div");
        seasonbar.className = "wc-seasonbar";
        const segments = [];
        let last = astro.seasonOf(y, 1);
        let start = 1;
        for (let d = 2; d <= yearDays; d++) {
          const s = astro.seasonOf(y, d);
          if (s !== last) {
            segments.push({ name: last, start, end: d - 1 });
            start = d;
            last = s;
          }
        }
        segments.push({ name: last, start, end: yearDays });
        segments.forEach((seg) => {
          const div = document.createElement("div");
          div.className = `wc-seasonbar__seg ${seg.name
            .toLowerCase()
            .replace(/\s+/g, "")}`;
          div.style.width = `${((seg.end - seg.start + 1) / yearDays) * 100}%`;
          seasonbar.appendChild(div);
        });
        events.winters.forEach((w) => {
          const mark = document.createElement("div");
          mark.className = "wc-seasonbar__mark";
          const doy = toDoy(w.m, w.d, months);
          mark.style.left = `${((doy - 1) / yearDays) * 100}%`;
          seasonbar.appendChild(mark);
        });
        anchorRow.appendChild(seasonbar);
        card.appendChild(anchorRow);

        const monthsDiv = document.createElement("div");
        monthsDiv.className = "wc-months";
        card.appendChild(monthsDiv);

        const footer = document.createElement("div");
        footer.className = "wc-footer";
        card.appendChild(footer);

        function updateFooter(d, m) {
          const doy = toDoy(m, d, months);
          const w = (starts[m - 1] + d - 1) % 7;
          const season = astro.seasonOf(y, doy);
          footer.innerHTML =
            `<strong>Date</strong> ${format(d, m, y)} ` +
            `<strong>Weekday</strong> ${WEEKDAY_NAMES[w]} ` +
            `<strong>Season</strong> ${season} ` +
            `<strong>Day-of-Year</strong> ${doy} / ${yearDays}`;
        }

        const selectedMatch = input.value.match(/(\d{2})[-.](\d{2})[-.](\d{1,4})/);
        const selected = selectedMatch
          ? {
              y: parseInt(selectedMatch[3], 10),
              m: parseInt(selectedMatch[2], 10),
              d: parseInt(selectedMatch[1], 10),
            }
          : null;

        for (let m = 1; m <= 15; m++) {
          const monthEl = document.createElement("div");
          monthEl.className = "wc-month";
          const head = document.createElement("div");
          head.className = "wc-month__head";
          head.innerHTML = `Month ${m} <span class="wc-month__days">${months[m - 1]} day</span>`;
          monthEl.appendChild(head);
          const wHead = document.createElement("div");
          wHead.className = "wc-weekdays";
          ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach((nm) => {
            const sp = document.createElement("span");
            sp.textContent = nm;
            wHead.appendChild(sp);
          });
          monthEl.appendChild(wHead);
          const grid = document.createElement("div");
          grid.className = "wc-grid";
          for (let i = 0; i < starts[m - 1]; i++) grid.appendChild(document.createElement("div"));
          for (let d = 1; d <= months[m - 1]; d++) {
            const dayEl = document.createElement("div");
            dayEl.className = "wc-day";
            dayEl.textContent = d;
            const doy = toDoy(m, d, months);
            const season = astro.seasonOf(y, doy).toLowerCase().replace(/\s+/g, "");
            dayEl.classList.add(`season-${season}`);
            if (season === "winterii") dayEl.classList.add("winter-ii");
            const w = (starts[m - 1] + d - 1) % 7;
            if (w === 5 || w === 6) dayEl.classList.add("is-weekend");
            if (
              Array.isArray(window.WOORLD_TODAY) &&
              window.WOORLD_TODAY[0] === y &&
              window.WOORLD_TODAY[1] === m &&
              window.WOORLD_TODAY[2] === d
            ) {
              dayEl.classList.add("is-today");
            }
            if (selected && selected.y === y && selected.m === m && selected.d === d) {
              dayEl.classList.add("is-selected");
            }
            dayEl.addEventListener("click", () => {
              choose(y, m, d);
            });
            grid.appendChild(dayEl);
          }
          monthEl.appendChild(grid);
          monthsDiv.appendChild(monthEl);
        }

        updateFooter(selected ? selected.d : 1, selected ? selected.m : 1);

        prev.addEventListener("click", () => build(y - 1));
        next.addEventListener("click", () => build(y + 1));
        yearInput.addEventListener("change", () => build(parseInt(yearInput.value, 10)));
      }

      build(year);
    }

    btn.addEventListener("click", open);
  }

  function enhanceAllWoorldDateInputs() {
    document
      .querySelectorAll('input[name$="_date"], input[data-woorld-date="1"]')
      .forEach((el) => attachWoorldCalendar(el));
  }

  exports.attachWoorldCalendar = attachWoorldCalendar;
  exports.enhanceAllWoorldDateInputs = enhanceAllWoorldDateInputs;
})(window);

