(function () {
  "use strict";

  function getBodyFlag(attribute) {
    var body = document.body;
    if (!body) {
      return null;
    }
    return body.getAttribute(attribute);
  }

  function logAdminIntent(event) {
    var target = event.target;
    if (!target || !target.closest) {
      return;
    }
    var actionTarget = target.closest("[data-admin-action]");
    if (!actionTarget) {
      return;
    }
    var actionName = actionTarget.getAttribute("data-admin-action") || "unknown";
    var section = actionTarget.closest("[data-admin-section]");
    var sectionName = section && section.getAttribute ? section.getAttribute("data-admin-section") : "toolbar";
    var mode = getBodyFlag("data-admin-readonly") === "true" ? "read-only" : "interactive";
    console.info(
      "[MSA admin] Action trigger:",
      actionName,
      "section:",
      sectionName || "unknown",
      "mode:",
      mode
    );
  }

  function getCookie(name) {
    var cookieValue = null;
    if (document.cookie && document.cookie !== "") {
      var cookies = document.cookie.split(";");
      for (var i = 0; i < cookies.length; i += 1) {
        var cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === name + "=") {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function getCsrfToken() {
    return getCookie("csrftoken");
  }

  function getSectionName(element) {
    if (!element) {
      return "toolbar";
    }
    if (element.getAttribute && element.getAttribute("data-admin-section")) {
      return element.getAttribute("data-admin-section") || "toolbar";
    }
    if (element.closest) {
      var ancestor = element.closest("[data-admin-section]");
      if (ancestor && ancestor.getAttribute) {
        return ancestor.getAttribute("data-admin-section") || "toolbar";
      }
    }
    return "toolbar";
  }

  function getToastContainer() {
    return document.getElementById("msa-toast-container");
  }

  function showToast(message, type) {
    if (!message) {
      return;
    }
    var container = getToastContainer();
    if (!container) {
      return;
    }
    var toast = document.createElement("div");
    toast.setAttribute("role", "alert");
    toast.className =
      "pointer-events-auto rounded-md px-4 py-2 text-sm shadow-lg ring-1 ring-black/20 transition-opacity duration-200";
    var toneClass = "bg-slate-900 text-slate-100";
    if (type === "success") {
      toneClass = "bg-emerald-600 text-white";
    } else if (type === "error") {
      toneClass = "bg-rose-600 text-white";
    }
    toast.className += " " + toneClass;
    toast.textContent = message;
    container.appendChild(toast);
    window.setTimeout(function () {
      toast.classList.add("opacity-0");
    }, 3500);
    window.setTimeout(function () {
      if (toast.parentNode) {
        toast.parentNode.removeChild(toast);
      }
    }, 4200);
  }

  function handleAdminFormSubmit(event) {
    var form = event.target;
    if (!form || form.getAttribute("data-admin-enhance") !== "fetch") {
      return;
    }
    event.preventDefault();

    var formData = new FormData(form);
    var actionName = formData.get("action") || "";
    var sectionName = getSectionName(form);
    var submitButton = form.querySelector("button[type='submit']");
    if (submitButton) {
      submitButton.disabled = true;
      submitButton.classList.add("opacity-70");
    }

    var csrfToken = getCsrfToken();
    var headers = {
      Accept: "application/json",
      "X-Requested-With": "XMLHttpRequest",
    };
    if (csrfToken) {
      headers["X-CSRFToken"] = csrfToken;
    }

    var url = form.getAttribute("action") || form.action || window.location.href;

    fetch(url, {
      method: "POST",
      headers: headers,
      body: formData,
    })
      .then(function (response) {
        return response
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            return { response: response, data: data };
          });
      })
      .then(function (result) {
        var response = result.response;
        var data = result.data || {};
        var ok = !!data.ok && response.ok;
        var message = "";
        if (ok && data.message) {
          message = data.message;
        } else if (!ok && data.error) {
          message = data.error;
        } else if (response.ok) {
          message = actionName ? "Action '" + actionName + "' accepted" : "Action accepted";
        } else {
          message = "Action failed (" + response.status + ")";
        }
        showToast(message, ok ? "success" : "error");
        console.info("[MSA admin] Action response:", {
          action: actionName || "unknown",
          section: sectionName || "unknown",
          ok: response.ok,
          status: response.status,
          payload: data,
        });
      })
      .catch(function (error) {
        console.error("[MSA admin] Action fetch failed:", actionName || "unknown", error);
        showToast("Chyba při odeslání akce.", "error");
      })
      .then(function () {
        if (submitButton) {
          submitButton.disabled = false;
          submitButton.classList.remove("opacity-70");
        }
      });
  }

  document.addEventListener("pointerdown", logAdminIntent, true);
  document.addEventListener("click", logAdminIntent, true);
  document.addEventListener("submit", handleAdminFormSubmit);
})();
