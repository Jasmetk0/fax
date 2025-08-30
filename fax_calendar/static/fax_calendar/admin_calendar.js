(function (exports) {
  const core = window.woorldCore;

  function yearLength(y) {
    return core.monthLengths(y).reduce((a, b) => a + b, 0);
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
      button.textContent = "📅"; // calendar emoji
      button.className = "woorld-calendar-btn";
      input.insertAdjacentElement("afterend", button);
    }

    const overlay = document.createElement("div");
    overlay.className = "woorld-calendar-overlay";
    document.body.appendChild(overlay);

    function build(year) {
      overlay.innerHTML = "";
      const months = core.monthLengths(year);
      const anchors = core.anchors(year);
      const starts = startWeekdays(year, months);
      let dayOfYear = 1;

      const panel = document.createElement("div");
      panel.className = "woorld-calendar";

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
      header.append(prev, yearInput, next);
      panel.appendChild(header);

      const grid = document.createElement("div");
      grid.className = "wc-month-grid";
      panel.appendChild(grid);

      for (let m = 1; m <= 15; m++) {
        const monthDiv = document.createElement("div");
        monthDiv.className = "wc-month";
        const mName = document.createElement("div");
        mName.className = "wc-month-name";
        mName.textContent = `Month ${m}`;
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
          for (const [key, val] of Object.entries(anchors)) {
            if (val === doy) {
              td.classList.add("wc-anchor");
              td.title = key.replace("_", " ");
            }
          }
          td.addEventListener("click", () => {
            input.value = format(d, m, year);
            overlay.classList.remove("active");
          });
          row.appendChild(td);
        }
        tbody.appendChild(row);
        table.appendChild(tbody);
        monthDiv.appendChild(table);
        grid.appendChild(monthDiv);
        dayOfYear += months[m - 1];
      }

      const todayBtn = document.createElement("button");
      todayBtn.type = "button";
      todayBtn.className = "wc-today";
      todayBtn.textContent = "Today";
      todayBtn.addEventListener("click", () => {
        const t = window.WOORLD_TODAY || [1, 1, 1];
        build(t[0]);
        input.value = format(t[2], t[1], t[0]);
        overlay.classList.remove("active");
      });
      panel.appendChild(todayBtn);

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
