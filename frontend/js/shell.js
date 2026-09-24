import { S } from './state.js';
import { $, esc } from './utils.js';
import { NAV_ITEMS } from './config.js';
import { activeBackend } from './backends/index.js';
import { mgr } from './manager.js';

export function renderShell() {
  $('app').innerHTML = `
  <aside class="fixed left-0 top-0 h-full w-[240px] bg-primary-container flex flex-col py-6 z-40">
    <div class="px-5 mb-8 mt-2">
      <img src="/assets/llmnetops-logo-formal.png" alt="LLMNetOps" class="h-9 brightness-0 invert">
    </div>
    <nav id="sidebar-nav" class="flex-1 px-3 space-y-1 sidebar-scroll overflow-y-auto"></nav>
    <div class="sidebar-mascot shrink-0" aria-hidden="true">
      <img src="/assets/llmnetops-mascot-sidebar.png" alt="" class="mascot-img" draggable="false">
    </div>
    <div class="px-6 pt-4 border-t border-white/10 mt-4">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 shrink-0 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-xs">${esc((S.user || '?').slice(0, 2).toUpperCase())}</div>
        <div class="overflow-hidden flex-1">
          <p class="text-white text-xs font-bold truncate">${esc(S.user || '')}</p>
          <p class="text-white/50 text-[10px] truncate">Network Admin</p>
        </div>
        <button id="logout-btn" title="Keluar" aria-label="Keluar" class="text-white/60 hover:text-white transition-colors">
          <span class="material-symbols-outlined text-[20px]">logout</span>
        </button>
      </div>
    </div>
  </aside>
  <header class="fixed top-0 left-[240px] right-0 h-[56px] bg-surface-container-lowest flex justify-between items-center px-6 z-50 border-b border-outline-variant">
    <nav class="flex items-center text-on-surface-variant text-body-sm">
      <span class="font-bold text-primary mr-2">Console</span>
      <span class="material-symbols-outlined text-[16px] mr-2">chevron_right</span>
      <span id="breadcrumb-page">Dashboard</span>
    </nav>
    <div class="flex items-center gap-4">
      <a href="#settings" id="backend-indicator" title="Backend aktif — ganti di Settings" class="flex items-center gap-2 px-3 py-1 border border-outline-variant rounded-full text-body-sm text-primary hover:bg-surface-container transition-colors"></a>
      <div class="h-8 w-8 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
        <span class="material-symbols-outlined text-on-surface-variant text-lg">account_circle</span>
      </div>
    </div>
  </header>
  <main class="ml-[240px] pt-[56px] min-h-screen bg-background flex flex-col">
    <div id="screen-container" class="flex-1"></div>
    <footer id="app-footer" class="px-6 py-2 text-[11px] text-on-surface-variant flex flex-wrap items-center gap-x-4 gap-y-1 border-t border-outline-variant">
      <span>LLMNetOps &middot; hibah <a href="#about" class="text-primary hover:underline">ISIF Asia</a></span>
      <a href="https://llmnetops.github.io/" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">llmnetops.github.io</a>
      <a href="https://apnic.foundation/projects/llmnetops/" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">apnic.foundation</a>
      <span>Kontak: <a href="mailto:llmnetops@ub.ac.id" class="text-primary hover:underline">llmnetops@ub.ac.id</a></span>
    </footer>
  </main>`;
  renderNav();
  renderBackendIndicator();
  $('logout-btn').onclick = async () => {
    try { await mgr('/auth/logout', { method: 'POST' }); } catch { /* the cookie is cleared server-side; reload either way */ }
    location.reload();
  };
  window.addEventListener('backend-changed', renderBackendIndicator);
}

