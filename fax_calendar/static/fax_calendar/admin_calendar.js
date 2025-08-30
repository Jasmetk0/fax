import {
  monthLengths,
  yearLength,
  toOrdinal,
  fromOrdinal,
  weekday,
} from "/static/fax_calendar/core.js";
import { seasonSegments, seasonOf } from "/static/fax_calendar/astro.js";

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

      function selectDate(yy, mm, dd) {
        y = yy;
        m = mm;
        d = dd;
        updateMonth();
      }

      // HEADER
      const header = document.createElement("div");
      header.className = "wc-header";
      const themeWrap = document.createElement("div");
      themeWrap.className = "wc-theme-toggle";
      themeWrap.appendChild(createThemeToggle(overlay));

      const monthCtrl = document.createElement("div");
      monthCtrl.className = "wc-month-ctrl";
      const monthSel = document.createElement("select");
      monthSel.className = "wc-select wc-select--badged";
      monthSel.setAttribute("aria-label", "Month");

        function populateMonthSelect(year) {
          monthSel.innerHTML = "";
          monthLengths(year).forEach((days, idx) => {
            const opt = document.createElement("option");
            opt.value = idx + 1;
            opt.textContent = `Měsíc ${idx + 1}`;
            opt.dataset.days = days;
            opt.className = "wc-badge";
            monthSel.appendChild(opt);
          });
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
        const yearSel = document.createElement("select");
        yearSel.className = "wc-select wc-select--badged";
        yearSel.setAttribute("aria-label", "Year");
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
        yearCtrl.append(yearSel, yArrows);

        function populateYearSelect() {
          yearSel.innerHTML = "";
          for (let i = 1; i <= 2100; i++) {
            const opt = document.createElement("option");
            opt.value = i;
            opt.textContent = i;
            opt.dataset.days = yearLength(i);
            opt.className = "wc-badge";
            yearSel.appendChild(opt);
          }
        }

        populateYearSelect();

      const yearLenDiv = document.createElement("div");
      yearLenDiv.className = "wc-year-len";
      const yearPill = document.createElement("span");
      yearPill.className = "wc-meta__pill wc-year-days";
      yearLenDiv.appendChild(yearPill);

      header.append(monthCtrl, yearCtrl, yearLenDiv, themeWrap);
      card.appendChild(header);

      // DOY SCRUBBER
      const scrubWrap = document.createElement("div");
      scrubWrap.className = "wc-doy-scrubber";
      const scrubRange = document.createElement("input");
      scrubRange.type = "range";
      scrubRange.className = "wc-doy-range";
      scrubWrap.appendChild(scrubRange);
      const scrubTrack = document.createElement("div");
      scrubTrack.className = "wc-doy-track";
      scrubWrap.appendChild(scrubTrack);
      card.appendChild(scrubWrap);

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

      // FOOTER
      const footer = document.createElement("div");
      footer.className = "wc-footer";
      const footerInfo = document.createElement("div");
      footerInfo.className = "wc-footer-info";
      footerInfo.innerHTML =
        '<div><strong>Date:</strong> <span class="js-date"></span></div>' +
        '<div><strong>Weekday:</strong> <span class="js-weekday"></span></div>' +
        '<div><strong>Season:</strong> <span class="js-season"></span></div>' +
        '<div><strong>Day in year:</strong> <span class="js-doy"></span> / <span class="js-yearlen2"></span></div>';
      const resetBtn = buildBtn(
        "Reset",
        () => selectDate(2020, 1, 1),
        "wc-btn--ghost",
      );
      resetBtn.dataset.act = "reset";
      const confirmBtn = buildBtn("Confirm", () => choose(y, m, d), "wc-btn--primary");
      confirmBtn.dataset.act = "confirm";
      footer.append(footerInfo, resetBtn, confirmBtn);

      const bodyWrap = document.createElement("div");
      bodyWrap.className = "wc-body";
      bodyWrap.append(monthSection, footer);
      card.appendChild(bodyWrap);

      function clampDay() {
        const months = monthLengths(y);
        const max = months[m - 1];
        if (d > max) d = max;
      }

        function updateHeader() {
          populateMonthSelect(y);
          const months = monthLengths(y);
          monthSel.value = String(m);
          monthPill.textContent = `${months[m - 1]} days`;
          yearSel.value = String(y);
          yearPill.textContent = `${yearLength(y)} days`;
        }

      function renderDoyTrack(yy) {
        const yl = yearLength(yy);
        scrubRange.min = "1";
        scrubRange.max = String(yl);
        scrubRange.step = "1";
        scrubTrack.innerHTML = "";
        const { segs } = seasonSegments(yy);
        segs.forEach((seg) => {
          const div = document.createElement("div");
          div.className = `wc-doy-track__seg ${seg.kind}`;
          const len = seg.endDoy - seg.startDoy + 1;
          div.style.setProperty("--l", `${((seg.startDoy - 1) / yl) * 100}%`);
          div.style.setProperty("--w", `${(len / yl) * 100}%`);
          scrubTrack.appendChild(div);
        });
        const months = monthLengths(yy);
        let cum = 0;
        for (let i = 0; i < months.length - 1; i++) {
          cum += months[i];
          const mark = document.createElement("div");
          mark.className = "wc-doy-track__mark";
          mark.style.left = `${(cum / yl) * 100}%`;
          scrubTrack.appendChild(mark);
        }
      }

      let trackYear = null;

      function updateMonth() {
        clampDay();
        updateHeader();
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
            Winter: "winter",
            Spring: "spring",
            Summer: "summer",
            Autumn: "autumn",
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
          cell.addEventListener("click", () => selectDate(y, m, dd));
          grid.appendChild(cell);
        }
        monthSection.querySelector(".js-month").textContent = m;
        monthSection.querySelector(".js-monthlen").textContent = monthLengths(y)[m - 1];
        if (trackYear !== y) {
          renderDoyTrack(y);
          trackYear = y;
        }
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
        scrubRange.value = doy;
      }

      updateMonth();

      scrubRange.addEventListener("input", () => {
        const doy = Number(scrubRange.value);
        const [yy, mm, dd] = fromOrdinal(y, doy);
        selectDate(yy, mm, dd);
      });

      scrubTrack.addEventListener("click", (e) => {
        const rect = scrubTrack.getBoundingClientRect();
        const p = (e.clientX - rect.left) / rect.width;
        const yl = yearLength(y);
        const doy = Math.min(yl, Math.max(1, Math.round(p * yl)));
        scrubRange.value = String(doy);
        const [yy, mm, dd] = fromOrdinal(y, doy);
        selectDate(yy, mm, dd);
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

        yearSel.addEventListener("change", () => {
          y = parseInt(yearSel.value, 10);
          updateMonth();
        });
        yUp.addEventListener("click", () => {
          y = Math.min(2100, y + 1);
          updateMonth();
        });
      yDown.addEventListener("click", () => {
        y = Math.max(1, y - 1);
        updateMonth();
      });

      window.addEventListener("resize", () => renderDoyTrack(y));
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
