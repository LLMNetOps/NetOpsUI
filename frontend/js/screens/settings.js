import { $, esc, badge, pageHeader } from '../utils.js';
import { BACKENDS, activeBackend, setActiveBackend } from '../backends/index.js';
import { mgr } from '../manager.js';

const CAPABILITY_LABELS = [
  ['serverThreads', 'Riwayat chat tersimpan di server', 'Riwayat chat tersimpan di browser ini'],
  ['approval', 'Approval untuk command berisiko', 'Tanpa approval (tool read-only)'],
];

// One backend is active for the whole UI at a time. Switching it resets the
// chat thread list (threads belong to a single backend).
export async function screenSettings(c) {
  const tab = (id, label, on) => `<button data-tab="${id}" class="pb-3 px-1 text-body-md ${on ? 'border-b-2 border-primary text-primary font-semibold' : 'text-on-surface-variant hover:text-primary'}">${label}</button>`;
  c.innerHTML = `<div class="p-container_gutter max-w-[1100px] mx-auto">
    ${pageHeader('Settings', 'Pilih backend agent yang dipakai UI dan lihat konfigurasinya.')}
    <div id="settings-tabs" class="border-b border-outline-variant mb-6 flex gap-8">
      ${tab('backend', 'Backend', true)}${tab('files', 'File Konfigurasi', false)}
    </div>
    <div id="pane-backend">
      <div id="backend-cards" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
      <p class="text-[11px] text-on-surface-variant mt-6">
        UI memanggil backend lewat proxy <span class="font-data-mono-sm">/backend/&lt;id&gt;/</span> (nginx).
        Alamat backend dan API key Hermes diatur di environment container frontend, bukan di browser — lihat README.
      </p>
    </div>
    <div id="pane-files" class="hidden"></div>
  </div>`;

  $('settings-tabs').onclick = e => {
    const b = e.target.closest('[data-tab]');
    if (!b) return;
    document.querySelectorAll('#settings-tabs [data-tab]').forEach(x => {
      const on = x === b;
      x.className = `pb-3 px-1 text-body-md ${on ? 'border-b-2 border-primary text-primary font-semibold' : 'text-on-surface-variant hover:text-primary'}`;
    });
    $('pane-backend').classList.toggle('hidden', b.dataset.tab !== 'backend');
    $('pane-files').classList.toggle('hidden', b.dataset.tab !== 'files');
    if (b.dataset.tab === 'files') renderFiles();
  };

  renderCards();
  Object.keys(BACKENDS).forEach(probe);
}

// Read-only view of the active backend's config files, served by the NetOpsUI
// manager. Secrets never reach the browser: config.yaml comes back masked and
// .env comes back as variable names only.
async function renderFiles() {
  const el = $('pane-files');
  const b = activeBackend();
  el.innerHTML = `<p class="text-body-sm text-on-surface-variant mb-4">Backend aktif: <b>${esc(b.label)}</b>. Nilai rahasia disamarkan di server; <span class="font-data-mono-sm">.env</span> hanya menampilkan nama variabel.</p>
    <div class="space-y-6">${['config', 'env', 'soul'].map(k => `<div id="file-${k}" class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden"></div>`).join('')}</div>`;
  const panel = (k, title, body) => { $('file-' + k).innerHTML = `<div class="px-5 py-3 border-b border-outline-variant font-data-mono-sm text-data-mono-sm text-primary">${title}</div>${body}`; };
  const missing = '<p class="p-5 text-body-sm text-on-surface-variant">File tidak ditemukan.</p>';
  const run = async (k, title, fn) => {
    panel(k, title, '<p class="p-5 text-body-sm text-on-surface-variant">Memuat...</p>');
    try { panel(k, title, fn(await mgr(`/backends/${b.id}/${k}`))); }
    catch (e) { panel(k, title, `<div class="p-5">${esc(e.message)}</div>`); }
  };
  const pre = t => `<pre class="p-5 font-data-mono text-data-mono whitespace-pre-wrap break-words max-h-[420px] overflow-auto">${esc(t)}</pre>`;
  await Promise.all([
    run('config', 'config.yaml', d => d.exists ? pre(d.yaml) : missing),
    run('env', '.env (nama variabel)', d => !d.exists ? missing : d.vars.length
      ? `<table class="w-full text-body-sm"><tbody>${d.vars.map(v => `<tr class="border-b border-outline-variant"><td class="px-5 py-2 font-data-mono-sm text-data-mono-sm">${esc(v.name)}</td><td class="px-5 py-2 text-right">${v.set ? badge('terisi', 'green') : badge('kosong', 'amber')}</td></tr>`).join('')}</tbody></table>`
      : '<p class="p-5 text-body-sm text-on-surface-variant">Tidak ada variabel.</p>'),
    run('soul', 'SOUL.md', d => d.exists ? pre(d.content) : missing),
  ]);
}

