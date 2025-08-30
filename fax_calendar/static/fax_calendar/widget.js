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

// --- BadgedSelect ---------------------------------------------------------

// Simple custom select component that supports right-aligned badges.
// The widget is keyboard accessible and exposes `.value` and `.onchange`.
class BadgedSelect {
  constructor(opts) {
    opts = opts || {};
    this.options = [];
    this.onchange = null;
    this._value = "";
    this.activeIndex = -1;

    this.el = document.createElement("div");
    this.el.className = "wc-badged-select";

    this.button = document.createElement("div");
    this.button.className = "wc-badged-select__button";
    this.button.tabIndex = 0;
    this.button.setAttribute("role", "button");
    this.button.setAttribute("aria-haspopup", "listbox");
    this.button.setAttribute("aria-expanded", "false");
    if (opts.ariaLabel) this.button.setAttribute("aria-label", opts.ariaLabel);
    this.el.appendChild(this.button);

    this.list = document.createElement("ul");
    this.list.className = "wc-badged-select__list";
    this.list.setAttribute("role", "listbox");
    this.list.tabIndex = -1;
    this.list.hidden = true;
    this.el.appendChild(this.list);

    this.button.addEventListener("click", () => this.toggle());
    this.button.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown" || e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        this.open();
      }
    });

    this.list.addEventListener("click", (e) => {
      const li = e.target.closest("li");
      if (li) {
        this.select(li.dataset.value);
        this.close();
      }
    });

    this.list.addEventListener("keydown", (e) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        this.highlight(this.activeIndex + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.highlight(this.activeIndex - 1);
      } else if (e.key === "Enter") {
        e.preventDefault();
        const li = this.list.children[this.activeIndex];
        if (li) {
          this.select(li.dataset.value);
          this.close();
        }
      } else if (e.key === "Escape") {
        e.preventDefault();
        this.close();
      }
    });

    this._docHandler = (e) => {
      if (!this.el.contains(e.target)) this.close();
    };
  }

  setOptions(options) {
    this.options = options.slice();
    this.list.innerHTML = "";
    options.forEach((opt, idx) => {
      const li = document.createElement("li");
      li.className = "wc-badged-option";
      li.setAttribute("role", "option");
      li.tabIndex = -1;
      li.dataset.value = String(opt.value);
      li.dataset.days = opt.days;
      const labelSpan = document.createElement("span");
      labelSpan.textContent = opt.label;
      const badge = document.createElement("span");
      badge.textContent = opt.days;
      li.append(labelSpan, badge);
      this.list.appendChild(li);
    });
  }

  open() {
    if (!this.list.hidden) return;
    this.list.hidden = false;
    this.button.setAttribute("aria-expanded", "true");
    document.addEventListener("click", this._docHandler);
    const idx = this.options.findIndex((o) => o.value === this._value);
    this.highlight(idx >= 0 ? idx : 0);
    this.list.focus();
  }

  close() {
    if (this.list.hidden) return;
    this.list.hidden = true;
    this.button.setAttribute("aria-expanded", "false");
    document.removeEventListener("click", this._docHandler);
    this.button.focus();
  }

  toggle() {
    if (this.list.hidden) this.open();
    else this.close();
  }

  highlight(idx) {
    const items = Array.from(this.list.children);
    if (!items.length) return;
    if (idx < 0) idx = items.length - 1;
    if (idx >= items.length) idx = 0;
    items.forEach((li) => li.classList.remove("is-active"));
    const li = items[idx];
    li.classList.add("is-active");
    li.focus();
    this.activeIndex = idx;
  }

  select(val) {
    this.value = val;
    if (typeof this.onchange === "function") this.onchange();
  }

  set value(v) {
    this._value = String(v);
    const opt = this.options.find((o) => String(o.value) === this._value);
    if (opt) this.button.textContent = opt.label;
    Array.from(this.list.children).forEach((li) => {
      const sel = li.dataset.value === this._value;
      li.classList.toggle("is-selected", sel);
      li.setAttribute("aria-selected", sel);
    });
  }

  get value() {
    return this._value;
  }
}

window.BadgedSelect = BadgedSelect;
