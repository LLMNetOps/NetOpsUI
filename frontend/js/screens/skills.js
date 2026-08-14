import { apiGet, apiPost, apiPut, apiDelete } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml, confirmDialog, alertDialog } from '../utils.js';
import { mountTagInput } from '../tag-input.js';

const KNOWN_DOMAINS = ['monitoring', 'routing', 'config', 'security', 'dhcp', 'netbox', 'report', 'general'];
const PAGE_SIZE = 10;
const STATUS_OPTIONS = [
  { key: 'enabled',  label: 'Enabled' },
  { key: 'disabled', label: 'Disabled' },
  { key: 'approval', label: 'Requires Approval' },
  { key: 'modified', label: 'Modified' },
];

let _skillsCache = [];
let _domainFilter = new Set(); // empty = no domain filter (show all)
let _statusFilter = new Set(); // empty = no status filter (show all)
let _filteredList = [];
let _currentPage = 1;
let _selectedName = null; // name of the skill shown in the detail panel (edit mode)
let _creating = false;    // true while the detail panel is showing the "new skill" form
let _detailCache = {};    // name -> full skill payload (with body), invalidated on save/restore/delete
let _toolNamesCache = null;
let _docClickHandler = null;

async function getToolNames() {
  if (!_toolNamesCache) {
    const r = await apiGet('/api/tool-names');
    _toolNamesCache = r.tools || [];
  }
  return _toolNamesCache;
}

