// Global widget registry – additional widgets can push into this array
window.HOME_WIDGETS = window.HOME_WIDGETS || [
  { id: 'home', href: '/', label: 'Domů', icon: '🏠', defaultSize: 'M', desc: 'Domů' },
  { id: 'wiki', href: '/wiki/', label: 'Wiki', icon: '📚', defaultSize: 'M', desc: 'Encyklopedie FAX' },
  { id: 'maps', href: '/maps/', label: 'Mapy', icon: '🗺️', defaultSize: 'M', desc: 'Leaflet mapy' },
  { id: 'sport', href: '/livesport/', label: 'Sport', icon: '🏅', defaultSize: 'M', desc: 'LiveSport' },
  { id: 'msa', href: '/msa/', label: 'MSA Squash', icon: '🎾', defaultSize: 'M', desc: 'MSA Squash Tour' },
  { id: 'mma', href: '/mma/', label: 'MMA', icon: '🥊', defaultSize: 'M', desc: 'MMA portál' }
];

window.initHomeWidgets = function() {
  const REG = window.HOME_WIDGETS;
  const REG_MAP = Object.fromEntries(REG.map(r => [r.id, r]));
  const KEY = 'home.widgets.v1';
  const container = document.getElementById('widgets');
  const panel = document.getElementById('widgets-panel');
  const live = document.getElementById('widgets-live');
  let state = load();
  render();

  function load() {
    try {
      const data = JSON.parse(localStorage.getItem(KEY));
      if (data && Array.isArray(data.items)) {
        const items = [];
        data.items.forEach(it => {
          const id = (it.id || '').toLowerCase();
          if (REG_MAP[id] && !items.find(x => x.id === id)) items.push({ id, size: it.size || REG_MAP[id].defaultSize });
        });
        if (items.length) return items;
      }
    } catch (_) {}
    const items = [];
    container.querySelectorAll('[data-id]').forEach(el => {
      const id = (el.dataset.id || '').toLowerCase();
      if (REG_MAP[id] && !items.find(x => x.id === id)) items.push({ id, size: REG_MAP[id].defaultSize });
    });
    save(items);
    return items;
  }

  function save(items) {
    try { localStorage.setItem(KEY, JSON.stringify({ items, version: 1 })); } catch (_) {}
  }

  function render() {
    container.innerHTML = '';
    state.forEach(it => {
      const reg = REG_MAP[it.id];
      if (!reg) return;
      const a = document.createElement('a');
      a.href = reg.href;
      a.dataset.id = reg.id;
      a.role = 'listitem';
      a.draggable = true;
      a.className = 'group relative rounded-2xl border border-slate-200 bg-white p-5 shadow-soft transition hover:shadow-lg focus:shadow-lg dark:border-slate-800 dark:bg-slate-900';
      a.innerHTML = `<button class="widget-remove absolute right-2 top-2 hidden h-6 w-6 items-center justify-center rounded-full bg-slate-200 text-slate-600 hover:bg-red-500 hover:text-white focus:bg-red-500 focus:text-white group-hover:flex group-focus-within:flex" aria-label="Odebrat">×</button>
        <div class="mb-1 text-sm text-slate-500">${reg.icon} ${reg.label}</div>
        <div class="font-medium">${reg.desc}</div>
        <div class="mt-4 text-xs text-slate-500">Aktualizováno…</div>`;
      container.appendChild(a);
    });
    const addBtn = document.createElement('button');
    addBtn.id = 'widgets-add';
    addBtn.type = 'button';
    addBtn.className = 'rounded-2xl border-2 border-dashed border-slate-300 bg-white p-5 text-left text-slate-500 shadow-soft transition hover:border-brand-400 hover:text-slate-700 hover:shadow-lg dark:border-slate-700 dark:bg-slate-900 dark:hover:border-brand-400 dark:hover:text-slate-200';
    addBtn.textContent = '＋ Přidat widget';
    container.appendChild(addBtn);
    document.getElementById('widgets-empty')?.classList.toggle('hidden', state.length !== 0);
    bind();
  }

  function bind() {
    let dragId = null;
    let wasDrag = false;
    container.querySelectorAll('[data-id]').forEach(tile => {
      tile.addEventListener('dragstart', e => {
        dragId = tile.dataset.id;
        tile.classList.add('opacity-50');
        wasDrag = true;
      });
      tile.addEventListener('dragend', () => {
        tile.classList.remove('opacity-50');
        dragId = null;
        setTimeout(() => { wasDrag = false; }, 50);
      });
      tile.addEventListener('dragover', e => { e.preventDefault(); });
      tile.addEventListener('dragenter', e => {
        if (tile.dataset.id !== dragId) tile.classList.add('widget-placeholder');
      });
      tile.addEventListener('dragleave', () => tile.classList.remove('widget-placeholder'));
      tile.addEventListener('drop', e => {
        e.preventDefault();
        tile.classList.remove('widget-placeholder');
        const targetId = tile.dataset.id;
        if (dragId && targetId && dragId !== targetId) {
          const from = state.findIndex(i => i.id === dragId);
          const to = state.findIndex(i => i.id === targetId);
          const [m] = state.splice(from, 1);
          state.splice(to, 0, m);
          save(state);
          render();
          liveMsg(REG_MAP[m.id].label + ' přesunuto');
        }
      });
      tile.addEventListener('click', e => {
        if (wasDrag) { e.preventDefault(); wasDrag = false; }
      });
      tile.querySelector('.widget-remove').addEventListener('click', e => {
        e.preventDefault(); e.stopPropagation();
        const id = tile.dataset.id;
        const idx = state.findIndex(i => i.id === id);
        const removed = state.splice(idx, 1)[0];
        save(state);
        render();
        showUndo(id, removed, idx);
      });
      tile.addEventListener('keydown', e => {
        const id = tile.dataset.id;
        const idx = state.findIndex(i => i.id === id);
        if ((e.ctrlKey || e.metaKey) && ['ArrowLeft','ArrowUp','ArrowRight','ArrowDown'].includes(e.key)) {
          e.preventDefault();
          let newIdx = idx;
          if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') newIdx = Math.max(0, idx - 1);
          else newIdx = Math.min(state.length - 1, idx + 1);
          if (newIdx !== idx) {
            const [m] = state.splice(idx, 1);
            state.splice(newIdx, 0, m);
            save(state);
            render();
            container.querySelector(`[data-id="${id}"]`)?.focus();
            liveMsg(REG_MAP[id].label + ' přesunuto');
          }
        } else if (['Delete','Backspace'].includes(e.key)) {
          e.preventDefault();
          tile.querySelector('.widget-remove').click();
        }
      });
    });
    const addBtn = document.getElementById('widgets-add');
    addBtn.addEventListener('click', e => {
      e.preventDefault(); e.stopPropagation();
      openPanel(addBtn);
    });
  }

  function openPanel(btn) {
    panel.innerHTML = '';
    const search = document.createElement('input');
    search.type = 'text';
    search.placeholder = 'Filtrovat...';
    search.className = 'mb-2 w-full rounded-md border border-slate-300 px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-800';
    panel.appendChild(search);
    const list = document.createElement('div');
    panel.appendChild(list);
    function renderList() {
      list.innerHTML = '';
      const q = search.value.toLowerCase();
      REG.forEach(r => {
        if (q && !r.label.toLowerCase().includes(q)) return;
        const exists = state.some(i => i.id === r.id);
        const b = document.createElement('button');
        b.className = `flex w-full items-center justify-between rounded-lg px-3 py-2 text-left ${exists ? 'opacity-50 cursor-not-allowed' : 'hover:bg-slate-100 dark:hover:bg-slate-800'}`;
        b.dataset.id = r.id;
        b.innerHTML = `<span>${r.icon} ${r.label}</span>${exists ? '<span class="text-xs">Přidáno</span>' : ''}`;
        b.disabled = exists;
        if (!exists) b.addEventListener('click', () => {
          state.push({ id: r.id, size: r.defaultSize });
          save(state);
          render();
          close();
        });
        list.appendChild(b);
      });
    }
    renderList();
    search.addEventListener('input', renderList);
    const rect = btn.getBoundingClientRect();
    const width = 260;
    let left = rect.left + window.scrollX;
    if (left + width > window.innerWidth) left = rect.right + window.scrollX - width;
    panel.style.position = 'absolute';
    panel.style.top = rect.bottom + window.scrollY + 8 + 'px';
    panel.style.left = left + 'px';
    panel.style.width = width + 'px';
    panel.classList.remove('hidden');
    function outside(e){ if (!panel.contains(e.target) && e.target !== btn) close(); }
    function esc(e){ if (e.key === 'Escape') close(); }
    document.addEventListener('click', outside);
    document.addEventListener('keydown', esc);
    function close(){ panel.classList.add('hidden'); document.removeEventListener('click', outside); document.removeEventListener('keydown', esc); }
  }

  function showUndo(id, item, index) {
    const div = document.createElement('div');
    div.className = 'toast';
    div.innerHTML = `Dlaždice odebrána. <button class="underline">Zpět</button>`;
    document.body.appendChild(div);
    const timer = setTimeout(() => div.remove(), 5000);
    div.querySelector('button').addEventListener('click', () => {
      clearTimeout(timer);
      div.remove();
      state.splice(index, 0, item);
      save(state);
      render();
    });
  }

  function liveMsg(msg){
    if (!live) return;
    live.textContent = '';
    setTimeout(() => { live.textContent = msg; }, 0);
  }
};
