(function () {
  function daysInMonth(month) {
    return month % 2 === 1 ? 29 : 28;
  }
  function validDate(val) {
    var m = val.match(/^(\d{1,2})\/(\d{1,2})\/(\d{1,4})$/);
    if (!m) return false;
    var d = parseInt(m[1], 10);
    var mo = parseInt(m[2], 10);
    if (mo < 1 || mo > 15) return false;
    var max = daysInMonth(mo);
    return d >= 1 && d <= max;
  }
  document.addEventListener("change", function (e) {
    var input = e.target.closest(".woorld-date-input");
    if (input) {
      if (!validDate(input.value)) {
        input.setCustomValidity("Neplatné Woorld datum");
      } else {
        input.setCustomValidity("");
      }
    }
  });

  document.addEventListener("change", function (e) {
    var form = e.target.closest("#woorld-date-form");
    if (form) {
      var data = new FormData(form);
      fetch(form.action, {
        method: "POST",
        headers: { "X-Requested-With": "XMLHttpRequest" },
        body: data,
      });
    }
  });
})();
