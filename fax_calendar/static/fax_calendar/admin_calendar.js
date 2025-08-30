import {
  monthLengths,
  yearLength,
  toOrdinal,
  fromOrdinal,
  weekday,
} from "/static/fax_calendar/core.js";
import {
  eventsForYear,
  seasonSegments,
  seasonOf,
} from "/static/fax_calendar/astro.js";

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

      const match = input.value.match(/(\d{2})[-.](\d{2})[-.](\d{1,4})/);
      let y = match ? parseInt(match[3], 10) : 2020;
      let m = match ? parseInt(match[2], 10) : 1;
      let d = match ? parseInt(match[1], 10) : 1;
      if (!match && Array.isArray(window.WOORLD_TODAY)) {
        y = window.WOORLD_TODAY[0];
        m = window.WOORLD_TODAY[1];
        d = window.WOORLD_TODAY[2];
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

      function choose(yy, mm, dd) {
        input.value = format(dd, mm, yy);
        close();
      }

      // HEADER
      const header = document.createElement("div");
      header.className = "wc-header";
      const themeWrap = document.createElement("div");
      themeWrap.className = "wc-theme-toggle";
      themeWrap.appendChild(createThemeToggle(overlay));
      header.appendChild(themeWrap);

      const monthCtrl = document.createElement("div");
      monthCtrl.className = "wc-month-ctrl";
      const monthSel = document.createElement("select");
      monthSel.className = "wc-select";
      monthSel.setAttribute("aria-label", "Month");
      for (let i = 1; i <= 15; i++) {
        const opt = document.createElement("option");
        opt.value = i;
        opt.textContent = `Měsíc ${i}`;
        monthSel.appendChild(opt);
      }
      const mArrows = document.createElement("div");
      mArrows.className = "wc-vert-arrows";
      const mUp = document.createElement("button");
      mUp.className = "wc-iconbtn";
      mUp.dataset.act = "month-up";
      mUp.textContent = "↑";
      const mDown = document.createElement("button");
      mDown.className = "wc-iconbtn";
      mDown.dataset.act = "month-down";
      mDown.textContent = "↓";
      mArrows.append(mUp, mDown);
      const monthPill = document.createElement("span");
      monthPill.className = "wc-meta__pill wc-month-len";
      monthCtrl.append(monthSel, mArrows, monthPill);

      const yearCtrl = document.createElement("div");
      yearCtrl.className = "wc-year-ctrl";
      const yearInput = document.createElement("input");
      yearInput.type = "number";
      yearInput.className = "wc-input";
      yearInput.setAttribute("aria-label", "Year");
      const yArrows = document.createElement("div");
      yArrows.className = "wc-vert-arrows";
      const yUp = document.createElement("button");
      yUp.className = "wc-iconbtn";
      yUp.dataset.act = "year-up";
      yUp.textContent = "↑";
      const yDown = document.createElement("button");
      yDown.className = "wc-iconbtn";
      yDown.dataset.act = "year-down";
      yDown.textContent = "↓";
      yArrows.append(yUp, yDown);
      const yScrollBtn = document.createElement("button");
      yScrollBtn.className = "wc-iconbtn";
      yScrollBtn.dataset.act = "year-scroller";
      yScrollBtn.textContent = "◎";
      const yearScroller = document.createElement("div");
      yearScroller.className = "wc-year-scroller";
      yearScroller.style.display = "none";
      yearCtrl.append(yearInput, yArrows, yScrollBtn, yearScroller);

      const yearLenDiv = document.createElement("div");
      yearLenDiv.className = "wc-year-len";
      const yearPill = document.createElement("span");
      yearPill.className = "wc-meta__pill wc-year-days";
      yearLenDiv.appendChild(yearPill);

      header.append(monthCtrl, yearCtrl, yearLenDiv);
      card.appendChild(header);

      // DOY SCRUBBER
      const scrubWrap = document.createElement("div");
      scrubWrap.className = "wc-doy-scrubber";
      const scrubRange = document.createElement("input");
      scrubRange.type = "range";
      scrubRange.min = "1";
      scrubRange.className = "wc-doy-range";
      scrubWrap.appendChild(scrubRange);
      card.appendChild(scrubWrap);

      // TOOLBAR
      const toolbar = document.createElement("div");
      toolbar.className = "wc-toolbar";
      const firstBtn = buildBtn("1. den", () => choose(y, 1, 1));
      firstBtn.dataset.act = "first-day";
      const lastBtn = buildBtn("Poslední den", () => {
        const [yy, mm, dd] = fromOrdinal(y, yearLength(y));
        choose(yy, mm, dd);
      });
      lastBtn.dataset.act = "last-day";
      const resetBtn = buildBtn("Reset", () => choose(2020, 1, 1), "wc-btn--ghost");
      resetBtn.dataset.act = "reset";
      toolbar.append(firstBtn, lastBtn, resetBtn);
      card.appendChild(toolbar);

      // ANCHORS
      const anchorRow = document.createElement("div");
      anchorRow.className = "wc-anchors";
      card.appendChild(anchorRow);

      // SEASON BAR
      const seasonbar = document.createElement("div");
      seasonbar.className = "wc-seasonbar";
      const legend = document.createElement("div");
      legend.className = "wc-season-legend";
      const yearLabel = document.createElement("div");
      yearLabel.className = "wc-yearlabel";
      seasonbar.appendChild(legend);
      seasonbar.appendChild(yearLabel);
      card.appendChild(seasonbar);

      // MONTH SECTION
      const monthSection = document.createElement("section");
      monthSection.className = "wc-month";
      const monthHead = document.createElement("div");
      monthHead.className = "wc-month__head";
      const monthTitle = document.createElement("h3");
      monthTitle.innerHTML = "Měsíc <span class=\"js-month\"></span>";
      const monthDays = document.createElement("div");
      monthDays.className = "wc-month__days";
      monthDays.innerHTML = '<span class="js-monthlen"></span> day';
      monthHead.append(monthTitle, monthDays);
      monthSection.appendChild(monthHead);
      const wHead = document.createElement("div");
      wHead.className = "wc-weekdays";
      ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"].forEach((nm) => {
        const sp = document.createElement("span");
        sp.textContent = nm;
        wHead.appendChild(sp);
      });
      monthSection.appendChild(wHead);
      const grid = document.createElement("div");
      grid.className = "wc-grid";
      monthSection.appendChild(grid);
      card.appendChild(monthSection);

      // FOOTER
      const footer = document.createElement("div");
      footer.className = "wc-footer";
      footer.innerHTML =
        '<div><strong>Datum:</strong> <span class="js-date"></span></div>' +
        '<div><strong>Weekday:</strong> <span class="js-weekday"></span></div>' +
        '<div><strong>Sezóna:</strong> <span class="js-season"></span></div>' +
        '<div><strong>Den v roce:</strong> <span class="js-doy"></span> / <span class="js-yearlen2"></span></div>';
      card.appendChild(footer);

      function clampDay() {
        const months = monthLengths(y);
        const max = months[m - 1];
        if (d > max) d = max;
      }

      function updateHeader() {
        const months = monthLengths(y);
        monthSel.value = String(m);
        monthPill.textContent = `${months[m - 1]} days`;
        yearInput.value = String(y);
        yearPill.textContent = `${yearLength(y)} days`;
      }

      function updateAnchors() {
        anchorRow.innerHTML = "";
        const events = eventsForYear(y);
        const cfg = [
          ["Winter", events.winters, "winter"],
          ["Spring", events.springs, "spring"],
          ["Summer", events.summers, "summer"],
          ["Autumn", events.autumns, "autumn"],
        ];
        cfg.forEach(([label, arr, season]) => {
          const btn = buildBtn(label, () => {
            if (arr.length) choose(arr[0].y, arr[0].m, arr[0].d);
          });
          btn.dataset.season = season;
          if (!arr.length) {
            btn.disabled = true;
            btn.title = "Anchor not present in this year";
          }
          anchorRow.appendChild(btn);
          if (label === "Winter" && arr.length > 1) {
            const btn2 = buildBtn("Winter II", () => {
              choose(arr[1].y, arr[1].m, arr[1].d);
            });
            btn2.dataset.season = "winter2";
            anchorRow.appendChild(btn2);
          }
        });
      }

      function updateSeasonBar() {
        seasonbar.innerHTML = "";
        const yl = yearLength(y);
        const { segs, winterMarks } = seasonSegments(y);
        const clsMap = {
          winter_i: "winter",
          spring: "spring",
          summer: "summer",
          autumn: "autumn",
        };
        segs.forEach((seg) => {
          const div = document.createElement("div");
          div.className = `wc-seasonbar__seg ${clsMap[seg.kind]}`;
          div.style.width = `${((seg.endDoy - seg.startDoy + 1) / yl) * 100}%`;
          seasonbar.appendChild(div);
        });
        winterMarks.forEach((w) => {
          const mark = document.createElement("div");
          mark.className = "wc-seasonbar__mark";
          mark.style.left = `${((w.doy - 0.5) / yl) * 100}%`;
          seasonbar.appendChild(mark);
        });

        seasonbar.appendChild(legend);
        seasonbar.appendChild(yearLabel);

        legend.innerHTML = "";
        const legItems = [
          ["Zima", "winter"],
          ["Jaro", "spring"],
          ["Léto", "summer"],
          ["Podzim", "autumn"],
        ];
        legItems.forEach(([label, cls]) => {
          const sp = document.createElement("span");
          sp.dataset.season = cls;
          sp.textContent = label;
          legend.appendChild(sp);
        });
        if (winterMarks.length === 2) {
          const sp = document.createElement("span");
          sp.dataset.season = "winter2";
          sp.textContent = "Zima II (den)";
          legend.appendChild(sp);
        }

        yearLabel.innerHTML = `Rok <span class="js-year">${y}</span> • <span class="js-yearlen">${yl}</span> dní`;
      }

      function updateMonth() {
        clampDay();
        updateHeader();
        updateAnchors();
        updateSeasonBar();
        grid.innerHTML = "";
        const months = monthLengths(y);
        const offset = weekday(y, m, 1);
        for (let i = 0; i < offset; i++) grid.appendChild(document.createElement("div"));
        for (let dd = 1; dd <= months[m - 1]; dd++) {
          const cell = document.createElement("div");
          cell.className = "wc-day";
          cell.textContent = dd;
          const doy = toOrdinal(y, m, dd);
          const seasonFull = seasonOf(y, doy);
          const seasonMap = {
            "Zima I": "winter",
            "Zima II": "winter",
            Jaro: "spring",
            "Léto": "summer",
            Podzim: "autumn",
          };
          const seasonCls = seasonMap[seasonFull] || "winter";
          cell.classList.add(`season-${seasonCls}`);
          const w = (offset + dd - 1) % 7;
          if (w === 5 || w === 6) cell.classList.add("is-weekend");
          if (
            Array.isArray(window.WOORLD_TODAY) &&
            window.WOORLD_TODAY[0] === y &&
            window.WOORLD_TODAY[1] === m &&
            window.WOORLD_TODAY[2] === dd
          ) {
            cell.classList.add("is-today");
          }
          if (dd === d) cell.classList.add("is-selected");
          cell.addEventListener("click", () => choose(y, m, dd));
          grid.appendChild(cell);
        }
        monthSection.querySelector(".js-month").textContent = m;
        monthSection.querySelector(".js-monthlen").textContent = monthLengths(y)[m - 1];
        updateFooter();
      }

      function updateFooter() {
        const doy = toOrdinal(y, m, d);
        const w = weekday(y, m, d);
        const season = seasonOf(y, doy);
        footer.querySelector(".js-date").textContent = format(d, m, y);
        footer.querySelector(".js-weekday").textContent = WEEKDAY_NAMES[w];
        footer.querySelector(".js-season").textContent = season;
        footer.querySelector(".js-doy").textContent = doy;
        footer.querySelector(".js-yearlen2").textContent = yearLength(y);
        scrubRange.max = yearLength(y);
        scrubRange.value = doy;
      }

      updateMonth();

      scrubRange.addEventListener("input", () => {
        const val = parseInt(scrubRange.value, 10);
        const [_, mm, dd] = fromOrdinal(y, val);
        m = mm;
        d = dd;
        updateMonth();
      });

      // EVENTS
      monthSel.addEventListener("change", () => {
        m = parseInt(monthSel.value, 10);
        updateMonth();
      });
      mUp.addEventListener("click", () => {
        m += 1;
        if (m > 15) {
          m = 1;
          y += 1;
        }
        updateMonth();
      });
      mDown.addEventListener("click", () => {
        m -= 1;
        if (m < 1) {
          m = 15;
          y -= 1;
        }
        updateMonth();
      });

      yearInput.addEventListener("change", () => {
        y = parseInt(yearInput.value, 10);
        updateMonth();
      });
      yUp.addEventListener("click", () => {
        y += 1;
        updateMonth();
      });
      yDown.addEventListener("click", () => {
        y -= 1;
        updateMonth();
      });

      function toggleYearScroller() {
        if (yearScroller.style.display === "block") {
          yearScroller.style.display = "none";
          yearScroller.innerHTML = "";
          return;
        }
        yearScroller.innerHTML = "";
        for (let i = y - 24; i <= y + 24; i++) {
          const btn = document.createElement("button");
          btn.type = "button";
          btn.textContent = `${i} — ${yearLength(i)} days`;
          btn.addEventListener("click", () => {
            y = i;
            yearScroller.style.display = "none";
            yearScroller.innerHTML = "";
            updateMonth();
          });
          yearScroller.appendChild(btn);
        }
        yearScroller.style.display = "block";
      }

      yScrollBtn.addEventListener("click", (e) => {
        e.stopPropagation();
        toggleYearScroller();
      });
      overlay.addEventListener("click", (e) => {
        if (!yearCtrl.contains(e.target)) {
          yearScroller.style.display = "none";
          yearScroller.innerHTML = "";
        }
      });
    }

    btn.addEventListener("click", open);
  }

  function enhanceAllWoorldDateInputs() {
    document
      .querySelectorAll('input[name$="_date"], input[data-woorld-date="1"]')
      .forEach((el) => attachWoorldCalendar(el));
  }

  window.attachWoorldCalendar = attachWoorldCalendar;
  window.enhanceAllWoorldDateInputs = enhanceAllWoorldDateInputs;
