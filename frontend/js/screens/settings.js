import { $, esc, badge, pageHeader, confirmDialog } from '../utils.js';
import { BACKENDS, activeBackend, setActiveBackend } from '../backends/index.js';
import { mgr } from '../manager.js';
import { S } from '../state.js';
import { renderLlm } from './settings-llm.js';

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
      ${tab('backend', 'Backend', true)}${tab('llm', 'LLM Provider', false)}${tab('files', 'File Konfigurasi', false)}${tab('account', 'Akun', false)}
    </div>
    <div id="pane-backend">
      <div id="backend-cards" class="grid grid-cols-1 md:grid-cols-2 gap-6"></div>
    </div>
    <div id="pane-llm" class="hidden"></div>
    <div id="pane-files" class="hidden"></div>
    <div id="pane-account" class="hidden"></div>
  </div>`;

  $('settings-tabs').onclick = e => {
    const b = e.target.closest('[data-tab]');
    if (!b) return;
    document.querySelectorAll('#settings-tabs [data-tab]').forEach(x => {
      const on = x === b;
      x.className = `pb-3 px-1 text-body-md ${on ? 'border-b-2 border-primary text-primary font-semibold' : 'text-on-surface-variant hover:text-primary'}`;
    });
    $('pane-backend').classList.toggle('hidden', b.dataset.tab !== 'backend');
    $('pane-llm').classList.toggle('hidden', b.dataset.tab !== 'llm');
    $('pane-files').classList.toggle('hidden', b.dataset.tab !== 'files');
    $('pane-account').classList.toggle('hidden', b.dataset.tab !== 'account');
    if (b.dataset.tab === 'account') renderAccount($('pane-account'));
    if (b.dataset.tab === 'llm') renderLlm($('pane-llm'));
    if (b.dataset.tab === 'files') renderFiles();
  };

  renderCards();
  Object.keys(BACKENDS).forEach(probe);
}

// Password change for the logged-in operator. Other sessions of the same user end.
function renderAccount(el) {
  const field = (id, label, auto) => `<label class="block text-label-caps font-label-caps text-on-surface-variant mb-1" for="${id}">${label}</label>
    <input id="${id}" type="password" autocomplete="${auto}" required maxlength="256" class="w-full mb-4 px-3 py-2 border border-outline-variant rounded-lg text-body-md">`;
  el.innerHTML = `<form id="pw-form" class="max-w-[420px] bg-surface-container-lowest border border-outline-variant rounded-lg p-6">
    <p class="text-body-sm text-on-surface-variant mb-4">Masuk sebagai <b>${esc(S.user)}</b>. Mengganti password mengeluarkan perangkat lain.</p>
    ${field('pw-current', 'PASSWORD SAAT INI', 'current-password')}${field('pw-new', 'PASSWORD BARU (MIN. 10 KARAKTER)', 'new-password')}${field('pw-confirm', 'ULANGI PASSWORD BARU', 'new-password')}
    <p id="pw-msg" class="text-body-sm mb-4 hidden"></p>
    <button class="px-4 py-2 bg-primary text-on-primary rounded-lg text-body-sm font-medium hover:bg-primary-container transition-colors">Ganti password</button>
  </form>`;
  $('pw-form').onsubmit = async e => {
    e.preventDefault();
    const msg = $('pw-msg');
    const show = (t, ok) => { msg.textContent = t; msg.className = `text-body-sm mb-4 ${ok ? 'text-green-700' : 'text-error'}`; };
    if ($('pw-new').value !== $('pw-confirm').value) return show('Password baru tidak sama.', false);
    try {
      await mgr('/auth/password', { method: 'POST', body: { current: $('pw-current').value, new: $('pw-new').value } });
      e.target.reset();
      show('Password diganti.', true);
    } catch (ex) { show(ex.message, false); }
  };
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
        ${b.capabilities.credential ? `<div id="cred-${b.id}" class="border-t border-outline-variant pt-4"></div>` : ''}
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

  Object.values(BACKENDS).filter(b => b.capabilities.credential).forEach(b => renderCredential(b));

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

// API key of a backend, kept in the manager's database (never in an env var).
// Write-only: the manager only says whether a key is set. It is tested
// server-side, and nginx injects it into proxied requests.
async function renderCredential(b) {
  const el = $(`cred-${b.id}`);
  if (!el) return;
  let st;
  try { st = await mgr(`/backends/${b.id}/credential`); }
  catch (e) { el.innerHTML = `<p class="text-body-sm text-red-600">Gagal memuat status API key: ${esc(e.message)}</p>`; return; }
  el.innerHTML = `
    <div class="flex justify-between items-center mb-2">
      <p class="text-label-caps font-label-caps text-on-surface-variant">API Key</p>
      ${st.has_key ? badge('tersimpan', 'green') : badge('belum diatur', 'amber')}
    </div>
    <input id="cred-key-${b.id}" type="password" autocomplete="new-password" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono"
      placeholder="${st.has_key ? '•••••••• tersimpan — isi untuk mengganti' : 'Tempel API key (API_SERVER_KEY Hermes)'}"/>
    <div class="flex flex-wrap items-center gap-2 mt-2">
      <button id="cred-test-${b.id}" class="px-3 py-1.5 border border-outline-variant text-primary text-body-sm rounded-md hover:bg-surface-container">Cek</button>
      <button id="cred-save-${b.id}" class="px-3 py-1.5 bg-secondary text-white text-body-sm font-medium rounded-md hover:opacity-90">Simpan</button>
      ${st.has_key ? `<button id="cred-del-${b.id}" class="px-3 py-1.5 border border-red-300 text-red-700 text-body-sm rounded-md hover:bg-red-50">Hapus</button>` : ''}
      <span id="cred-out-${b.id}" class="text-body-sm text-on-surface-variant"></span>
    </div>
    <p class="text-[11px] text-on-surface-variant mt-2">Disimpan di database NetOpsUI (bukan di environment) dan tidak pernah dikirim balik ke browser. Berlaku langsung tanpa restart.${st.updated_at ? ' Terakhir diubah ' + esc(st.updated_at) + ' UTC.' : ''}</p>`;
  const out = $(`cred-out-${b.id}`), input = $(`cred-key-${b.id}`);
  const say = (msg, cls) => { out.className = `text-body-sm ${cls}`; out.textContent = msg; };

  $(`cred-test-${b.id}`).onclick = async () => {
    say('Memeriksa...', 'text-on-surface-variant');
    try {
      const r = await mgr(`/backends/${b.id}/credential/test`, { method: 'POST', body: { api_key: input.value || null } });
      r.ok ? say(`Key diterima${r.models?.length ? ' · model: ' + r.models[0] : ''}`, 'text-green-700') : say(r.error, 'text-red-600');
    } catch (e) { say(e.message, 'text-red-600'); }
  };
  $(`cred-save-${b.id}`).onclick = async () => {
    if (!input.value.trim()) { say('Isi API key terlebih dulu.', 'text-red-600'); return; }
    try { await mgr(`/backends/${b.id}/credential`, { method: 'PUT', body: { api_key: input.value } }); }
    catch (e) { say(e.message, 'text-red-600'); return; }
    await renderCredential(b);
    probe(b.id);
    window.dispatchEvent(new CustomEvent('backend-changed', { detail: { id: activeBackend().id } })); // refresh header indicator
  };
  const del = $(`cred-del-${b.id}`);
  if (del) del.onclick = async () => {
    const ok = await confirmDialog({ title: 'Hapus API key?', message: `API key ${b.label} dihapus dari database. Chat ke backend ini akan ditolak (401) sampai key diisi lagi.`, confirmLabel: 'Hapus', danger: true });
    if (!ok) return;
    try { await mgr(`/backends/${b.id}/credential`, { method: 'DELETE' }); } catch (e) { say(e.message, 'text-red-600'); return; }
    await renderCredential(b);
    window.dispatchEvent(new CustomEvent('backend-changed', { detail: { id: activeBackend().id } }));
  };
}
