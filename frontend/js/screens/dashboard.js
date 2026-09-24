import { $, esc, cardHtml, pageHeader, loadingHtml, fmtFullDateTime } from '../utils.js';
import { NAV_ITEMS } from '../config.js';
import { activeBackend } from '../backends/index.js';

function emptyBody(msg) {
  return `<div class="h-full flex items-center justify-center"><p class="text-body-sm text-on-surface-variant text-center">${msg}</p></div>`;
}

function statCard(label, body) {
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
    <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">${label}</p>
    ${body}
  </div>`;
}

export async function screenDashboard(c) {
  const backend = activeBackend();
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    ${pageHeader(
      'Overview',
      `Ringkasan backend aktif (<b>${esc(backend.label)}</b>) dan percakapan terakhir.`,
      `<button id="btn-dash-refresh" class="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg text-body-sm font-medium text-primary hover:bg-surface-container-low transition-colors">
        <span class="material-symbols-outlined text-lg">refresh</span>Refresh
      </button>`
    )}
    <div id="dash-body">${loadingHtml('Memuat dashboard...')}</div>
  </div>`;

  $('btn-dash-refresh').onclick = loadDashboard;
  await loadDashboard();
}

async function loadDashboard() {
  const backend = activeBackend();
  const body = $('dash-body');
  const btn = $('btn-dash-refresh');
  if (btn) { btn.disabled = true; btn.querySelector('.material-symbols-outlined').classList.add('animate-spin'); }

  // Each source fails independently so one unreachable endpoint doesn't blank the page.
  const [health, threads, skills] = await Promise.allSettled([
    backend.health(), backend.listThreads(), backend.listSkills(),
  ]);

  if (body) body.innerHTML = `
    <div class="grid grid-cols-4 gap-6 mb-6">
      ${statBackend(backend, health)}
      ${statModel(health)}
      ${statCount('THREADS', threads, backend.capabilities.serverThreads ? 'tersimpan di server' : 'tersimpan di browser ini')}
      ${statCount('SKILLS', skills, 'terpasang')}
    </div>
    <div class="grid grid-cols-2 gap-6">
      ${recentThreadsHtml(threads)}
      ${unavailableHtml()}
    </div>`;
  document.querySelectorAll('[data-goto]').forEach(el => {
    el.onclick = () => { location.hash = el.dataset.goto; };
  });
  if (btn) { btn.disabled = false; btn.querySelector('.material-symbols-outlined').classList.remove('animate-spin'); }
}

function statBackend(backend, health) {
  const ok = health.status === 'fulfilled' && health.value.ok;
  const [dot, text] = health.status === 'rejected'
    ? ['bg-red-500', 'tidak terjangkau']
    : ok ? ['bg-green-500', 'terhubung'] : ['bg-amber-500', 'status tidak OK'];
  const title = health.status === 'rejected' ? health.reason.message : '';
  return statCard('BACKEND', `
    <p class="text-title-sm font-title-sm text-primary">${esc(backend.label)}</p>
    <p class="text-[11px] mt-1 flex items-center gap-1.5" title="${esc(title)}"><span class="w-2 h-2 rounded-full ${dot}"></span>${text}</p>`);
}

function statModel(health) {
  const h = health.status === 'fulfilled' ? health.value : null;
  return statCard('MODEL', `
    <p class="text-title-sm font-title-sm text-primary truncate" title="${esc(h?.model || '')}">${esc(h?.model || '—')}</p>
    <p class="text-[11px] text-on-surface-variant mt-1 truncate" title="${esc(h?.detail || '')}">${esc(h?.detail || '')}</p>`);
}

function statCount(label, result, caption) {
  if (result.status === 'rejected') {
    return statCard(label, `<p class="text-display-lg font-display-lg text-outline">—</p>
      <p class="text-[11px] text-red-700 mt-1 truncate" title="${esc(result.reason.message)}">gagal dimuat</p>`);
  }
  return statCard(label, `<p class="text-display-lg font-display-lg text-primary">${result.value.length}</p>
    <p class="text-[11px] text-on-surface-variant mt-1">${caption}</p>`);
}

function recentThreadsHtml(threads) {
  if (threads.status === 'rejected') {
    return cardHtml('Thread Terakhir', emptyBody('Gagal memuat thread: ' + esc(threads.reason.message)));
  }
  const list = threads.value.slice(0, 8);
  if (!list.length) return cardHtml('Thread Terakhir', emptyBody('Belum ada percakapan.'));
  const rows = list.map(t => `
    <div data-goto="chat/${esc(t.id)}" class="px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <div class="flex justify-between items-baseline gap-2">
        <span class="text-body-sm font-medium text-primary truncate">${esc(t.title)}</span>
        <span class="text-[10px] text-outline tabular-nums shrink-0">${esc(fmtFullDateTime(t.updatedAt))}</span>
      </div>
      <p class="text-[11px] text-on-surface-variant truncate mt-0.5">${esc(t.lastMessage || '—')}</p>
    </div>`).join('');
  return cardHtml('Thread Terakhir', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function unavailableHtml() {
  const rows = NAV_ITEMS.filter(n => n.unavailable).map(n => `
    <div data-goto="${esc(n.id)}" class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <span class="material-symbols-outlined text-[18px] text-outline">${n.icon}</span>
      <span class="text-body-sm text-on-surface flex-1">${esc(n.label)}</span>
      <span class="text-[10px] font-bold uppercase tracking-wider text-outline">belum tersedia</span>
    </div>`).join('');
  return cardHtml('Fitur Menunggu API Backend', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}
