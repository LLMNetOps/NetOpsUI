import { $, esc, badge, pageHeader, loadingHtml, errorHtml, confirmDialog, alertDialog } from '../utils.js';
import { mgr, getActiveProfile, setActiveProfile } from '../manager.js';

const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;

// Agent profiles = named system prompts kept in NetOpsUI's DB.
//  - Hermes: the active profile is sent with every chat run as `instructions`.
//  - NetOps Agent: has no per-request prompt; a profile can be applied to its
//    SOUL.md (persona file), which replaces the file (old one is backed up).
export async function screenAgents(c) {
  let profiles = [], selected = null, isNew = false;

  c.innerHTML = `<div class="p-container_gutter max-w-[1700px] mx-auto">
    ${pageHeader('Agents', 'Profil agent (prompt) yang dikelola di NetOpsUI. Dipakai per-chat di Hermes, atau diterapkan ke SOUL.md NetOps Agent.', `
      <button id="ag-new" class="px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 flex items-center gap-1"><span class="material-symbols-outlined text-[18px]">add</span>Profil Baru</button>`)}
    <div class="grid grid-cols-12 gap-6">
      <div class="col-span-12 xl:col-span-4">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div id="ag-list">${loadingHtml('Memuat...')}</div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-8"><div id="ag-editor"></div></div>
    </div>
  </div>`;

  function renderList() {
    const active = getActiveProfile();
    $('ag-list').innerHTML = profiles.length ? profiles.map(p => `
      <button data-slug="${esc(p.slug)}" class="w-full text-left px-5 py-3 border-b border-outline-variant hover:bg-surface-container-low transition-colors ${selected === p.slug ? 'bg-surface-container-low' : ''}">
        <div class="flex justify-between items-center gap-2"><p class="font-medium text-primary truncate">${esc(p.name)}</p>${active === p.slug ? badge('Chat Hermes', 'blue') : ''}</div>
        <p class="text-[11px] text-on-surface-variant truncate">${esc(p.description || p.slug)}</p>
      </button>`).join('') : `<p class="p-5 text-body-sm text-on-surface-variant">Belum ada profil.</p>`;
    $('ag-list').querySelectorAll('[data-slug]').forEach(b => { b.onclick = () => select(b.dataset.slug); });
  }

  function renderEditor() {
    const el = $('ag-editor');
    if (!isNew && !selected) {
      el.innerHTML = `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center text-body-sm text-on-surface-variant">Pilih profil di kiri, atau buat profil baru.</div>`;
      return;
    }
    const p = isNew ? { slug: '', name: '', description: '', prompt: '' } : profiles.find(x => x.slug === selected);
    if (!p) { el.innerHTML = ''; return; }
    const isActive = getActiveProfile() === p.slug;
    el.innerHTML = `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg">
      <div class="px-6 py-4 border-b border-outline-variant"><h3 class="font-title-sm text-title-sm text-primary">${isNew ? 'Profil Baru' : esc(p.name)}</h3></div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <label class="block"><span class="text-[11px] text-on-surface-variant">Nama</span>
            <input id="g-name" value="${esc(p.name)}" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm"/></label>
          <label class="block"><span class="text-[11px] text-on-surface-variant">Slug</span>
            <input id="g-slug" ${isNew ? '' : 'disabled'} value="${esc(p.slug)}" placeholder="noc-operator" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm font-data-mono disabled:bg-surface-container"/></label>
        </div>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Deskripsi</span>
          <input id="g-desc" value="${esc(p.description)}" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm"/></label>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Prompt / persona</span>
          <textarea id="g-prompt" rows="16" spellcheck="false" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-data-mono font-data-mono">${esc(p.prompt)}</textarea></label>
        <div id="g-err" class="text-red-600 text-body-sm"></div>
        <div class="flex flex-wrap items-center gap-2">
          <button id="g-save" class="px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90">Simpan</button>
          ${isNew ? '' : `
            <button id="g-use" class="px-3 py-2 border border-outline-variant rounded-lg text-body-sm text-primary hover:bg-surface-container">${isActive ? 'Berhenti pakai di chat Hermes' : 'Pakai di chat Hermes'}</button>
            <button id="g-soul" class="px-3 py-2 border border-outline-variant rounded-lg text-body-sm text-primary hover:bg-surface-container">Terapkan ke SOUL.md NetOps Agent</button>
            <span class="flex-1"></span>
            <button id="g-delete" class="px-3 py-2 border border-red-300 text-red-700 rounded-lg text-body-sm hover:bg-red-50">Hapus</button>`}
        </div>
      </div>
    </div>`;
    $('g-save').onclick = save;
    if ($('g-use')) $('g-use').onclick = () => { setActiveProfile(isActive ? null : p.slug); renderList(); renderEditor(); };
    if ($('g-soul')) $('g-soul').onclick = applySoul;
    if ($('g-delete')) $('g-delete').onclick = del;
  }

  const form = () => ({ slug: $('g-slug').value.trim(), name: $('g-name').value.trim(), description: $('g-desc').value.trim(), prompt: $('g-prompt').value });

  async function save() {
    const f = form(), err = $('g-err');
    if (!f.name) { err.textContent = 'Nama wajib diisi.'; return; }
    if (isNew && !SLUG_RE.test(f.slug)) { err.textContent = 'Slug harus huruf kecil/angka/strip, maksimal 64 karakter.'; return; }
    try {
      const saved = isNew ? await mgr('/profiles', { method: 'POST', body: f }) : await mgr('/profiles/' + f.slug, { method: 'PUT', body: f });
      isNew = false; await load(); select(saved.slug);
    } catch (e) { err.textContent = e.message; }
  }

  async function applySoul() {
    const cur = await mgr('/backends/netops/soul').catch(() => null);
    const ok = await confirmDialog({
      title: 'Timpa SOUL.md NetOps Agent?',
      message: `Isi SOUL.md saat ini akan diganti dengan prompt profil ini dan berlaku untuk semua sesi NetOps Agent berikutnya.${cur?.exists ? ' Versi lama disimpan sebagai backup di server NetOpsUI.' : ''}`,
      confirmLabel: 'Terapkan', danger: true,
    });
    if (!ok) return;
    try { await mgr(`/profiles/${selected}/apply-soul`, { method: 'POST' }); await alertDialog('SOUL.md NetOps Agent diperbarui.', 'Berhasil'); }
    catch (e) { $('g-err').textContent = e.message; }
  }

  async function del() {
    const ok = await confirmDialog({ title: 'Hapus profil?', message: `"${selected}" akan dihapus dari NetOpsUI. SOUL.md NetOps Agent yang sudah pernah diterapkan tidak berubah.`, confirmLabel: 'Hapus', danger: true });
    if (!ok) return;
    try {
      await mgr('/profiles/' + selected, { method: 'DELETE' });
      if (getActiveProfile() === selected) setActiveProfile(null);
      selected = null; await load();
    } catch (e) { $('g-err').textContent = e.message; }
  }

  function select(slug) { selected = slug; isNew = false; renderList(); renderEditor(); }
  $('ag-new').onclick = () => { isNew = true; selected = null; renderList(); renderEditor(); };

  async function load() {
    try { profiles = (await mgr('/profiles')).profiles; renderList(); }
    catch (e) { $('ag-list').innerHTML = errorHtml('Gagal memuat profil: ' + e.message); }
  }

  await load();
  renderEditor();
}
