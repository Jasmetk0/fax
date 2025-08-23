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
  var input = document.getElementById("woorld-date-input");
  if (input) {
    input.addEventListener("change", function () {
      if (!validDate(input.value)) {
        input.setCustomValidity("Neplatné Woorld datum");
      } else {
        input.setCustomValidity("");
      }
    });
  }
  var form = document.getElementById("woorld-date-form");
  if (form) {
    form.addEventListener("submit", function (e) {
      if (e) e.preventDefault();
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
})();