export async function screenSkills(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Skill Library', 'Kelola prosedur agent. Pilih skill di kiri untuk edit — perubahan hot-reload, tanpa restart server.', `
      <button id="btn-create-skill" class="px-4 py-2 bg-primary text-white rounded font-body-md hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">add</span> New Skill
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg items-start">
      <div class="col-span-12 xl:col-span-5 space-y-stack_gap_lg">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-6 py-3 border-b border-outline-variant flex flex-wrap gap-2 items-center justify-between">
            <span class="text-label-caps font-label-caps text-on-surface-variant">Klik ikon filter di kolom Domain / Status untuk memilih beberapa sekaligus.</span>
            <input id="skills-search" type="text" placeholder="Filter skill..." class="px-3 py-1.5 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary w-48">
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
                <th class="py-3 px-4">Skill Name</th>
                <th class="py-3 px-4">
                  <button id="th-domain-filter-btn" type="button" class="flex items-center gap-1 hover:text-primary transition-colors">
                    <span>Domain</span>
                    <span id="th-domain-filter-icon" class="material-symbols-outlined text-[14px]">filter_list</span>
                  </button>
                </th>
                <th class="py-3 px-4">
                  <button id="th-status-filter-btn" type="button" class="flex items-center gap-1 hover:text-primary transition-colors">
                    <span>Status</span>
                    <span id="th-status-filter-icon" class="material-symbols-outlined text-[14px]">filter_list</span>
                  </button>
                </th>
              </tr></thead>
              <tbody id="skills-tbody" class="divide-y divide-outline-variant"><tr><td class="py-8 text-center" colspan="3">${loadingHtml()}</td></tr></tbody>
            </table>
          </div>
          <div id="skills-pagination" class="px-4 py-3 border-t border-outline-variant flex items-center justify-between gap-4 flex-wrap"></div>
        </div>
        <div id="th-domain-filter-dropdown" class="hidden fixed z-30 w-56 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg py-2 normal-case font-body-sm text-on-surface"></div>
        <div id="th-status-filter-dropdown" class="hidden fixed z-30 w-56 bg-surface-container-lowest border border-outline-variant rounded-lg shadow-lg py-2 normal-case font-body-sm text-on-surface"></div>
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-5 py-4 border-b border-outline-variant">
            <h3 class="font-title-sm text-title-sm text-primary">Pending Skills</h3>
          </div>
          <div id="skills-pending" class="p-4">${loadingHtml('Memuat pending...')}</div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-7">
        <div id="skill-detail-panel" class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          ${emptyPanelHtml()}
        </div>
      </div>
    </div>
  </div>`;

  const createBtn = $('btn-create-skill');
  if (createBtn) createBtn.onclick = startCreate;

  const searchEl = $('skills-search');
  if (searchEl) searchEl.oninput = () => applyFilter();

  setupFilterDropdown('th-domain-filter-btn', 'th-domain-filter-dropdown');
  setupFilterDropdown('th-status-filter-btn', 'th-status-filter-dropdown');
  renderStatusDropdown();

  if (_docClickHandler) document.removeEventListener('click', _docClickHandler);
  _docClickHandler = () => closeAllFilterDropdowns();
  document.addEventListener('click', _docClickHandler);

  _selectedName = null;
  _creating = false;
  _domainFilter = new Set();
  _statusFilter = new Set();
  await Promise.all([loadSkills(), loadPending()]);
}

// ── Column filter dropdowns (Domain / Status) ─────────────────────────────────

function closeAllFilterDropdowns() {
  ['th-domain-filter-dropdown', 'th-status-filter-dropdown'].forEach(id => {
    const el = $(id);
    if (el) el.classList.add('hidden');
  });
}

function setupFilterDropdown(btnId, dropdownId) {
  const btn = $(btnId);
  const dd = $(dropdownId);
  if (!btn || !dd) return;
  btn.onclick = e => {
    e.stopPropagation();
    const wasOpen = !dd.classList.contains('hidden');
    closeAllFilterDropdowns();
    if (!wasOpen) {
      const r = btn.getBoundingClientRect();
      dd.style.top = `${r.bottom + 4}px`;
      dd.style.left = `${r.left}px`;
      dd.classList.remove('hidden');
    }
  };
  dd.onclick = e => e.stopPropagation();
}

function updateFilterIcons() {
  const dIcon = $('th-domain-filter-icon');
  if (dIcon) dIcon.classList.toggle('text-primary', _domainFilter.size > 0);
  const sIcon = $('th-status-filter-icon');
  if (sIcon) sIcon.classList.toggle('text-primary', _statusFilter.size > 0);
}

function checklistDropdownHtml(title, options, selected, clearAttr) {
  return `<div class="px-3 pb-2 flex items-center justify-between border-b border-outline-variant mb-1">
    <span class="text-label-caps font-label-caps text-outline">${esc(title)}</span>
    <button ${clearAttr} class="text-label-caps font-label-caps text-primary hover:underline">Clear</button>
  </div>
  <div class="max-h-64 overflow-y-auto px-1">
    ${options.map(o => `<label class="flex items-center gap-2 px-2 py-1.5 rounded hover:bg-surface-container-low cursor-pointer">
      <input type="checkbox" data-check="${esc(o.key)}" class="w-4 h-4 accent-primary" ${selected.has(o.key) ? 'checked' : ''}>
      <span class="text-body-sm">${esc(o.label)}</span>
    </label>`).join('') || `<p class="text-body-sm text-on-surface-variant px-2 py-1.5">Tidak ada opsi.</p>`}
  </div>`;
}

function renderDomainDropdown() {
  const el = $('th-domain-filter-dropdown');
  if (!el) return;
  const domains = [...new Set(_skillsCache.map(s => s.domain).filter(Boolean))].sort()
    .map(d => ({ key: d, label: d }));
  el.innerHTML = checklistDropdownHtml('Filter Domain', domains, _domainFilter, 'data-clear-domain');
  el.querySelectorAll('[data-check]').forEach(cb => {
    cb.onchange = () => {
      const d = cb.dataset.check;
      if (cb.checked) _domainFilter.add(d); else _domainFilter.delete(d);
      updateFilterIcons();
      applyFilter();
    };
  });
  el.querySelector('[data-clear-domain]').onclick = () => {
    _domainFilter.clear();
    renderDomainDropdown();
    updateFilterIcons();
    applyFilter();
  };
}

function renderStatusDropdown() {
  const el = $('th-status-filter-dropdown');
  if (!el) return;
  el.innerHTML = checklistDropdownHtml('Filter Status', STATUS_OPTIONS, _statusFilter, 'data-clear-status');
  el.querySelectorAll('[data-check]').forEach(cb => {
    cb.onchange = () => {
      const k = cb.dataset.check;
      if (cb.checked) _statusFilter.add(k); else _statusFilter.delete(k);
      updateFilterIcons();
      applyFilter();
    };
  });
  el.querySelector('[data-clear-status]').onclick = () => {
    _statusFilter.clear();
    renderStatusDropdown();
    updateFilterIcons();
    applyFilter();
  };
}

function emptyPanelHtml() {
  return `<div class="p-12 flex flex-col items-center justify-center text-center">
    <span class="material-symbols-outlined text-5xl text-outline-variant mb-3">psychology</span>
    <p class="text-body-sm text-on-surface-variant">Pilih skill di tabel untuk melihat dan mengedit, atau buat skill baru.</p>
  </div>`;
}

async function loadSkills() {
  try {
    const r = await apiGet('/api/skills');
    _skillsCache = r.skills || [];
    renderDomainDropdown();
    applyFilter();
    // If a row was selected (e.g. right after save/restore), refresh its panel in place
    if (_selectedName && _skillsCache.some(s => s.name === _selectedName)) {
      await renderDetailPanel(_selectedName);
    }
  } catch (e) {
    const tb = $('skills-tbody');
    if (tb) tb.innerHTML = `<tr><td class="py-6 px-4 text-center" colspan="3">${errorHtml('Gagal memuat skills: ' + e.message)}</td></tr>`;
  }
}

async function loadPending() {
  const el = $('skills-pending');
  if (!el) return;
  try {
    const r = await apiGet('/api/skills/pending');
    const items = r.pending || [];
    if (!items.length) {
      el.innerHTML = `<p class="text-body-sm text-on-surface-variant py-2">Tidak ada skill pending.</p>`;
      return;
    }
    el.innerHTML = items.map(p => `<div class="border border-outline-variant rounded-lg p-3 mb-3 last:mb-0">
      <p class="font-data-mono text-data-mono text-primary mb-2">${esc(p.name)}</p>
      <p class="text-label-caps font-label-caps text-on-surface-variant mb-3">${esc(p.path)}</p>
      <div class="flex gap-2">
        <button data-approve-pending="${esc(p.name)}" class="flex-1 px-2 py-1 bg-green-600 text-white text-label-caps font-label-caps rounded hover:bg-green-700 transition-colors">Approve</button>
        <button data-reject-pending="${esc(p.name)}" class="flex-1 px-2 py-1 bg-red-600 text-white text-label-caps font-label-caps rounded hover:bg-red-700 transition-colors">Reject</button>
      </div>
    </div>`).join('');

    el.querySelectorAll('[data-approve-pending]').forEach(btn => {
      btn.onclick = () => approvePendingSkill(btn.dataset.approvePending);
    });
    el.querySelectorAll('[data-reject-pending]').forEach(btn => {
      btn.onclick = () => rejectPendingSkill(btn.dataset.rejectPending);
    });
  } catch (e) {
    el.innerHTML = errorHtml(e.message);
  }
}

function applyFilter() {
  const q = ($('skills-search') || {}).value?.toLowerCase() || '';
  _filteredList = _skillsCache.filter(s => {
    if (_domainFilter.size && !_domainFilter.has(s.domain)) return false;
    if (_statusFilter.size) {
      const flags = new Set([s.enabled !== false ? 'enabled' : 'disabled']);
      if (s.approval_required) flags.add('approval');
      if (s.has_default) flags.add('modified');
      if (![..._statusFilter].some(f => flags.has(f))) return false;
    }
    if (q && !(s.name || '').toLowerCase().includes(q) && !(s.domain || '').toLowerCase().includes(q)) return false;
    return true;
  });
  _currentPage = 1;
  renderRows();
}

function renderRows() {
  const tb = $('skills-tbody');
  if (!tb) return;

  const total = _filteredList.length;
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  if (_currentPage > totalPages) _currentPage = totalPages;

  if (!total) {
    tb.innerHTML = `<tr><td class="py-8 px-4 text-center text-on-surface-variant text-body-sm" colspan="3">Tidak ada skill ditemukan.</td></tr>`;
    renderPagination(0, 1, 1);
    return;
  }

  const start = (_currentPage - 1) * PAGE_SIZE;
  const page = _filteredList.slice(start, start + PAGE_SIZE);

  tb.innerHTML = page.map(s => {
    const isSelected = !_creating && _selectedName === s.name;
    return `<tr data-row-select="${esc(s.name)}" class="cursor-pointer transition-colors ${isSelected ? 'bg-primary/5 border-l-[3px] border-l-primary' : 'hover:bg-surface-container-low border-l-[3px] border-l-transparent'}">
    <td class="py-2.5 px-4">
      <p class="font-data-mono text-data-mono font-medium text-primary truncate max-w-[180px]">${esc(s.name)}</p>
    </td>
    <td class="py-2.5 px-4">${s.domain ? badge(s.domain, 'blue') : '—'}</td>
    <td class="py-2.5 px-4">
      <div class="flex flex-wrap items-center gap-1">
        ${badge(s.enabled !== false ? 'ENABLED' : 'DISABLED', s.enabled !== false ? 'green' : 'gray')}
        ${s.approval_required ? badge('APPROVAL', 'amber') : ''}
        ${s.has_default ? badge('MODIFIED', 'amber') : ''}
      </div>
    </td>
  </tr>`;
  }).join('');

  tb.querySelectorAll('[data-row-select]').forEach(row => {
    row.onclick = () => selectSkill(row.dataset.rowSelect);
  });

  renderPagination(total, _currentPage, totalPages);
}

function renderPagination(total, current, totalPages) {
  const el = $('skills-pagination');
  if (!el) return;

  if (totalPages <= 1 && total <= PAGE_SIZE) {
    el.innerHTML = total
      ? `<span class="text-label-caps font-label-caps text-on-surface-variant">${total} skill</span>`
      : '';
    return;
  }

  const start = (current - 1) * PAGE_SIZE + 1;
  const end = Math.min(current * PAGE_SIZE, total);

  const btnBase = 'min-w-[32px] h-8 px-2 text-label-caps font-label-caps rounded transition-colors';
  const btnActive = `${btnBase} bg-primary text-white`;
  const btnNormal = `${btnBase} border border-outline-variant text-on-surface-variant hover:bg-surface-container-low`;
  const btnDisabled = `${btnBase} border border-outline-variant text-on-surface-variant/30 cursor-not-allowed`;

  function pageBtn(n) {
    if (n === current) return `<button class="${btnActive}" data-page="${n}">${n}</button>`;
    return `<button class="${btnNormal}" data-page="${n}">${n}</button>`;
  }

  function buildPageNumbers() {
    if (totalPages <= 7) {
      return Array.from({ length: totalPages }, (_, i) => pageBtn(i + 1)).join('');
    }
    const pages = [];
    pages.push(pageBtn(1));
    if (current > 3) pages.push(`<span class="text-on-surface-variant px-1">…</span>`);
    const lo = Math.max(2, current - 1);
    const hi = Math.min(totalPages - 1, current + 1);
    for (let i = lo; i <= hi; i++) pages.push(pageBtn(i));
    if (current < totalPages - 2) pages.push(`<span class="text-on-surface-variant px-1">…</span>`);
    pages.push(pageBtn(totalPages));
    return pages.join('');
  }

  el.innerHTML = `
    <span class="text-label-caps font-label-caps text-on-surface-variant">
      Showing ${start}–${end} of ${total} skills
    </span>
    <div class="flex items-center gap-1">
      <button class="${current === 1 ? btnDisabled : btnNormal}" data-page="${current - 1}" ${current === 1 ? 'disabled' : ''}>
        <span class="material-symbols-outlined text-[16px]">chevron_left</span>
      </button>
      ${buildPageNumbers()}
      <button class="${current === totalPages ? btnDisabled : btnNormal}" data-page="${current + 1}" ${current === totalPages ? 'disabled' : ''}>
        <span class="material-symbols-outlined text-[16px]">chevron_right</span>
      </button>
    </div>`;

  el.querySelectorAll('[data-page]').forEach(btn => {
    if (!btn.disabled) btn.onclick = () => {
      _currentPage = parseInt(btn.dataset.page);
      renderRows();
    };
  });
}

async function startCreate() {
  _creating = true;
  _selectedName = null;
  renderRows();
  const panel = $('skill-detail-panel');
  panel.innerHTML = editFormHtml(null, false);
  await wireEditForm(null, false);
}

async function selectSkill(name) {
  _creating = false;
  _selectedName = name;
  renderRows();
  await renderDetailPanel(name);
}

async function renderDetailPanel(name) {
  const panel = $('skill-detail-panel');
  if (!panel) return;
  panel.innerHTML = loadingHtml('Memuat detail skill...');

  try {
    const skill = _detailCache[name] || await apiGet(`/api/skills/${encodeURIComponent(name)}`);
    _detailCache[name] = skill;
    if (_selectedName !== name) return; // user already clicked another row while this was loading
    panel.innerHTML = editFormHtml(skill, true);
    await wireEditForm(skill, true);
  } catch (e) {
    if (_selectedName !== name) return;
    panel.innerHTML = errorHtml('Gagal memuat skill: ' + e.message);
  }
}

function editFormHtml(skill, isEdit) {
  return `<div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
    <h3 class="font-title-sm text-title-sm text-primary font-bold">${isEdit ? esc(skill.name) : 'New Skill'}</h3>
    <button id="sf-close" class="text-on-surface-variant hover:text-primary transition-colors p-1 rounded" title="Tutup"><span class="material-symbols-outlined text-[20px]">close</span></button>
  </div>
  <div class="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
    <div id="sf-error" class="hidden"></div>
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Skill Name *</label>
        <input id="sf-name" type="text" value="${esc(skill?.name || '')}" ${isEdit ? 'readonly' : ''} placeholder="e.g. network-health-check" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary ${isEdit ? 'bg-surface-container-low text-on-surface-variant' : ''}">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Domain *</label>
        <select id="sf-domain" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
          ${KNOWN_DOMAINS.map(d => `<option value="${d}" ${skill?.domain === d ? 'selected' : ''}>${d}</option>`).join('')}
        </select>
      </div>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Triggers</label>
      <div id="sf-triggers"></div>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Tools</label>
      <div id="sf-tools"></div>
    </div>
    <div class="flex gap-6">
      <label class="flex items-center gap-2 cursor-pointer">
        <input id="sf-enabled" type="checkbox" ${skill?.enabled !== false ? 'checked' : ''} class="w-4 h-4 accent-primary">
        <span class="text-body-sm text-on-surface-variant">Enabled</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input id="sf-approval" type="checkbox" ${skill?.approval_required ? 'checked' : ''} class="w-4 h-4 accent-amber-500">
        <span class="text-body-sm text-on-surface-variant">Requires Approval</span>
      </label>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Skill Body (Bahasa Indonesia)</label>
      <textarea id="sf-body" rows="14" placeholder="Tulis prosedur skill di sini dalam Bahasa Indonesia..." class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"></textarea>
    </div>
  </div>
  <div class="flex justify-between items-center px-6 py-4 border-t border-outline-variant">
    <div class="flex gap-3">
      ${isEdit ? `<button id="sf-delete" class="px-4 py-2 border border-red-200 text-red-600 rounded text-body-sm hover:bg-red-50 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">delete</span>Hapus
      </button>` : ''}
      ${isEdit && skill?.has_default
        ? `<button id="sf-restore" class="px-4 py-2 border border-amber-200 text-amber-700 rounded text-body-sm hover:bg-amber-50 transition-colors flex items-center gap-2">
             <span class="material-symbols-outlined text-sm">restart_alt</span>Restore Default
           </button>`
        : ''}
    </div>
    <div class="flex gap-3">
      <button id="sf-cancel" class="px-4 py-2 border border-outline-variant rounded text-body-sm text-on-surface-variant hover:bg-surface-container-low transition-colors">${isEdit ? 'Reset' : 'Batal'}</button>
      <button id="sf-save" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Skill'}
      </button>
    </div>
  </div>`;
}

async function wireEditForm(skill, isEdit) {
  // Set textarea value directly — bypasses HTML parsing of potentially large text
  $('sf-body').value = skill?.body || '';

  const toolNames = await getToolNames();
  const toolsWidget = mountTagInput($('sf-tools'), { initial: skill?.tools || [], options: toolNames, placeholder: 'Cari tool...' });
  const triggersWidget = mountTagInput($('sf-triggers'), { initial: skill?.triggers || [], options: [], placeholder: 'Ketik trigger lalu Enter...' });

  $('sf-close').onclick = () => {
    _creating = false;
    _selectedName = null;
    renderRows();
    $('skill-detail-panel').innerHTML = emptyPanelHtml();
  };

  // Reset/Batal re-renders the panel from the last-loaded (cached) data, discarding edits
  $('sf-cancel').onclick = async () => {
    if (isEdit) {
      $('skill-detail-panel').innerHTML = editFormHtml(skill, true);
      await wireEditForm(skill, true);
    } else {
      $('sf-close').click();
    }
  };

  const deleteBtn = $('sf-delete');
  if (deleteBtn) deleteBtn.onclick = () => deleteSkillByName(skill.name);

  const restoreBtn = $('sf-restore');
  if (restoreBtn) restoreBtn.onclick = async () => {
    const ok = await confirmDialog({
      title: 'Restore ke default?',
      message: `Semua perubahan pada skill "${skill.name}" akan dikembalikan ke versi default dari repo. Tindakan ini tidak bisa dibatalkan.`,
      confirmLabel: 'Restore', danger: true,
    });
    if (!ok) return;
    try {
      await apiPost(`/api/skills/${encodeURIComponent(skill.name)}/restore`, {});
      delete _detailCache[skill.name];
      await skillsRefresh();
    } catch (e) {
      await alertDialog('Gagal restore: ' + e.message, 'Terjadi Kesalahan');
    }
  };

  $('sf-save').onclick = async () => {
    const errEl = $('sf-error');
    const saveBtn = $('sf-save');
    const name = ($('sf-name').value || '').trim();
    const domain = $('sf-domain').value;
    const body = ($('sf-body').value || '').trim();
    const enabled = $('sf-enabled').checked;
    const approval_required = $('sf-approval').checked;

    if (!name) { errEl.innerHTML = errorHtml('Nama skill wajib diisi.'); errEl.classList.remove('hidden'); return; }
    if (!body) { errEl.innerHTML = errorHtml('Body skill wajib diisi.'); errEl.classList.remove('hidden'); return; }

    const payload = {
      name, domain, body, enabled, approval_required,
      triggers: triggersWidget.getValues(),
      tools: toolsWidget.getValues(),
    };

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Menyimpan...';

    try {
      if (isEdit) {
        await apiPut(`/api/skills/${encodeURIComponent(skill.name)}`, payload);
        delete _detailCache[skill.name];
      } else {
        await apiPost('/api/skills', payload);
        _creating = false;
        _selectedName = name;
      }
      await skillsRefresh();
    } catch (e) {
      errEl.innerHTML = errorHtml(e.message || 'Gagal menyimpan skill.');
      errEl.classList.remove('hidden');
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Skill'}`;
    }
  };
}

