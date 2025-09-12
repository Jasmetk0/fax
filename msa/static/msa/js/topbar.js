// msa/static/msa/js/topbar.js
(function () {
  const header = document.getElementById("msa-topbar");
  const moreBtn = document.getElementById("msa-more-btn");
  const moreMenu = document.getElementById("msa-more-menu");
  const menuItems = moreMenu ? Array.from(moreMenu.querySelectorAll('[role="menuitem"]')) : [];
  const searchInput = document.querySelector('input[name="q"]');

  // 1) Stín při scrollu
  const onScroll = () => {
    if (!header) return;
    header.classList.toggle("shadow-md", window.scrollY > 6);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();

  // 2) "/" → fokus na vyhledávání (pokud nejsi v input/textarea a nejsou modifikátory)
  document.addEventListener("keydown", (e) => {
    const tag = (document.activeElement && document.activeElement.tagName) || "";
    if (e.key === "/" && !e.ctrlKey && !e.metaKey && !e.altKey && tag !== "INPUT" && tag !== "TEXTAREA") {
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    }
  });

  // 3) Esc v search inputu → clear + blur
  if (searchInput) {
    searchInput.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        searchInput.value = "";
        searchInput.blur();
      }
    });
  }

  // 4) Dropdown "More"
  if (moreBtn && moreMenu) {
    const closeMore = (focusBtn = false) => {
      moreMenu.classList.add("hidden");
      moreBtn.setAttribute("aria-expanded", "false");
      if (focusBtn) moreBtn.focus();
    };
    const openMore = () => {
      moreMenu.classList.remove("hidden");
      moreBtn.setAttribute("aria-expanded", "true");
      if (menuItems.length) menuItems[0].focus();
    };
    const isOpen = () => moreBtn.getAttribute("aria-expanded") === "true";
    const inTree = (el) => el && (el === moreMenu || el === moreBtn || moreMenu.contains(el) || moreBtn.contains(el));

    moreBtn.addEventListener("click", () => (isOpen() ? closeMore() : openMore()));

    // Klik mimo → zavřít
    document.addEventListener("click", (e) => {
      if (!inTree(e.target)) closeMore();
    });

    // Klávesy v menu: šipky cyklují, Esc zavře
    moreMenu.addEventListener("keydown", (e) => {
      if (!menuItems.length) return;
      if (e.key === "ArrowDown" || e.key === "ArrowUp") {
        e.preventDefault();
        let i = menuItems.indexOf(document.activeElement);
        i = i < 0 ? 0 : i;
        i = e.key === "ArrowDown" ? (i + 1) % menuItems.length : (i - 1 + menuItems.length) % menuItems.length;
        menuItems[i].focus();
      } else if (e.key === "Escape") {
        closeMore(true);
      }
    });

    // Globální Esc, pokud je menu otevřené
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && isOpen()) closeMore(true);
    });

    // Ztráta fokusu celé větve → zavřít
    let blurTimer;
    const scheduleBlurCheck = () => {
      clearTimeout(blurTimer);
      blurTimer = setTimeout(() => {
        if (!inTree(document.activeElement)) closeMore();
      }, 0);
    };
    moreMenu.addEventListener("focusout", scheduleBlurCheck);
    moreBtn.addEventListener("focusout", scheduleBlurCheck);
  }
})();
