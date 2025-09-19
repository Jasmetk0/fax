(function () {
  "use strict";

  function logPlaceholderAction(event) {
    var target = event.target.closest ? event.target.closest("[data-admin-action]") : null;
    if (!target) {
      return;
    }
    var actionName = target.getAttribute("data-admin-action") || "unknown";
    var sectionTarget = target.closest ? target.closest("[data-admin-section]") : null;
    var sectionName = sectionTarget && sectionTarget.getAttribute
      ? sectionTarget.getAttribute("data-admin-section")
      : "toolbar";
    console.info(
      "[MSA admin] Placeholder action triggered:",
      actionName,
      "section:",
      sectionName || "unknown"
    );
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
