(function () {
  function daysInMonth(month) {
    return month % 2 === 1 ? 29 : 28;
  }
  function pad(num) {
    return num < 10 ? "0" + num : String(num);
  }
  function validDate(val) {
    var m = val.match(/^(\d{1,2})\/(\d{1,2})\/(\d{1,4})$/);
    if (!m) return false;
    var d = parseInt(m[1], 10);
    var mo = parseInt(m[2], 10);
    var max = daysInMonth(mo);
    return mo >= 1 && mo <= 15 && d >= 1 && d <= max;
  }
  function buildPicker(input) {
    var picker = document.createElement("div");
    picker.className = "woorld-picker";
    var nav = document.createElement("div");
    nav.className = "wp-nav";
    var prev = document.createElement("button");
    prev.type = "button";
    prev.textContent = "<";
    var next = document.createElement("button");
    next.type = "button";
    next.textContent = ">";
    var mSel = document.createElement("select");
    for (var i = 1; i <= 15; i++) {
      var opt = document.createElement("option");
      opt.value = i;
      opt.textContent = pad(i);
      mSel.appendChild(opt);
    }
    var yInp = document.createElement("input");
    yInp.type = "number";
    yInp.min = "1";
    yInp.className = "wp-year";
    nav.appendChild(prev);
    nav.appendChild(mSel);
    nav.appendChild(yInp);
    nav.appendChild(next);
    picker.appendChild(nav);
    var days = document.createElement("div");
    days.className = "wp-days";
    picker.appendChild(days);
    input.parentNode.classList.add("woorld-wrapper");
    input.parentNode.insertBefore(picker, input.nextSibling);
    picker.style.display = "block";
    function renderDays() {
      days.innerHTML = "";
      var max = daysInMonth(parseInt(mSel.value, 10));
      for (var d = 1; d <= max; d++) {
        (function (day) {
          var cell = document.createElement("div");
          cell.className = "wp-day";
          cell.textContent = pad(day);
          cell.addEventListener("click", function () {
            input.value = pad(day) + "/" + pad(parseInt(mSel.value, 10)) + "/" + yInp.value;
            input.dispatchEvent(new Event("change"));
          });
          days.appendChild(cell);
        })(d);
      }
    }
    prev.addEventListener("click", function () {
      var m = parseInt(mSel.value, 10) - 1;
      if (m < 1) m = 15;
      mSel.value = m;
      renderDays();
    });
    next.addEventListener("click", function () {
      var m = parseInt(mSel.value, 10) + 1;
      if (m > 15) m = 1;
      mSel.value = m;
      renderDays();
    });
    mSel.addEventListener("change", renderDays);
    input.addEventListener("focus", function () {
      var m = input.value.match(/^(\d{1,2})\/(\d{1,2})\/(\d{1,4})$/);
      if (m) {
        mSel.value = parseInt(m[2], 10);
        yInp.value = parseInt(m[3], 10);
      }
      renderDays();
    });
    renderDays();
  }
  document.addEventListener("DOMContentLoaded", function () {
    var inputs = document.querySelectorAll("[data-woorld-datepicker]");
    inputs.forEach(function (inp) {
      inp.addEventListener("change", function () {
        if (!validDate(inp.value)) {
          inp.setCustomValidity("Neplatné Woorld datum");
        } else {
          inp.setCustomValidity("");
        }
      });
      buildPicker(inp);
    });
    var form = document.getElementById("woorld-date-form");
    if (form) {
      form.addEventListener("submit", function (e) {
        e.preventDefault();
        var input = form.querySelector("#woorld-date-input");
        if (input && !validDate(input.value)) {
          input.setCustomValidity("Neplatné Woorld datum");
          input.reportValidity();
          return;
        }
        var data = new FormData(form);
        var endpoint = form.dataset.endpoint || form.action;
        var csrf = form.querySelector('[name=csrfmiddlewaretoken]').value;
        fetch(endpoint, {
          method: "POST",
          headers: {
            "X-Requested-With": "XMLHttpRequest",
            "X-CSRFToken": csrf,
          },
          body: data,
        })
          .then(function (resp) {
            return resp.json();
          })
          .then(function (data) {
            if (data.error) {
              alert(data.error);
            } else if (data.value && input) {
              input.value = data.value;
            }
          });
      });
    }
  });
})();
