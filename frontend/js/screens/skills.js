import { $, esc, badge, pageHeader, loadingHtml, errorHtml, confirmDialog, alertDialog } from '../utils.js';
import { BACKENDS, activeBackend } from '../backends/index.js';
import { mgr } from '../manager.js';

const STATUS = {
  draft:        ['Draft', 'gray'],
  in_sync:      ['Tersinkron', 'green'],
  db_changed:   ['Perlu publish', 'amber'],
  disk_changed: ['Diubah di backend', 'red'],
  missing:      ['File hilang', 'red'],
};
const SLUG_RE = /^[a-z0-9][a-z0-9-]{0,63}$/;

// Skill library managed in NetOpsUI's DB. "Publish" writes SKILL.md into the
// backend's skills folder; the backends only list skills, they can't edit them.
export async function screenSkills(c) {
  let skills = [], disk = [], selected = null, isNew = false;

  c.innerHTML = `<div class="p-container_gutter max-w-[1700px] mx-auto">
    ${pageHeader('Skills', 'Kelola skill di NetOpsUI, lalu publish ke folder skill NetOps Agent atau Hermes.', `
      <button id="sk-new" class="px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 flex items-center gap-1"><span class="material-symbols-outlined text-[18px]">add</span>Skill Baru</button>`)}
    <div class="grid grid-cols-12 gap-6">
      <div class="col-span-12 xl:col-span-4 space-y-6">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-5 py-3 border-b border-outline-variant text-label-caps font-label-caps text-on-surface-variant">Library NetOpsUI</div>
          <div id="sk-list" class="max-h-[420px] overflow-y-auto">${loadingHtml('Memuat...')}</div>
        </div>
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-5 py-3 border-b border-outline-variant flex justify-between items-center">
            <span class="text-label-caps font-label-caps text-on-surface-variant">Di disk <span id="sk-disk-name"></span></span>
          </div>
          <div id="sk-disk" class="max-h-[320px] overflow-y-auto">${loadingHtml('Memuat...')}</div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-8"><div id="sk-editor"></div></div>
    </div>
  </div>`;

  const backend = activeBackend();
  $('sk-disk-name').textContent = `(${backend.label})`;

  function statusPills(s) {
    return Object.entries(s.publications).map(([b, p]) => {
      const [label, v] = STATUS[p.status] || STATUS.draft;
      return `<span class="text-[10px] text-on-surface-variant">${esc(BACKENDS[b].shortLabel)}: ${badge(label, v)}</span>`;
    }).join('');
  }

  function renderList() {
    $('sk-list').innerHTML = skills.length ? skills.map(s => `
      <button data-slug="${esc(s.slug)}" class="w-full text-left px-5 py-3 border-b border-outline-variant hover:bg-surface-container-low transition-colors ${selected === s.slug ? 'bg-surface-container-low' : ''}">
        <p class="font-data-mono text-data-mono text-primary font-semibold truncate">${esc(s.slug)}</p>
        <p class="text-[11px] text-on-surface-variant truncate">${esc(s.description || '—')}</p>
        <div class="flex flex-wrap gap-2 mt-1.5">${statusPills(s)}</div>
      </button>`).join('')
      : `<p class="p-5 text-body-sm text-on-surface-variant">Belum ada skill. Buat baru atau import dari disk.</p>`;
    $('sk-list').querySelectorAll('[data-slug]').forEach(b => { b.onclick = () => select(b.dataset.slug); });
  }

  function renderDisk() {
    const rows = disk.filter(d => !d.managed);
    $('sk-disk').innerHTML = rows.length ? rows.map(d => `
      <div class="px-5 py-2.5 border-b border-outline-variant flex items-center gap-3">
        <div class="min-w-0 flex-1">
          <p class="font-data-mono-sm text-data-mono-sm text-primary truncate" title="${esc(d.path)}">${esc(d.name)}</p>
          <p class="text-[10px] text-on-surface-variant truncate">${esc(d.category ? d.category + ' · ' : '')}${esc(d.description || '—')}</p>
        </div>
        <button data-import="${esc(d.path)}" class="shrink-0 px-2.5 py-1 border border-outline-variant rounded text-[11px] text-primary hover:bg-surface-container">Import</button>
      </div>`).join('')
      : `<p class="p-5 text-body-sm text-on-surface-variant">Semua skill di disk sudah ada di library.</p>`;
    $('sk-disk').querySelectorAll('[data-import]').forEach(b => {
      b.onclick = async () => {
        b.disabled = true;
        try { const s = await mgr('/skills/import', { method: 'POST', body: { backend: backend.id, path: b.dataset.import } }); await load(); select(s.slug); }
        catch (e) { b.disabled = false; await alertDialog(e.message, 'Gagal import'); }
      };
    });
  }

  function renderEditor() {
    const el = $('sk-editor');
    if (!isNew && !selected) {
      el.innerHTML = `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 text-center text-body-sm text-on-surface-variant">Pilih skill di kiri, atau buat skill baru.</div>`;
      return;
    }
    const s = isNew ? { slug: '', description: '', tags: [], body: '', publications: {} } : skills.find(x => x.slug === selected);
    if (!s) { el.innerHTML = ''; return; }
    const pubBtns = isNew ? '' : Object.keys(BACKENDS).map(b => {
      const p = s.publications[b];
      const published = p && p.status !== 'draft';
      return `<button data-publish="${b}" class="px-3 py-2 border border-outline-variant rounded-lg text-body-sm text-primary hover:bg-surface-container">Publish ke ${esc(BACKENDS[b].shortLabel)}</button>
        ${published ? `<button data-unpublish="${b}" class="px-2 py-2 text-[11px] text-on-surface-variant hover:text-red-600" title="Hapus file dari ${esc(b)}">cabut</button>` : ''}`;
    }).join('');
    el.innerHTML = `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg">
      <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
        <h3 class="font-title-sm text-title-sm text-primary">${isNew ? 'Skill Baru' : esc(s.slug)}</h3>
        ${isNew ? '' : `<div class="flex gap-3">${statusPills(s)}</div>`}
      </div>
      <div class="p-6 space-y-4">
        <div class="grid grid-cols-2 gap-4">
          <label class="block"><span class="text-[11px] text-on-surface-variant">Slug (nama folder)</span>
            <input id="f-slug" ${isNew ? '' : 'disabled'} value="${esc(s.slug)}" placeholder="cek-bgp-neighbor" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm font-data-mono bg-surface-container-lowest disabled:bg-surface-container"/></label>
          <label class="block"><span class="text-[11px] text-on-surface-variant">Tags (pisahkan koma)</span>
            <input id="f-tags" value="${esc(s.tags.join(', '))}" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm"/></label>
        </div>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Deskripsi (dipakai agent untuk memutuskan kapan skill ini relevan)</span>
          <input id="f-desc" value="${esc(s.description)}" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm"/></label>
        <label class="block"><span class="text-[11px] text-on-surface-variant">Isi skill (Markdown)</span>
          <textarea id="f-body" rows="18" spellcheck="false" class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-data-mono font-data-mono">${esc(s.body)}</textarea></label>
        <div id="f-err" class="text-red-600 text-body-sm"></div>
        <div class="flex flex-wrap items-center gap-2">
          <button id="f-save" class="px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90">Simpan</button>
          ${pubBtns}
          <span class="flex-1"></span>
          ${isNew ? '' : '<button id="f-delete" class="px-3 py-2 border border-red-300 text-red-700 rounded-lg text-body-sm hover:bg-red-50">Hapus</button>'}
        </div>
      </div>
    </div>`;
    $('f-save').onclick = save;
    el.querySelectorAll('[data-publish]').forEach(b => { b.onclick = () => publish(b.dataset.publish); });
    el.querySelectorAll('[data-unpublish]').forEach(b => { b.onclick = () => unpublish(b.dataset.unpublish); });
    if ($('f-delete')) $('f-delete').onclick = del;
  }

  function form() {
    return {
      slug: $('f-slug').value.trim(),
      description: $('f-desc').value.trim(),
      tags: $('f-tags').value.split(',').map(t => t.trim()).filter(Boolean),
      body: $('f-body').value,
    };
  }

  async function save() {
    const f = form(), err = $('f-err');
    if (isNew && !SLUG_RE.test(f.slug)) { err.textContent = 'Slug harus huruf kecil/angka/strip, maksimal 64 karakter.'; return; }
    try {
      const saved = isNew ? await mgr('/skills', { method: 'POST', body: f }) : await mgr('/skills/' + f.slug, { method: 'PUT', body: f });
      isNew = false; await load(); select(saved.slug);
    } catch (e) { err.textContent = e.message; }
  }

  async function publish(b) {
    const slug = selected, f = form();
    // Publish what is on screen: save first so an unsaved edit is not silently skipped.
    try { await mgr('/skills/' + slug, { method: 'PUT', body: f }); } catch (e) { $('f-err').textContent = e.message; return; }
    const call = force => mgr(`/skills/${slug}/publish`, { method: 'POST', body: { backend: b, force } });
    try { await call(false); }
    catch (e) {
      if (e.status !== 409) { $('f-err').textContent = e.message; return; }
      const ok = await confirmDialog({ title: 'Timpa file di backend?', message: e.message, confirmLabel: 'Timpa', danger: true });
      if (!ok) return;
      try { await call(true); } catch (e2) { $('f-err').textContent = e2.message; return; }
    }
    await load(); select(slug);
  }

  async function unpublish(b) {
    const ok = await confirmDialog({ title: 'Cabut skill dari backend?', message: `File SKILL.md akan dihapus dari folder skill ${BACKENDS[b].label}. Skill tetap ada di library NetOpsUI.`, confirmLabel: 'Cabut', danger: true });
    if (!ok) return;
    try { await mgr(`/skills/${selected}/unpublish`, { method: 'POST', body: { backend: b } }); await load(); select(selected); }
    catch (e) { $('f-err').textContent = e.message; }
  }

  async function del() {
    const s = skills.find(x => x.slug === selected);
    const published = Object.entries(s.publications).filter(([, p]) => p.status !== 'draft').map(([b]) => BACKENDS[b].shortLabel);
    const ok = await confirmDialog({
      title: 'Hapus skill?',
      message: `"${selected}" dihapus dari library NetOpsUI.` + (published.length ? ` File yang sudah dipublish ke ${published.join(' & ')} TIDAK ikut dihapus (cabut dulu lewat tombol "cabut" bila perlu).` : ''),
      confirmLabel: 'Hapus', danger: true,
    });
    if (!ok) return;
    try { await mgr('/skills/' + selected, { method: 'DELETE' }); selected = null; await load(); }
    catch (e) { $('f-err').textContent = e.message; }
  }

  function select(slug) { selected = slug; isNew = false; renderList(); renderEditor(); }

  $('sk-new').onclick = () => { isNew = true; selected = null; renderList(); renderEditor(); };

  async function load() {
    const [a, b] = await Promise.allSettled([mgr('/skills'), mgr(`/backends/${backend.id}/disk-skills`)]);
    if (a.status === 'rejected') {
      $('sk-list').innerHTML = errorHtml('Gagal memuat library: ' + a.reason.message);
      $('sk-editor').innerHTML = '';
    } else { skills = a.value.skills; renderList(); }
    if (b.status === 'rejected') $('sk-disk').innerHTML = errorHtml('Gagal membaca disk: ' + b.reason.message);
    else { disk = b.value.skills; renderDisk(); }
  }

  await load();
  renderEditor();
}
