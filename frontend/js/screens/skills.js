import { apiGet, apiPost, apiPut, apiDelete } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml } from '../utils.js';

const KNOWN_DOMAINS = ['monitoring', 'routing', 'config', 'security', 'dhcp', 'netbox', 'report', 'general'];
const PAGE_SIZE = 10;

let _skillsCache = [];
let _activeFilter = 'all';
let _filteredList = [];
let _currentPage = 1;

export async function screenSkills(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Skill Library', 'Manage agent procedures. Changes are hot-reloaded — no restart required.', `
      <button id="btn-create-skill" class="px-4 py-2 bg-primary text-white rounded font-body-md hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">add</span> New Skill
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-9">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-6 py-3 border-b border-outline-variant flex flex-wrap gap-2 items-center justify-between">
            <div id="skills-filters" class="flex flex-wrap gap-2"></div>
            <input id="skills-search" type="text" placeholder="Filter skill..." class="px-3 py-1.5 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary w-48">
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
                <th class="py-3 px-4">Skill Name</th>
                <th class="py-3 px-4">Domain</th>
                <th class="py-3 px-4">Status</th>
                <th class="py-3 px-4">Approval</th>
                <th class="py-3 px-4 text-right">Actions</th>
              </tr></thead>
              <tbody id="skills-tbody" class="divide-y divide-outline-variant"><tr><td class="py-8 text-center" colspan="5">${loadingHtml()}</td></tr></tbody>
            </table>
          </div>
          <div id="skills-pagination" class="px-4 py-3 border-t border-outline-variant flex items-center justify-between gap-4 flex-wrap"></div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-3">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-5 py-4 border-b border-outline-variant">
            <h3 class="font-title-sm text-title-sm text-primary">Pending Skills</h3>
          </div>
          <div id="skills-pending" class="p-4">${loadingHtml('Memuat pending...')}</div>
        </div>
      </div>
    </div>
  </div>`;

  const createBtn = $('btn-create-skill');
  if (createBtn) createBtn.onclick = () => openSkillModal(null);

  const searchEl = $('skills-search');
  if (searchEl) searchEl.oninput = () => applyFilter();

  await Promise.all([loadSkills(), loadPending()]);
}

async function loadSkills() {
  try {
    const r = await apiGet('/api/skills');
    _skillsCache = r.skills || [];
    buildFilters();
    applyFilter();
  } catch (e) {
    const tb = $('skills-tbody');
    if (tb) tb.innerHTML = `<tr><td class="py-6 px-4 text-center" colspan="5">${errorHtml('Gagal memuat skills: ' + e.message)}</td></tr>`;
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

function buildFilters() {
  const el = $('skills-filters');
  if (!el) return;
  const domains = ['all', ...new Set(_skillsCache.map(s => s.domain).filter(Boolean))];
  el.innerHTML = domains.map(d => `<button data-filter="${esc(d)}" class="px-3 py-1 rounded-full text-label-caps font-label-caps border transition-colors ${_activeFilter === d
    ? 'bg-primary text-white border-primary'
    : 'bg-surface-container-lowest text-on-surface-variant border-outline-variant hover:bg-surface-container-low'}">${esc(d === 'all' ? 'All' : d)}</button>`).join('');
  el.querySelectorAll('[data-filter]').forEach(btn => {
    btn.onclick = () => { _activeFilter = btn.dataset.filter; _currentPage = 1; buildFilters(); applyFilter(); };
  });
}

