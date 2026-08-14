import { apiGet, apiPut, apiPost } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml, alertDialog, confirmDialog } from '../utils.js';
import { mountTagInput } from '../tag-input.js';

let _agentsCache = [];
let _selectedName = null;
let _detailCache = {}; // name -> full detail payload, invalidated on save/restore
let _toolNamesCache = null;
let _skillNamesCache = null;
let _llmProfilesCache = null;
let _resizeHandler = null;

// The panel's sticky top can't be a hardcoded pixel guess — pageHeader's subtitle
// wraps to a different number of lines depending on viewport width, which shifts
// where the panel actually starts. Measure its real static (unstuck) position and
// derive max-height from that so the bottom always lands just above the viewport
// edge instead of running off the bottom.
function fitDetailPanel() {
  const panel = $('agent-detail-panel');
  if (!panel) return;
  const top = Math.round(panel.getBoundingClientRect().top);
  panel.style.top = `${top}px`;
  panel.style.maxHeight = `calc(100vh - ${top}px - 24px)`;
}

async function getToolNames() {
  if (!_toolNamesCache) {
    const r = await apiGet('/api/tool-names');
    _toolNamesCache = r.tools || [];
  }
  return _toolNamesCache;
}

async function getSkillNames() {
  if (!_skillNamesCache) {
    const r = await apiGet('/api/skills');
    _skillNamesCache = (r.skills || []).map(s => s.name);
  }
  return _skillNamesCache;
}

// Active LLM connection profiles, configured in #settings. Multiple profiles can be
// active at once so different agents can each be wired to a different backend.
async function getActiveLlmProfiles() {
  if (!_llmProfilesCache) {
    const r = await apiGet('/api/config/llm/profiles');
    _llmProfilesCache = (r.profiles || []).filter(p => p.is_active);
  }
  return _llmProfilesCache;
}

