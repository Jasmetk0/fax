(function () {
  var core = window.woorldCore;

  function validate(val) {
    var m = val.match(/^(\d{1,2})[-.](\d{1,2})[-.](\d{1,4})$/);
    if (!m) return "Neplatné Woorld datum";
    var d = parseInt(m[1], 10);
    var mo = parseInt(m[2], 10);
    var y = parseInt(m[3], 10);
    if (mo < 1 || mo > 15) return "Měsíc musí být 1–15";
    var ml = core.monthLengths(y);
    var max = ml[mo - 1];
    if (d < 1 || d > max) return "Month " + mo + " has " + max + " days in year " + y;
    return "";
  }

  document.addEventListener("change", function (e) {
    var input = e.target.closest(".woorld-date-input");
    if (input) {
      var err = validate(input.value);
      if (err) input.setCustomValidity(err);
      else input.setCustomValidity("");
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