function applyFilter() {
  const q = ($('skills-search') || {}).value?.toLowerCase() || '';
  _filteredList = _activeFilter === 'all' ? _skillsCache : _skillsCache.filter(s => s.domain === _activeFilter);
  if (q) _filteredList = _filteredList.filter(s => (s.name || '').toLowerCase().includes(q) || (s.domain || '').toLowerCase().includes(q));
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
    tb.innerHTML = `<tr><td class="py-8 px-4 text-center text-on-surface-variant text-body-sm" colspan="5">Tidak ada skill ditemukan.</td></tr>`;
    renderPagination(0, 1, 1);
    return;
  }

  const start = (_currentPage - 1) * PAGE_SIZE;
  const page = _filteredList.slice(start, start + PAGE_SIZE);

  tb.innerHTML = page.map(s => `<tr class="hover:bg-surface-container-low transition-colors group">
    <td class="py-3 px-4">
      <p class="font-data-mono text-data-mono font-medium text-primary">${esc(s.name)}</p>
      ${s.triggers?.length ? `<p class="text-label-caps font-label-caps text-on-surface-variant mt-0.5 truncate max-w-[260px]">${esc(s.triggers.slice(0,3).join(', '))}</p>` : ''}
    </td>
    <td class="py-3 px-4">${s.domain ? badge(s.domain, 'blue') : '—'}</td>
    <td class="py-3 px-4">${badge(s.enabled !== false ? 'ENABLED' : 'DISABLED', s.enabled !== false ? 'green' : 'gray')}</td>
    <td class="py-3 px-4">${s.approval_required ? badge('REQUIRED', 'amber') : badge('NONE', 'gray')}</td>
    <td class="py-3 px-4 text-right">
      <div class="flex items-center justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button data-edit-skill="${esc(s.name)}" class="p-1.5 rounded hover:bg-surface-container-low text-primary transition-colors" title="Edit skill">
          <span class="material-symbols-outlined text-[18px]">edit</span>
        </button>
        <button data-delete-skill="${esc(s.name)}" class="p-1.5 rounded hover:bg-red-50 text-red-600 transition-colors" title="Delete skill">
          <span class="material-symbols-outlined text-[18px]">delete</span>
        </button>
      </div>
    </td>
  </tr>`).join('');

  tb.querySelectorAll('[data-edit-skill]').forEach(btn => {
    btn.onclick = () => editSkillByName(btn.dataset.editSkill);
  });
  tb.querySelectorAll('[data-delete-skill]').forEach(btn => {
    btn.onclick = () => deleteSkillByName(btn.dataset.deleteSkill);
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

function openSkillModal(skill) {
  const overlay = document.createElement('div');
  overlay.id = 'skill-modal-overlay';
  // No backdrop-blur — it forces full-page GPU compositing and makes the browser slow
  overlay.className = 'fixed inset-0 z-[999] flex items-center justify-center bg-black/60';

  const isEdit = !!skill;
  const triggers = skill?.triggers?.join(', ') || '';
  const tools = skill?.tools?.join(', ') || '';

  // textarea body is set via .value after append — avoids HTML-escaping and parsing a large string
  overlay.innerHTML = `<div class="bg-white rounded-xl shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col mx-4">
    <div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
      <h2 class="font-title-md text-title-md text-primary font-bold">${isEdit ? 'Edit Skill' : 'New Skill'}</h2>
      <button id="sm-close" class="text-on-surface-variant hover:text-primary transition-colors p-1 rounded"><span class="material-symbols-outlined">close</span></button>
    </div>
    <div class="flex-1 overflow-y-auto p-6 space-y-4">
      <div id="sm-error" class="hidden"></div>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Skill Name *</label>
          <input id="sm-name" type="text" value="${esc(skill?.name || '')}" ${isEdit ? 'readonly' : ''} placeholder="e.g. network-health-check" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary ${isEdit ? 'bg-surface-container-low text-on-surface-variant' : ''}">
        </div>
        <div>
          <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Domain *</label>
          <select id="sm-domain" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
            ${KNOWN_DOMAINS.map(d => `<option value="${d}" ${skill?.domain === d ? 'selected' : ''}>${d}</option>`).join('')}
          </select>
        </div>
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Triggers (comma-separated)</label>
        <input id="sm-triggers" type="text" value="${esc(triggers)}" placeholder="e.g. network health, check router, status jaringan" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Tools (comma-separated)</label>
        <input id="sm-tools" type="text" value="${esc(tools)}" placeholder="e.g. get_interface_stats, check_reachability" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div class="flex gap-6">
        <label class="flex items-center gap-2 cursor-pointer">
          <input id="sm-enabled" type="checkbox" ${skill?.enabled !== false ? 'checked' : ''} class="w-4 h-4 accent-primary">
          <span class="text-body-sm text-on-surface-variant">Enabled</span>
        </label>
        <label class="flex items-center gap-2 cursor-pointer">
          <input id="sm-approval" type="checkbox" ${skill?.approval_required ? 'checked' : ''} class="w-4 h-4 accent-amber-500">
          <span class="text-body-sm text-on-surface-variant">Requires Approval</span>
        </label>
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Skill Body (Bahasa Indonesia)</label>
        <textarea id="sm-body" rows="12" placeholder="Tulis prosedur skill di sini dalam Bahasa Indonesia..." class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"></textarea>
      </div>
    </div>
    <div class="flex justify-end gap-3 px-6 py-4 border-t border-outline-variant">
      <button id="sm-cancel" class="px-4 py-2 border border-outline-variant rounded text-body-sm text-on-surface-variant hover:bg-surface-container-low transition-colors">Batal</button>
      <button id="sm-save" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Skill'}
      </button>
    </div>
  </div>`;

  document.body.appendChild(overlay);

  // Set textarea value directly — bypasses HTML parsing of potentially large text
  document.getElementById('sm-body').value = skill?.body || '';

  const closeModal = () => { const el = document.getElementById('skill-modal-overlay'); if (el) el.remove(); };
  document.getElementById('sm-close').onclick = closeModal;
  document.getElementById('sm-cancel').onclick = closeModal;
  overlay.onclick = e => { if (e.target === overlay) closeModal(); };

  document.getElementById('sm-save').onclick = async () => {
    const errEl = document.getElementById('sm-error');
    const saveBtn = document.getElementById('sm-save');
    const name = (document.getElementById('sm-name').value || '').trim();
    const domain = document.getElementById('sm-domain').value;
    const body = (document.getElementById('sm-body').value || '').trim();
    const triggersRaw = (document.getElementById('sm-triggers').value || '').trim();
    const toolsRaw = (document.getElementById('sm-tools').value || '').trim();
    const enabled = document.getElementById('sm-enabled').checked;
    const approval_required = document.getElementById('sm-approval').checked;

    if (!name) { errEl.innerHTML = errorHtml('Nama skill wajib diisi.'); errEl.classList.remove('hidden'); return; }
    if (!body) { errEl.innerHTML = errorHtml('Body skill wajib diisi.'); errEl.classList.remove('hidden'); return; }

    const payload = {
      name, domain, body, enabled, approval_required,
      triggers: triggersRaw ? triggersRaw.split(',').map(t => t.trim()).filter(Boolean) : [],
      tools: toolsRaw ? toolsRaw.split(',').map(t => t.trim()).filter(Boolean) : [],
    };

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Menyimpan...';

    try {
      if (isEdit) {
        await apiPut(`/api/skills/${encodeURIComponent(skill.name)}`, payload);
      } else {
        await apiPost('/api/skills', payload);
      }
      closeModal();
      await skillsRefresh();
    } catch (e) {
      errEl.innerHTML = errorHtml(e.message || 'Gagal menyimpan skill.');
      errEl.classList.remove('hidden');
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Skill'}`;
    }
  };
}

async function editSkillByName(name) {
  try {
    const skill = await apiGet(`/api/skills/${encodeURIComponent(name)}`);
    openSkillModal(skill);
  } catch (e) {
    alert('Gagal memuat skill: ' + e.message);
  }
}

async function deleteSkillByName(name) {
  if (!confirm(`Hapus skill "${name}"? Tindakan ini tidak bisa dibatalkan.`)) return;
  try {
    await apiDelete(`/api/skills/${encodeURIComponent(name)}`);
    await skillsRefresh();
  } catch (e) {
    alert('Gagal menghapus: ' + e.message);
  }
}

async function approvePendingSkill(name) {
  if (!confirm(`Approve skill "${name}"?`)) return;
  try {
    await apiPost(`/api/skills/pending/${encodeURIComponent(name)}/approve`, {});
    await skillsRefresh();
  } catch (e) {
    alert('Gagal approve: ' + e.message);
  }
}

async function rejectPendingSkill(name) {
  if (!confirm(`Reject dan hapus skill pending "${name}"?`)) return;
  try {
    await apiPost(`/api/skills/pending/${encodeURIComponent(name)}/reject`, {});
    await skillsRefresh();
  } catch (e) {
    alert('Gagal reject: ' + e.message);
  }
}

async function skillsRefresh() {
  await Promise.all([loadSkills(), loadPending()]);
}
