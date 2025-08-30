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

  function yearLength(y) {
    return astro.yearLength(y);
  }

  function startWeekdays(year, months) {
    let w = 0;
    for (let y = 1; y < year; y++) {
      w = (w + yearLength(y)) % 7;
    }
    const out = [];
    for (let i = 0; i < months.length; i++) {
      out.push(w);
      w = (w + months[i]) % 7;
    }
    return out;
  }

  function format(day, month, year) {
    return (
      String(day).padStart(2, "0") +
      "-" +
      String(month).padStart(2, "0") +
      "-" +
      String(year).padStart(4, "0")
    );
  }

  function attachWoorldCalendar(input) {
    if (input.dataset.woorldDateEnhanced) return;
    input.dataset.woorldDateEnhanced = "1";

    let button = input.nextElementSibling;
    if (!button || !button.classList.contains("woorld-calendar-btn")) {
      button = document.createElement("button");
      button.type = "button";
      button.textContent = "\uD83D\uDCC5"; // calendar emoji
      button.className = "woorld-calendar-btn";
      input.insertAdjacentElement("afterend", button);
    }

    const overlay = document.createElement("div");
    overlay.className = "woorld-calendar-overlay";
    document.body.appendChild(overlay);

    function build(year) {
      overlay.innerHTML = "";
      const months = core.monthLengths(year);
      const starts = startWeekdays(year, months);
      let dayOfYear = 1;

      const panel = document.createElement("div");
      panel.className = "woorld-calendar";
      if (localStorage.getItem("wc-theme") === "dark") {
        panel.classList.add("wc-dark");
      }

      const header = document.createElement("div");
      header.className = "wc-header";
      const prev = document.createElement("button");
      prev.type = "button";
      prev.textContent = "\u2039";
      const next = document.createElement("button");
      next.type = "button";
      next.textContent = "\u203A";
      const yearInput = document.createElement("input");
      yearInput.type = "number";
      yearInput.value = year;
      const yearDays = document.createElement("span");
      yearDays.className = "wc-year-days";
      yearDays.textContent = `${yearLength(year)} days`;
      const themeBtn = document.createElement("button");
      themeBtn.type = "button";
      themeBtn.textContent = "☼";
      themeBtn.addEventListener("click", () => {
        panel.classList.toggle("wc-dark");
        const mode = panel.classList.contains("wc-dark") ? "dark" : "light";
        localStorage.setItem("wc-theme", mode);
      });
      header.append(prev, yearInput, next, yearDays, themeBtn);
      panel.appendChild(header);

      // Season bar
      const bar = document.createElement("div");
      bar.className = "wc-season-bar";
      const segments = [];
      let last = astro.seasonOf(year, 1);
      let startD = 1;
      for (let d = 2; d <= yearLength(year); d++) {
        const s = astro.seasonOf(year, d);
        if (s !== last) {
          segments.push({ name: last, start: startD, end: d - 1 });
          startD = d;
          last = s;
        }
      }
      segments.push({ name: last, start: startD, end: yearLength(year) });
      segments.forEach((seg) => {
        const div = document.createElement("div");
        div.className = `wc-season-segment season-${seg.name
          .toLowerCase()
          .replace(/\s+/g, "")}`;
        const width = ((seg.end - seg.start + 1) / yearLength(year)) * 100;
        div.style.width = `${width}%`;
        div.title = `${seg.name} ${seg.start}-${seg.end}`;
        bar.appendChild(div);
      });
      panel.appendChild(bar);

      // Action buttons
      const actions = document.createElement("div");
      actions.className = "wc-actions";
      function choose(y, m, d) {
        input.value = format(d, m, y);
        overlay.classList.remove("active");
      }
      const firstBtn = document.createElement("button");
      firstBtn.type = "button";
      firstBtn.textContent = "1st day";
      firstBtn.addEventListener("click", () => choose(year, 1, 1));
      const lastOrd = yearLength(year);
      const [yL, mL, dL] = astro.fromOrdinal(year, lastOrd);
      const lastBtn = document.createElement("button");
      lastBtn.type = "button";
      lastBtn.textContent = "Last day";
      lastBtn.addEventListener("click", () => choose(yL, mL, dL));
      const resetBtn = document.createElement("button");
      resetBtn.type = "button";
      resetBtn.textContent = "Reset";
      resetBtn.addEventListener("click", () => choose(2020, 1, 1));
      actions.append(firstBtn, lastBtn, resetBtn);

      const events = astro.eventsForYear(year);
      function anchorBtn(name, arr) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = name;
        if (arr.length) {
          const e = arr[0];
          btn.addEventListener("click", () => choose(e.y, e.m, e.d));
        } else {
          btn.disabled = true;
          btn.title = "Anchor not present in this year";
        }
        actions.appendChild(btn);
      }
      anchorBtn("Winter", events.winters);
      if (events.winters.length > 1) anchorBtn("Winter II", [events.winters[1]]);
      anchorBtn("Spring", events.springs);
      anchorBtn("Summer", events.summers);
      anchorBtn("Autumn", events.autumns);

      panel.appendChild(actions);

      const grid = document.createElement("div");
      grid.className = "wc-month-grid";
      panel.appendChild(grid);

      const info = document.createElement("div");
      info.className = "wc-info";
      panel.appendChild(info);

      function updateInfo(d, m) {
        const doy = toDoy(m, d);
        const w = (starts[m - 1] + d - 1) % 7;
        const season = astro.seasonOf(year, doy);
        info.textContent = `Date ${format(d, m, year)} – ${WEEKDAY_NAMES[w]}, ${season}, ${doy} / ${yearLength(
          year
        )}`;
      }

      function toDoy(m, d) {
        let n = d;
        for (let i = 1; i < m; i++) n += months[i - 1];
        return n;
      }

      for (let m = 1; m <= 15; m++) {
        const monthDiv = document.createElement("div");
        monthDiv.className = "wc-month";
        const mName = document.createElement("div");
        mName.className = "wc-month-name";
        mName.textContent = `Month ${m}`;
        const mDays = document.createElement("span");
        mDays.className = "wc-month-days";
        mDays.textContent = `${months[m - 1]} day`;
        mName.appendChild(mDays);
        monthDiv.appendChild(mName);

        const table = document.createElement("table");
        const thead = document.createElement("thead");
        const hrow = document.createElement("tr");
        for (const wday of ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]) {
          const th = document.createElement("th");
          th.textContent = wday;
          hrow.appendChild(th);
        }
        thead.appendChild(hrow);
        table.appendChild(thead);

        const tbody = document.createElement("tbody");
        let row = document.createElement("tr");
        for (let i = 0; i < starts[m - 1]; i++) {
          row.appendChild(document.createElement("td"));
        }
        for (let d = 1; d <= months[m - 1]; d++) {
          if (row.children.length === 7) {
            tbody.appendChild(row);
            row = document.createElement("tr");
          }
          const td = document.createElement("td");
          td.textContent = d;
          const doy = dayOfYear + d - 1;
          const season = astro.seasonOf(year, doy);
          td.classList.add(`season-${season.toLowerCase().replace(/\s+/g, "")}`);
          const w = (starts[m - 1] + d - 1) % 7;
          if (w === 5 || w === 6) td.classList.add("wc-weekend");
          td.addEventListener("click", () => {
            choose(year, m, d);
            updateInfo(d, m);
          });
          row.appendChild(td);
        }
        tbody.appendChild(row);
        table.appendChild(tbody);
        monthDiv.appendChild(table);
        grid.appendChild(monthDiv);
        dayOfYear += months[m - 1];
      }

      overlay.appendChild(panel);

      prev.addEventListener("click", () => build(parseInt(yearInput.value, 10) - 1));
      next.addEventListener("click", () => build(parseInt(yearInput.value, 10) + 1));
      yearInput.addEventListener("change", () => build(parseInt(yearInput.value, 10)));
    }

    function open() {
      let year = 1;
      const match = input.value.match(/\d{1,2}[-.]\d{1,2}[-.](\d{1,4})/);
      if (match) {
        year = parseInt(match[1], 10);
      } else if (Array.isArray(window.WOORLD_TODAY)) {
        year = window.WOORLD_TODAY[0];
      }
      build(year);
      overlay.classList.add("active");
    }

    button.addEventListener("click", open);
    overlay.addEventListener("click", (e) => {
      if (e.target === overlay) overlay.classList.remove("active");
    });
  }

  function enhanceAllWoorldDateInputs() {
    document
      .querySelectorAll('input[name$="_date"], input[data-woorld-date="1"]')
      .forEach((el) => attachWoorldCalendar(el));
  }

  exports.attachWoorldCalendar = attachWoorldCalendar;
  exports.enhanceAllWoorldDateInputs = enhanceAllWoorldDateInputs;
})(window);