function renderCards() {
  const el = $('backend-cards');
  if (!el) return;
  const active = activeBackend().id;
  el.innerHTML = Object.values(BACKENDS).map(b => {
    const isActive = b.id === active;
    const caps = CAPABILITY_LABELS.map(([k, yes, no]) => {
      const on = !!b.capabilities[k];
      return `<li class="flex items-center gap-2"><span class="material-symbols-outlined text-[16px] ${on ? 'text-green-700' : 'text-outline'}">${on ? 'check_circle' : 'remove_circle_outline'}</span>${on ? yes : no}</li>`;
    }).join('');
    const stop = b.capabilities.stop === 'interrupt'
      ? 'Stop menghentikan run di server'
      : 'Stop hanya memutus stream (run di server tetap selesai)';
    return `<div class="bg-surface-container-lowest border ${isActive ? 'border-primary ring-1 ring-primary' : 'border-outline-variant'} rounded-lg shadow-sm flex flex-col">
      <div class="p-5 border-b border-outline-variant flex justify-between items-start gap-3">
        <div>
          <h3 class="font-title-sm text-title-sm text-primary">${esc(b.label)}</h3>
          <p class="text-body-sm text-on-surface-variant mt-1">${esc(b.description)}</p>
        </div>
        ${isActive ? badge('AKTIF', 'green') : ''}
      </div>
      <div class="p-5 flex-1 space-y-4 text-body-sm">
        <div id="health-${b.id}" class="text-on-surface-variant">Memeriksa koneksi...</div>
        <ul class="space-y-1.5 text-on-surface-variant">${caps}
          <li class="flex items-center gap-2"><span class="material-symbols-outlined text-[16px] text-outline">stop_circle</span>${stop}</li>
        </ul>
      </div>
      <div class="p-5 pt-0 flex gap-2">
        <button data-activate="${b.id}" ${isActive ? 'disabled' : ''} class="px-4 py-2 rounded-lg text-body-sm font-medium transition-colors ${isActive ? 'bg-surface-container text-on-surface-variant cursor-default' : 'bg-secondary text-white hover:opacity-90'}">${isActive ? 'Sedang dipakai' : 'Gunakan backend ini'}</button>
        <button data-probe="${b.id}" class="px-4 py-2 border border-outline-variant rounded-lg text-body-sm text-primary hover:bg-surface-container transition-colors">Cek koneksi</button>
      </div>
    </div>`;
  }).join('');

  el.onclick = e => {
    const act = e.target.closest('[data-activate]');
    if (act && !act.disabled) {
      setActiveBackend(act.dataset.activate);
      renderCards();
      Object.keys(BACKENDS).forEach(probe);
      return;
    }
    const pr = e.target.closest('[data-probe]');
    if (pr) probe(pr.dataset.probe);
  };
}

async function probe(id) {
  const el = () => $(`health-${id}`);
  if (el()) el().innerHTML = '<span class="text-on-surface-variant">Memeriksa koneksi...</span>';
  try {
    const h = await BACKENDS[id].health();
    if (!el()) return;
    el().innerHTML = `<div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full ${h.ok ? 'bg-green-500' : 'bg-amber-500'}"></span>
        <span class="font-medium ${h.ok ? 'text-green-700' : 'text-amber-700'}">${h.ok ? 'Terhubung' : 'Merespons, status tidak OK'}</span></div>
      <p class="text-[11px] text-on-surface-variant mt-1 font-data-mono-sm">model: ${esc(h.model)}${h.detail ? ' &middot; ' + esc(h.detail) : ''}</p>`;
  } catch (e) {
    if (!el()) return;
    el().innerHTML = `<div class="flex items-center gap-2"><span class="w-2 h-2 rounded-full bg-red-500"></span><span class="font-medium text-red-700">Tidak terjangkau</span></div>
      <p class="text-[11px] text-on-surface-variant mt-1 break-all">${esc(e.message)}</p>`;
  }
}
