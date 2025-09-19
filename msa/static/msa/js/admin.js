(function () {
  "use strict";

  function logPlaceholderAction(event) {
    var target = event.target.closest ? event.target.closest("[data-admin-action]") : null;
    if (!target) {
      return;
    }
    var actionName = target.getAttribute("data-admin-action") || "unknown";
    console.info("[MSA admin] Placeholder action triggered:", actionName);
  }

  document.addEventListener(
    "pointerdown",
    function (event) {
      logPlaceholderAction(event);
    },
    true
  );

  document.addEventListener(
    "click",
    function (event) {
      logPlaceholderAction(event);
    },
    true
  );
})();
