import { $, esc, badge, loadingHtml, errorHtml, confirmDialog, alertDialog } from '../utils.js';
import { BACKENDS, activeBackend } from '../backends/index.js';
import { mgr } from '../manager.js';

// LLM provider profiles live in NetOpsUI (API key write-only: the manager never
// returns it). "Terapkan" writes a provider into a backend's config.yaml
// `model:` block; the backend must be restarted afterwards to pick it up.

const slugify = s => s.toLowerCase().normalize('NFKD').replace(/[^a-z0-9]+/g, '-').replace(/^-+|-+$/g, '').slice(0, 64);
const KEY_SRC = {
  env:     ['key di env backend', 'blue'],
  literal: ['tertulis di config', 'amber'],
  none:    ['tanpa key', 'gray'],
};

export async function renderLlm(el) {
  let providers = [], editing = null, applying = null;
  const modelCache = {}; // slug or '_form' → model ids from the last connection test

  el.innerHTML = `
    <div class="space-y-6">
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-5 py-3 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
          <div><h3 class="font-title-sm text-title-sm text-primary">LLM yang sedang dipakai backend</h3>
            <p class="text-[11px] text-on-surface-variant">Dibaca dari config.yaml masing-masing backend.</p></div>
          <button id="llm-refresh" class="text-body-sm text-primary hover:underline flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">refresh</span>Muat ulang</button>
        </div>
        <div id="llm-current">${loadingHtml('Memuat...')}</div>
      </div>
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-5 py-3 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
          <div><h3 class="font-title-sm text-title-sm text-primary">Provider Tersimpan</h3>
            <p class="text-[11px] text-on-surface-variant">Endpoint OpenAI-compatible (Ollama, vLLM, LM Studio, OpenAI, dll.). API key disimpan di server NetOpsUI dan tidak pernah dikirim balik ke browser.</p></div>
          <button id="llm-add" class="text-secondary font-medium text-body-sm flex items-center gap-1"><span class="material-symbols-outlined text-[18px]">add</span>Tambah Provider</button>
        </div>
        <div id="llm-form" class="hidden"></div>
        <div id="llm-list">${loadingHtml('Memuat...')}</div>
      </div>
    </div>`;

  // ── current per-backend LLM ────────────────────────────────────────────────
  async function loadCurrent() {
    const box = $('llm-current');
    box.innerHTML = loadingHtml('Memuat...');
    const rows = await Promise.all(Object.values(BACKENDS).map(async b => {
      try { return [b, await mgr(`/backends/${b.id}/llm`), null]; }
      catch (e) { return [b, null, e.message]; }
    }));
    box.innerHTML = `<div class="divide-y divide-outline-variant">${rows.map(([b, d, err]) => {
      if (err) return `<div class="px-5 py-3 text-body-sm"><b>${esc(b.label)}</b> ${errorHtml(err)}</div>`;
      if (!d.exists) return `<div class="px-5 py-3 text-body-sm"><b>${esc(b.label)}</b> <span class="text-on-surface-variant">config.yaml tidak ditemukan</span></div>`;
      const [ks, kv] = KEY_SRC[d.key_source];
      const deleg = (d.delegation || []).length
        ? `<p class="text-[11px] text-on-surface-variant mt-1">Agent delegasi: ${d.delegation.map(x => `${esc(x.agent)} → <span class="font-data-mono-sm">${esc(x.model || '—')}</span>`).join(', ')}</p>` : '';
      return `<div class="px-5 py-3">
        <div class="flex justify-between items-center gap-3"><p class="font-medium text-primary">${esc(b.label)}</p>
          <span class="flex items-center gap-2">${d.key_ref ? `<span class="text-[10px] font-data-mono-sm text-on-surface-variant">${esc(d.key_ref)}</span>` : ''}${badge(ks, kv)}</span></div>
        <p class="text-body-sm mt-1"><span class="font-data-mono text-data-mono">${esc(d.model || '—')}</span>
          <span class="text-on-surface-variant"> · ${esc(d.base_url || '—')}${d.provider ? ' · provider: ' + esc(d.provider) : ''}</span></p>${deleg}</div>`;
    }).join('')}</div>`;
  }

  // ── provider list ──────────────────────────────────────────────────────────
  function renderList() {
    const box = $('llm-list');
    if (!providers.length) {
      box.innerHTML = `<p class="p-5 text-body-sm text-on-surface-variant">Belum ada provider. Klik <b>Tambah Provider</b>.</p>`;
      return;
    }
    box.innerHTML = `<div class="divide-y divide-outline-variant">${providers.map(p => `
      <div>
        <div class="px-5 py-3 flex items-center gap-3">
          <div class="min-w-0 flex-1">
            <p class="font-medium text-primary truncate">${esc(p.name)} ${p.has_key ? badge('key tersimpan', 'green') : badge('tanpa key', 'gray')}</p>
            <p class="text-[11px] text-on-surface-variant truncate"><span class="font-data-mono-sm">${esc(p.model || '(model belum dipilih)')}</span> · ${esc(p.base_url)}</p>
          </div>
          <button data-apply="${esc(p.slug)}" class="px-3 py-1.5 bg-secondary text-white rounded-md text-body-sm font-medium hover:opacity-90">Terapkan…</button>
          <button data-edit="${esc(p.slug)}" title="Ubah" class="material-symbols-outlined text-[18px] text-on-surface-variant hover:text-primary">edit</button>
          <button data-del="${esc(p.slug)}" title="Hapus" class="material-symbols-outlined text-[18px] text-on-surface-variant hover:text-red-600">delete</button>
        </div>
        ${applying === p.slug ? applyPanel(p) : ''}
      </div>`).join('')}</div>`;
    box.querySelectorAll('[data-edit]').forEach(b => { b.onclick = () => openForm(providers.find(p => p.slug === b.dataset.edit)); });
    box.querySelectorAll('[data-del]').forEach(b => { b.onclick = () => del(b.dataset.del); });
    box.querySelectorAll('[data-apply]').forEach(b => { b.onclick = () => { applying = applying === b.dataset.apply ? null : b.dataset.apply; renderList(); }; });
    if (applying) bindApply(providers.find(p => p.slug === applying));
  }

  // ── add / edit form ────────────────────────────────────────────────────────
  function openForm(p) {
    editing = p || null;
    const f = $('llm-form');
    f.classList.remove('hidden');
    f.innerHTML = `<div class="border-b border-outline-variant p-5 bg-surface-container-low">
      <p class="font-medium text-primary text-body-md mb-3">${p ? 'Ubah provider' : 'Tambah provider'}</p>
      <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
        <label class="block"><span class="text-[11px] text-on-surface-variant">Nama</span>
          <input id="lp-name" value="${esc(p?.name || '')}" placeholder="Ollama Kampus" class="mt-1 w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2"/></label>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Base URL (biasanya berakhiran /v1)</span>
          <input id="lp-url" value="${esc(p?.base_url || '')}" placeholder="https://ollama.example.com/v1" class="mt-1 w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono"/></label>
        <label class="block"><span class="text-[11px] text-on-surface-variant">API key <span class="font-normal">(opsional)</span></span>
          <input id="lp-key" type="password" autocomplete="new-password" placeholder="${p?.has_key ? '•••••••• tersimpan — kosongkan agar tidak berubah' : 'Kosongkan jika tanpa key'}" class="mt-1 w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono"/></label>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Model</span>
          <input id="lp-model" list="lp-models" value="${esc(p?.model || '')}" placeholder="Klik Cek Koneksi untuk melihat daftar" class="mt-1 w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono"/>
          <datalist id="lp-models">${(modelCache[p?.slug || '_form'] || []).map(m => `<option value="${esc(m)}">`).join('')}</datalist></label>
      </div>
      ${p?.has_key ? `<label class="flex items-center gap-2 text-body-sm text-on-surface-variant mb-3"><input id="lp-clear" type="checkbox"/> Hapus API key yang tersimpan</label>` : ''}
      <div class="flex items-center gap-3 mb-3">
        <button id="lp-test" type="button" class="px-3 py-1.5 border border-outline-variant text-primary font-medium text-body-sm rounded-md hover:bg-surface-container flex items-center gap-1"><span class="material-symbols-outlined text-[16px]">wifi_tethering</span>Cek Koneksi</button>
        <span id="lp-test-out" class="text-body-sm text-on-surface-variant"></span>
      </div>
      <div class="flex items-center gap-2">
        <button id="lp-save" class="px-4 py-2 bg-secondary text-white font-medium text-body-sm rounded-md hover:opacity-90">Simpan</button>
        <button id="lp-cancel" class="px-4 py-2 border border-outline-variant text-on-surface-variant font-medium text-body-sm rounded-md hover:bg-surface-container">Batal</button>
        <span id="lp-err" class="text-red-600 text-body-sm"></span>
      </div></div>`;
    $('lp-cancel').onclick = closeForm;
    $('lp-test').onclick = testConn;
    $('lp-save').onclick = save;
  }

  function closeForm() { editing = null; $('llm-form').classList.add('hidden'); $('llm-form').innerHTML = ''; }

  async function testConn() {
    const out = $('lp-test-out');
    out.className = 'text-body-sm text-on-surface-variant';
    out.textContent = 'Memeriksa...';
    try {
      const r = await mgr('/llm/test', { method: 'POST', body: {
        base_url: $('lp-url').value.trim(), api_key: $('lp-key').value || undefined, provider: editing?.slug } });
      if (r.ok) {
        modelCache[editing?.slug || '_form'] = r.models;
        $('lp-models').innerHTML = r.models.map(m => `<option value="${esc(m)}">`).join('');
        out.className = 'text-body-sm text-green-700';
        out.textContent = `Terhubung · ${r.models.length} model · ${r.latency_ms} ms`;
      } else { out.className = 'text-body-sm text-red-600'; out.textContent = r.error; }
    } catch (e) { out.className = 'text-body-sm text-red-600'; out.textContent = e.message; }
  }

  async function save() {
    const name = $('lp-name').value.trim(), url = $('lp-url').value.trim(), err = $('lp-err');
    if (!name) { err.textContent = 'Nama wajib diisi.'; return; }
    if (!/^https?:\/\//.test(url)) { err.textContent = 'Base URL harus diawali http:// atau https://'; return; }
    const body = { slug: editing?.slug || slugify(name), name, base_url: url, model: $('lp-model').value.trim() };
    if (!body.slug) { err.textContent = 'Nama tidak bisa dijadikan slug.'; return; }
    const key = $('lp-key').value;
    if (key) body.api_key = key;                       // new key
    else if ($('lp-clear')?.checked) body.api_key = ''; // explicit clear
    try {
      if (editing) await mgr('/llm/providers/' + editing.slug, { method: 'PUT', body });
      else await mgr('/llm/providers', { method: 'POST', body });
      closeForm(); await loadProviders();
    } catch (e) { err.textContent = e.message; }
  }

  async function del(slug) {
    const ok = await confirmDialog({ title: 'Hapus provider?', message: `"${slug}" dihapus dari NetOpsUI, termasuk API key yang tersimpan. Config backend yang sudah memakainya tidak berubah.`, confirmLabel: 'Hapus', danger: true });
    if (!ok) return;
    try { await mgr('/llm/providers/' + slug, { method: 'DELETE' }); if (applying === slug) applying = null; await loadProviders(); }
    catch (e) { await alertDialog(e.message, 'Gagal menghapus'); }
  }

  // ── apply to backend(s) ────────────────────────────────────────────────────
  function applyPanel(p) {
    const active = activeBackend().id;
    return `<div class="px-5 pb-4 pt-1 bg-surface-container-low border-t border-outline-variant">
      <p class="text-body-sm font-medium text-primary mt-3 mb-2">Terapkan “${esc(p.name)}” ke:</p>
      <div class="flex flex-wrap gap-5 mb-3">${Object.values(BACKENDS).map(b => `
        <label class="flex items-center gap-2 text-body-sm"><input type="checkbox" data-target="${b.id}" ${b.id === active ? 'checked' : ''}/> ${esc(b.label)}</label>`).join('')}</div>
      <label class="block max-w-md mb-3"><span class="text-[11px] text-on-surface-variant">Model</span>
        <input id="ap-model" list="ap-models" value="${esc(p.model || '')}" class="mt-1 w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono"/>
        <datalist id="ap-models">${(modelCache[p.slug] || []).map(m => `<option value="${esc(m)}">`).join('')}</datalist></label>
      <label id="ap-deleg-row" class="flex items-center gap-2 text-body-sm mb-3"><input id="ap-deleg" type="checkbox" checked/> NetOps Agent: ikut ubah model agent delegasi (network-specialist, dst.)</label>
      <p class="text-[11px] text-on-surface-variant mb-3">${p.has_key
        ? '<b>API key akan ditulis sebagai teks di config.yaml</b> (menggantikan referensi <span class="font-data-mono-sm">${…}</span> bila ada).'
        : 'Provider ini tanpa key: <span class="font-data-mono-sm">api_key</span> lama di config akan <b>dihapus</b> agar key provider sebelumnya tidak terkirim ke endpoint ini.'}
        Backup config dibuat otomatis. Backend <b>tidak</b> di-restart oleh NetOpsUI.</p>
      <div class="flex items-center gap-2">
        <button id="ap-go" class="px-4 py-2 bg-secondary text-white font-medium text-body-sm rounded-md hover:opacity-90">Terapkan</button>
        <button id="ap-cancel" class="px-4 py-2 border border-outline-variant text-on-surface-variant font-medium text-body-sm rounded-md hover:bg-surface-container">Batal</button>
        <button id="ap-fetch" class="ml-2 text-body-sm text-primary hover:underline">Ambil daftar model</button>
        <span id="ap-err" class="text-red-600 text-body-sm"></span>
      </div></div>`;
  }

  function bindApply(p) {
    const targets = () => [...document.querySelectorAll('[data-target]:checked')].map(x => x.dataset.target);
    const syncDeleg = () => $('ap-deleg-row').classList.toggle('hidden', !targets().includes('netops'));
    document.querySelectorAll('[data-target]').forEach(x => { x.onchange = syncDeleg; });
    syncDeleg();
    $('ap-cancel').onclick = () => { applying = null; renderList(); };
    $('ap-fetch').onclick = async () => {
      try {
        const r = await mgr('/llm/test', { method: 'POST', body: { base_url: p.base_url, provider: p.slug } });
        if (!r.ok) { $('ap-err').textContent = r.error; return; }
        modelCache[p.slug] = r.models; $('ap-models').innerHTML = r.models.map(m => `<option value="${esc(m)}">`).join(''); $('ap-err').textContent = '';
      } catch (e) { $('ap-err').textContent = e.message; }
    };
    $('ap-go').onclick = async () => {
      const t = targets(), model = $('ap-model').value.trim(), err = $('ap-err');
      if (!t.length) { err.textContent = 'Pilih minimal satu backend.'; return; }
      if (!model) { err.textContent = 'Model wajib diisi.'; return; }
      const names = t.map(id => BACKENDS[id].label).join(' dan ');
      const ok = await confirmDialog({
        title: 'Tulis ke config backend?',
        message: `config.yaml ${names} akan diubah ke ${p.name} / ${model}. Backup dibuat otomatis. Backend harus di-restart agar perubahan berlaku.`,
        confirmLabel: 'Terapkan', danger: true });
      if (!ok) return;
      const done = [], failed = [];
      for (const id of t) {
        try {
          const r = await mgr(`/backends/${id}/llm/apply`, { method: 'POST', body: { provider: p.slug, model, include_delegation: $('ap-deleg').checked } });
          done.push(`${BACKENDS[id].label} (backup: ${r.backup})`);
        } catch (e) { failed.push(`${BACKENDS[id].label}: ${e.message}`); }
      }
      applying = null; renderList(); loadCurrent();
      await alertDialog(
        (done.length ? `Berhasil ditulis:\n• ${done.join('\n• ')}\n\nRestart backend tersebut agar LLM baru dipakai.` : '') +
        (failed.length ? `${done.length ? '\n\n' : ''}Gagal:\n• ${failed.join('\n• ')}` : ''),
        failed.length ? 'Sebagian gagal' : 'Berhasil');
    };
  }

  async function loadProviders() {
    try { providers = (await mgr('/llm/providers')).providers; renderList(); }
    catch (e) { $('llm-list').innerHTML = `<div class="p-5">${errorHtml('Gagal memuat provider: ' + e.message)}</div>`; }
  }

  $('llm-add').onclick = () => openForm(null);
  $('llm-refresh').onclick = loadCurrent;
  await Promise.all([loadCurrent(), loadProviders()]);
}