async function deleteSkillByName(name) {
  const ok = await confirmDialog({
    title: 'Hapus skill?', message: `Skill "${name}" akan dihapus permanen. Tindakan ini tidak bisa dibatalkan.`,
    confirmLabel: 'Hapus', danger: true,
  });
  if (!ok) return;
  try {
    await apiDelete(`/api/skills/${encodeURIComponent(name)}`);
    delete _detailCache[name];
    if (_selectedName === name) {
      _selectedName = null;
      $('skill-detail-panel').innerHTML = emptyPanelHtml();
    }
    await skillsRefresh();
  } catch (e) {
    await alertDialog('Gagal menghapus: ' + e.message, 'Terjadi Kesalahan');
  }
}

async function approvePendingSkill(name) {
  const ok = await confirmDialog({ title: 'Approve skill?', message: `Skill pending "${name}" akan diaktifkan.`, confirmLabel: 'Approve' });
  if (!ok) return;
  try {
    await apiPost(`/api/skills/pending/${encodeURIComponent(name)}/approve`, {});
    await skillsRefresh();
  } catch (e) {
    await alertDialog('Gagal approve: ' + e.message, 'Terjadi Kesalahan');
  }
}

async function rejectPendingSkill(name) {
  const ok = await confirmDialog({
    title: 'Reject skill?', message: `Skill pending "${name}" akan dihapus.`,
    confirmLabel: 'Reject', danger: true,
  });
  if (!ok) return;
  try {
    await apiPost(`/api/skills/pending/${encodeURIComponent(name)}/reject`, {});
    await skillsRefresh();
  } catch (e) {
    await alertDialog('Gagal reject: ' + e.message, 'Terjadi Kesalahan');
  }
}

async function skillsRefresh() {
  await Promise.all([loadSkills(), loadPending()]);
}
