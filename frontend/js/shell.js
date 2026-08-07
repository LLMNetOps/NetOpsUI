import { S } from './state.js';
import { $, esc } from './utils.js';
import { NAV_ITEMS } from './config.js';

export function renderShell() {
  $('app').innerHTML = `
  <aside class="fixed left-0 top-0 h-full w-[240px] bg-primary-container flex flex-col py-6 z-40">
    <div class="px-5 mb-8 mt-2">
      <img src="/assets/llmnetops-logo-formal.png" alt="LLMNetOps" class="h-9 brightness-0 invert">
    </div>
    <nav id="sidebar-nav" class="flex-1 px-3 space-y-1 sidebar-scroll overflow-y-auto"></nav>
    <div class="px-6 pt-4 border-t border-white/10 mt-4">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-xs">OP</div>
        <div class="overflow-hidden">
          <p class="text-white text-xs font-bold truncate">Operator</p>
          <p class="text-white/50 text-[10px] truncate">Network Admin</p>
        </div>
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
      <div class="flex items-center gap-2 px-3 py-1 bg-green-50 border border-green-100 rounded-full">
        <span class="relative flex h-2 w-2">
          <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
          <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
        </span>
        <span class="font-label-caps text-label-caps text-green-700">SYSTEM ONLINE</span>
      </div>
      <button class="text-on-surface-variant hover:bg-surface-container p-1.5 rounded-full transition-colors">
        <span class="material-symbols-outlined">notifications</span>
      </button>
      <div class="h-8 w-8 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
        <span class="material-symbols-outlined text-on-surface-variant text-lg">account_circle</span>
      </div>
    </div>
  </header>
  <main class="ml-[240px] pt-[56px] min-h-screen bg-background">
    <div id="screen-container"></div>
  </main>`;
  renderNav();
}

export function renderNav() {
  const nav = $('sidebar-nav');
  if (!nav) return;
  nav.innerHTML = NAV_ITEMS.map(item => {
    const active = S.screen === item.id;
    const base = 'flex items-center gap-3 px-3 py-2.5 transition-all duration-150 ease-in-out font-label-caps text-label-caps cursor-pointer';
    const cls = active
      ? 'text-surface-container-lowest bg-white/10 border-l-[3px] border-secondary-container'
      : 'text-surface-container-lowest/60 hover:bg-white/5 hover:text-surface-container-lowest border-l-[3px] border-transparent';
    const fill = active ? "font-variation-settings:'FILL' 1;" : '';
    return `<a class="${base} ${cls}" data-screen="${item.id}">
      <span class="material-symbols-outlined" style="${fill}">${item.icon}</span><span>${item.label}</span>
    </a>`;
  }).join('');
  nav.onclick = e => {
    const a = e.target.closest('[data-screen]');
    if (a) location.hash = a.dataset.screen;
  };
}