export async function screenAgents(c, param) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Agents', 'Kelola konfigurasi specialist agent. Pilih agent di kiri untuk edit. Perubahan disimpan ke database dan baru berlaku setelah server di-restart.')}
    <div class="grid grid-cols-12 gap-stack_gap_lg items-start">
      <div class="col-span-12 xl:col-span-5">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
                <th class="py-3 px-4">Agent</th>
                <th class="py-3 px-4">Model</th>
                <th class="py-3 px-4">Status</th>
              </tr></thead>
              <tbody id="agents-tbody" class="divide-y divide-outline-variant"><tr><td class="py-8 text-center" colspan="3">${loadingHtml()}</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-7">
        <div id="agent-detail-panel" class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden flex flex-col sticky">
          ${emptyPanelHtml()}
        </div>
      </div>
    </div>
  </div>`;

  fitDetailPanel();
  if (_resizeHandler) window.removeEventListener('resize', _resizeHandler);
  _resizeHandler = fitDetailPanel;
  window.addEventListener('resize', _resizeHandler);

  _selectedName = null;
  await loadAgents();

  if (param && _agentsCache.some(a => a.name === param)) {
    await selectAgent(param);
  }
}

function emptyPanelHtml() {
  return `<div class="p-12 flex flex-col items-center justify-center text-center">
    <span class="material-symbols-outlined text-5xl text-outline-variant mb-3">smart_toy</span>
    <p class="text-body-sm text-on-surface-variant">Pilih agent di tabel untuk melihat dan mengedit konfigurasinya.</p>
  </div>`;
}

async function loadAgents() {
  const tb = $('agents-tbody');
  try {
    const r = await apiGet('/api/agents');
    _agentsCache = r.agents || [];
    renderRows();
    // If a row was selected (e.g. right after save/restore), refresh its panel in place
    if (_selectedName && _agentsCache.some(a => a.name === _selectedName)) {
      await renderDetailPanel(_selectedName);
    }
  } catch (e) {
    if (tb) tb.innerHTML = `<tr><td class="py-6 px-4 text-center" colspan="3">${errorHtml('Gagal memuat agents: ' + e.message)}</td></tr>`;
  }
}

function renderRows() {
  const tb = $('agents-tbody');
  if (!tb) return;

  if (!_agentsCache.length) {
    tb.innerHTML = `<tr><td class="py-8 px-4 text-center text-on-surface-variant text-body-sm" colspan="3">Tidak ada agent ditemukan.</td></tr>`;
    return;
  }

  tb.innerHTML = _agentsCache.map(a => summaryRowHtml(a)).join('');

  tb.querySelectorAll('[data-row-select]').forEach(row => {
    row.onclick = () => selectAgent(row.dataset.rowSelect);
  });
}

function summaryRowHtml(a) {
  const isSelected = _selectedName === a.name;
  return `<tr data-row-select="${esc(a.name)}" class="cursor-pointer transition-colors ${isSelected ? 'bg-primary/5 border-l-[3px] border-l-primary' : 'hover:bg-surface-container-low border-l-[3px] border-l-transparent'}">
    <td class="py-3 px-4">
      <p class="font-data-mono text-data-mono font-medium text-primary">${esc(a.name)}</p>
      <p class="text-label-caps font-label-caps text-on-surface-variant mt-0.5">${esc(a.alias || '')}</p>
    </td>
    <td class="py-3 px-4 text-body-sm font-data-mono-sm">${esc(a.model || '')}</td>
    <td class="py-3 px-4">
      ${badge(a.enabled !== false ? 'ENABLED' : 'DISABLED', a.enabled !== false ? 'green' : 'gray')}
      ${a.has_default ? badge('MODIFIED', 'amber') : ''}
    </td>
  </tr>`;
}

async function selectAgent(name) {
  _selectedName = name;
  renderRows();
  await renderDetailPanel(name);
}

async function renderDetailPanel(name) {
  const panel = $('agent-detail-panel');
  if (!panel) return;
  panel.innerHTML = loadingHtml('Memuat detail agent...');

  try {
    const agent = _detailCache[name] || await apiGet(`/api/agents/${encodeURIComponent(name)}`);
    _detailCache[name] = agent;
    if (_selectedName !== name) return; // user already clicked another row while this was loading
    panel.innerHTML = editFormHtml(agent);
    await wireEditForm(agent);
  } catch (e) {
    if (_selectedName !== name) return;
    panel.innerHTML = errorHtml('Gagal memuat agent: ' + e.message);
  }
}

function editFormHtml(agent) {
  return `<div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant flex-shrink-0">
    <h3 class="font-title-sm text-title-sm text-primary font-bold">${esc(agent.name)}${agent.alias ? ` <span class="text-on-surface-variant font-normal text-body-sm">(${esc(agent.alias)})</span>` : ''}</h3>
    <button id="af-close" class="text-on-surface-variant hover:text-primary transition-colors p-1 rounded" title="Tutup"><span class="material-symbols-outlined text-[20px]">close</span></button>
  </div>
  <div class="p-6 space-y-4 flex-1 min-h-0 overflow-y-auto">
    <div id="af-error" class="hidden"></div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Description (dipakai supervisor untuk routing)</label>
      <input id="af-description" type="text" value="${esc(agent.description || '')}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
    </div>
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Model</label>
        <select id="af-model" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
          <option value="${esc(agent.model || '')}">${esc(agent.model || '(pilih model)')}</option>
        </select>
        <p id="af-model-hint" class="text-[11px] text-on-surface-variant mt-1">Daftar model dimuat dari Ollama Host di sebelah kanan.</p>
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Ollama Host (opsional)</label>
        <select id="af-ollama-host" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
          <option value="">Memuat profile...</option>
        </select>
        <p class="text-[11px] text-on-surface-variant mt-1">Dari LLM Connection Profiles yang aktif di Settings. Kosongkan untuk pakai default global.</p>
      </div>
    </div>
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">num_ctx</label>
        <input id="af-num-ctx" type="number" value="${agent.num_ctx ?? 8192}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">num_predict</label>
        <input id="af-num-predict" type="number" value="${agent.num_predict ?? 2048}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
    </div>
    <div class="grid grid-cols-3 gap-4">
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">context_window</label>
        <input id="af-context-window" type="number" value="${agent.context_window ?? 10}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">timeout (detik)</label>
        <input id="af-timeout" type="number" value="${agent.timeout ?? 300}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">max_iters</label>
        <input id="af-max-iters" type="number" value="${agent.max_iters ?? 20}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Tools</label>
      <div id="af-tools"></div>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Skills</label>
      <div id="af-skills"></div>
    </div>
    <div class="flex gap-6">
      <label class="flex items-center gap-2 cursor-pointer">
        <input id="af-enabled" type="checkbox" ${agent.enabled !== false ? 'checked' : ''} class="w-4 h-4 accent-primary">
        <span class="text-body-sm text-on-surface-variant">Enabled</span>
      </label>
      <label class="flex items-center gap-2 cursor-pointer">
        <input id="af-reasoning" type="checkbox" ${agent.reasoning ? 'checked' : ''} class="w-4 h-4 accent-primary">
        <span class="text-body-sm text-on-surface-variant">Reasoning mode</span>
      </label>
    </div>
    <div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">System Prompt (Bahasa Indonesia)</label>
      <textarea id="af-body" rows="14" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary resize-y"></textarea>
    </div>
  </div>
  <div class="flex justify-between items-center px-6 py-4 border-t border-outline-variant flex-shrink-0">
    ${agent.has_default
      ? `<button id="af-restore" class="px-4 py-2 border border-amber-200 text-amber-700 rounded text-body-sm hover:bg-amber-50 transition-colors flex items-center gap-2">
           <span class="material-symbols-outlined text-sm">restart_alt</span>Restore Default
         </button>`
      : '<span></span>'}
    <div class="flex items-center gap-3">
      <span class="text-label-caps font-label-caps text-on-surface-variant hidden md:inline">Perlu restart server agar diterapkan</span>
      <button id="af-cancel" class="px-4 py-2 border border-outline-variant rounded text-body-sm text-on-surface-variant hover:bg-surface-container-low transition-colors">Reset</button>
      <button id="af-save" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">save</span>Simpan Perubahan
      </button>
    </div>
  </div>`;
}

async function wireEditForm(agent) {
  // Set textarea value directly — bypasses HTML parsing of potentially large text
  $('af-body').value = agent.body || '';

  const [toolNames, skillNames, llmProfiles] = await Promise.all([getToolNames(), getSkillNames(), getActiveLlmProfiles()]);
  const toolsWidget = mountTagInput($('af-tools'), { initial: agent.tools || [], options: toolNames, placeholder: 'Cari tool...' });
  const skillsWidget = mountTagInput($('af-skills'), { initial: agent.skills || [], options: skillNames, placeholder: 'Cari skill...' });

  const hostSelect = $('af-ollama-host');
  const current = agent.ollama_host || '';
  const knownUrls = new Set(llmProfiles.map(p => p.base_url));
  const customOpt = current && !knownUrls.has(current)
    ? `<option value="${esc(current)}" selected>${esc(current)} (custom)</option>` : '';
  hostSelect.innerHTML = `<option value="">(pakai default global)</option>${customOpt}`
    + llmProfiles.map(p => `<option value="${esc(p.base_url)}" ${p.base_url === current ? 'selected' : ''}>${esc(p.name)} — ${esc(p.base_url)}</option>`).join('');

  // Model dropdown depends on which host is selected — fetch the model list for
  // that connection so the operator picks from what's actually available instead
  // of typing a name that might not exist (typos silently break the agent).
  function setModelOptions(models, currentValue) {
    const sel = $('af-model');
    if (!sel) return;
    const values = [...models];
    if (currentValue && !values.includes(currentValue)) values.unshift(currentValue);
    sel.innerHTML = values.length
      ? values.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')
      : `<option value="${esc(currentValue)}">${esc(currentValue || '(tidak ada model ditemukan)')}</option>`;
    if (currentValue) sel.value = currentValue;
  }

  async function refreshModelOptions() {
    const hint = $('af-model-hint');
    const currentModel = ($('af-model').value || '').trim() || agent.model || '';
    const hostUrl = hostSelect.value;
    const matchedProfile = llmProfiles.find(p => p.base_url === hostUrl);
    if (hint) hint.textContent = 'Memuat model tersedia...';
    try {
      const r = matchedProfile
        ? await apiPost(`/api/config/llm/profiles/${matchedProfile.id}/models`, {})
        : await apiPost('/api/llm/models', hostUrl ? { base_url: hostUrl } : {});
      if (r.ok) {
        setModelOptions(r.models, currentModel);
        if (hint) hint.textContent = `${r.models.length} model ditemukan dari ${matchedProfile ? matchedProfile.name : (hostUrl || 'default global')} (${r.latency_ms} ms).`;
      } else if (hint) {
        hint.textContent = `Gagal memuat model dari host ini: ${r.error || 'Unknown error'}. Model saat ini (${esc(currentModel)}) tetap dipakai.`;
      }
    } catch (e) {
      if (hint) hint.textContent = 'Gagal menghubungi backend: ' + e.message;
    }
  }

  hostSelect.onchange = refreshModelOptions;
  refreshModelOptions();

  $('af-close').onclick = () => {
    _selectedName = null;
    renderRows();
    $('agent-detail-panel').innerHTML = emptyPanelHtml();
  };

  // Reset just re-renders the panel from the last-loaded (cached) agent data, discarding edits
  $('af-cancel').onclick = async () => {
    $('agent-detail-panel').innerHTML = editFormHtml(agent);
    await wireEditForm(agent);
  };

  const restoreBtn = $('af-restore');
  if (restoreBtn) restoreBtn.onclick = async () => {
    const ok = await confirmDialog({
      title: 'Restore ke default?',
      message: `Semua perubahan pada agent "${agent.name}" akan dikembalikan ke versi default dari repo. Tindakan ini tidak bisa dibatalkan.`,
      confirmLabel: 'Restore', danger: true,
    });
    if (!ok) return;
    try {
      await apiPost(`/api/agents/${encodeURIComponent(agent.name)}/restore`, {});
      delete _detailCache[agent.name];
      await loadAgents();
    } catch (e) {
      await alertDialog('Gagal restore: ' + e.message, 'Terjadi Kesalahan');
    }
  };

  $('af-save').onclick = async () => {
    const errEl = $('af-error');
    const saveBtn = $('af-save');
    const description = ($('af-description').value || '').trim();
    const model = ($('af-model').value || '').trim();
    const body = ($('af-body').value || '').trim();

    if (!description) { errEl.innerHTML = errorHtml('Description wajib diisi.'); errEl.classList.remove('hidden'); return; }
    if (!model) { errEl.innerHTML = errorHtml('Model wajib diisi.'); errEl.classList.remove('hidden'); return; }
    if (!body) { errEl.innerHTML = errorHtml('System prompt wajib diisi.'); errEl.classList.remove('hidden'); return; }

    const payload = {
      description, model, body,
      tools: toolsWidget.getValues(),
      skills: skillsWidget.getValues(),
      num_ctx: parseInt($('af-num-ctx').value) || 8192,
      num_predict: parseInt($('af-num-predict').value) || 2048,
      context_window: parseInt($('af-context-window').value) || 10,
      timeout: parseInt($('af-timeout').value) || 300,
      max_iters: parseInt($('af-max-iters').value) || 20,
      ollama_host: ($('af-ollama-host').value || '').trim(),
      reasoning: $('af-reasoning').checked,
      enabled: $('af-enabled').checked,
    };

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Menyimpan...';

    try {
      await apiPut(`/api/agents/${encodeURIComponent(agent.name)}`, payload);
      delete _detailCache[agent.name];
      await loadAgents();
    } catch (e) {
      errEl.innerHTML = errorHtml(e.message || 'Gagal menyimpan agent.');
      errEl.classList.remove('hidden');
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<span class="material-symbols-outlined text-sm">save</span>Simpan Perubahan';
    }
  };
}
