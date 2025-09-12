/**
 * MSA Topbar micro-interakce:
 * - Přidá stín při scrollu (class 'shadow-md') -> lepší čitelnost.
 * - Hotkey "/": fokus na <input name="q"> (vyhledávání).
 * - Esc v search inputu: vyčistí hodnotu.
 * - Dropdown "More": přepíná hidden + aria-expanded; fokus na první položku,
 *   šipky cyklují, klik mimo nebo Esc zavře (Esc vrací fokus na tlačítko).
*/
(function(){
  const header = document.getElementById('msa-topbar');
  const moreBtn = document.getElementById('msa-more-btn');
  const moreMenu = document.getElementById('msa-more-menu');
  const menuItems = moreMenu ? Array.from(moreMenu.querySelectorAll('[role="menuitem"]')) : [];
  const searchInput = document.querySelector('input[name="q"]');

  // Stín po scrollu
  const onScroll = () => {
    if (!header) return;
    if (window.scrollY > 6) {
      header.classList.add('shadow-md');
    } else {
      header.classList.remove('shadow-md');
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll(); // init

  // Hotkey "/": fokusne search (ignoruje, když je focus v inputu/textarea)
  document.addEventListener('keydown', (e) => {
    const tag = (document.activeElement && document.activeElement.tagName) || '';
    if (e.key === '/' && !e.ctrlKey && !e.metaKey && !e.altKey && tag !== 'INPUT' && tag !== 'TEXTAREA') {
      if (searchInput) {
        e.preventDefault();
        searchInput.focus();
      }
    }
  });

  // Esc v search inputu -> clear
  if (searchInput) {
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') {
        searchInput.value = '';
        searchInput.blur();
      }
    });
  }

  // Dropdown "More": toggle + a11y
  const closeMore = (focusBtn = false) => {
    if (moreMenu && moreBtn) {
      moreMenu.classList.add('hidden');
      moreBtn.setAttribute('aria-expanded', 'false');
      if (focusBtn) moreBtn.focus();
    }
  };
  const openMore = () => {
    if (moreMenu && moreBtn) {
      moreMenu.classList.remove('hidden');
      moreBtn.setAttribute('aria-expanded', 'true');
      if (menuItems.length) menuItems[0].focus();
    }
  };
  if (moreBtn && moreMenu) {
    let blurTimer;
    const isInMenuTree = (el) =>
      el && (el === moreMenu || el === moreBtn || moreMenu.contains(el) || moreBtn.contains(el));
    moreBtn.addEventListener('click', () => {
      const isOpen = moreBtn.getAttribute('aria-expanded') === 'true';
      isOpen ? closeMore() : openMore();
    });
    // Zavírání klikem mimo
    document.addEventListener('click', (e) => {
      if (!moreMenu.contains(e.target) && !moreBtn.contains(e.target)) {
        closeMore();
      }
    });
    // Klávesnice v menu
    moreMenu.addEventListener('keydown', (e) => {
      if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
        e.preventDefault();
        const items = menuItems;
        let idx = items.indexOf(document.activeElement);
        if (e.key === 'ArrowDown') {
          idx = (idx + 1) % items.length;
        } else {
          idx = (idx - 1 + items.length) % items.length;
        }
        items[idx].focus();
      } else if (e.key === 'Escape') {
        closeMore(true);
      }
    });
    moreMenu.addEventListener('focusout', () => {
      clearTimeout(blurTimer);
      blurTimer = setTimeout(() => {
        if (!isInMenuTree(document.activeElement)) closeMore();
      }, 0);
    });
    moreBtn.addEventListener('focusout', () => {
      clearTimeout(blurTimer);
      blurTimer = setTimeout(() => {
        if (!isInMenuTree(document.activeElement)) closeMore();
      }, 0);
    });
    // Zavírání klávesou Esc globálně
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && moreBtn.getAttribute('aria-expanded') === 'true') {
        closeMore(true);
      }
    });
  }
})();

// Vysvětlení: čistý vanilla JS bez závislostí; používáme třídu 'hidden' a aria-expanded
// pro přístupnost. Scroll stín přidává class 'shadow-md' nad výchozí 'shadow-sm'.