// Header pill: active backend + reachability. Health is re-probed on every
// render (shell load and backend switch), never on a timer.
export async function renderBackendIndicator() {
  const el = $('backend-indicator');
  if (!el) return;
  const b = activeBackend();
  const pill = (dot, title) => {
    el.innerHTML = `<span class="w-2 h-2 rounded-full ${dot}"></span><span class="font-medium">${esc(b.label)}</span>`;
    el.title = title;
  };
  pill('bg-gray-300', 'Memeriksa koneksi...');
  try {
    const h = await b.health();
    if (activeBackend() !== b) return; // switched while probing
    pill(h.ok ? 'bg-green-500' : 'bg-amber-500', `${b.label} · model ${h.model}${h.detail ? ' · ' + h.detail : ''}`);
  } catch (e) {
    if (activeBackend() !== b) return;
    pill('bg-red-500', `${b.label} tidak terjangkau: ${e.message}`);
  }
}

let _collapsedGroups = new Set();
let _lastActiveGroup; // group of the screen that was active on the previous renderNav() call

export function renderNav() {
  const nav = $('sidebar-nav');
  if (!nav) return;

  const activeItem = NAV_ITEMS.find(i => i.id === S.screen);
  const activeGroup = activeItem?.group;

  // Accordion: navigating into a different group auto-collapses every other
  // named group and opens the active one. Re-renders triggered by manually
  // clicking a group header (same screen, no navigation) skip this reset so
  // the user can still peek into a group without leaving the current page.
  if (activeGroup !== _lastActiveGroup) {
    _collapsedGroups = new Set(NAV_ITEMS.map(i => i.group).filter(Boolean));
    if (activeGroup) _collapsedGroups.delete(activeGroup);
    _lastActiveGroup = activeGroup;
  }

  let lastGroup;
  nav.innerHTML = NAV_ITEMS.map(item => {
    const active = S.screen === item.id;
    const base = 'flex items-center gap-3 px-3 py-2.5 transition-all duration-150 ease-in-out font-label-caps text-label-caps cursor-pointer';
    const cls = active
      ? 'text-surface-container-lowest bg-white/10 border-l-[3px] border-secondary-container'
      : 'text-surface-container-lowest/60 hover:bg-white/5 hover:text-surface-container-lowest border-l-[3px] border-transparent';
    const fill = active ? "font-variation-settings:'FILL' 1;" : '';

    // Consecutive items sharing a group are visually clustered; a group
    // boundary (entering or leaving one) gets a divider, and entering a
    // named group additionally gets a clickable, collapsible label.
    let separator = '';
    if (item.group !== lastGroup) {
      let label = '';
      if (item.group) {
        const collapsed = _collapsedGroups.has(item.group);
        label = `<button data-group-toggle="${esc(item.group)}" class="w-full flex items-center justify-between px-3 py-2.5 text-[10px] font-bold uppercase tracking-wider text-surface-container-lowest/40 hover:text-surface-container-lowest/70 hover:bg-white/5 rounded transition-colors cursor-pointer">
          <span>${esc(item.group)}</span>
          <span class="material-symbols-outlined text-[16px] transition-transform ${collapsed ? '-rotate-90' : ''}">expand_more</span>
        </button>`;
      }
      separator = `<div class="mt-3 pt-2 border-t border-white/10">${label}</div>`;
    }
    lastGroup = item.group;

    const hiddenCls = item.group && _collapsedGroups.has(item.group) ? 'hidden' : '';
    return `${separator}<a class="${base} ${cls} ${hiddenCls}" data-screen="${item.id}">
      <span class="material-symbols-outlined" style="${fill}">${item.icon}</span><span class="flex-1">${item.label}</span>
      ${item.unavailable ? '<span class="text-[9px] font-bold uppercase tracking-wider text-surface-container-lowest/40">soon</span>' : ''}
    </a>`;
  }).join('');

  nav.onclick = e => {
    const toggle = e.target.closest('[data-group-toggle]');
    if (toggle) {
      const g = toggle.dataset.groupToggle;
      if (_collapsedGroups.has(g)) _collapsedGroups.delete(g); else _collapsedGroups.add(g);
      renderNav();
      return;
    }
    const a = e.target.closest('[data-screen]');
    if (a) location.hash = a.dataset.screen;
  };
}
