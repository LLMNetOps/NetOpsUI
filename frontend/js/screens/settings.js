import { apiGet, apiPost, apiPut, apiDelete } from '../api.js';
import { $, esc, pageHeader, loadingHtml, errorHtml, preHtml, confirmDialog, alertDialog } from '../utils.js';

export async function screenSettings(c) {
  const tab = (id, label, active) =>
    `<button data-stab="${id}" class="pb-3 px-1 text-body-md transition-all ${active ? 'border-b-2 border-primary text-primary font-semibold' : 'text-on-surface-variant hover:text-primary'}">${label}</button>`;

  c.innerHTML = `<div class="p-container_gutter max-w-[1400px] mx-auto">
    ${pageHeader('System Settings', 'Configure global parameters for autonomous network operations.')}
    <div class="border-b border-outline-variant mb-stack_gap_lg flex gap-8" id="settings-tabs">
      ${tab('environment', 'LLM Setting', true)}
      ${tab('memory', 'Memory', false)}
    </div>

    <!-- LLM Setting -->
    <div class="settings-pane" id="settings-content-environment">
      <div class="max-w-2xl space-y-6">

        <!-- Saved profiles -->
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden shadow-sm">
          <div class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
            <div>
              <h3 class="font-title-sm text-title-sm text-primary">LLM Connection Profiles</h3>
              <p class="text-[11px] text-on-surface-variant">Simpan beberapa koneksi LLM dan aktifkan dengan satu klik.</p>
            </div>
            <button id="settings-add-profile" class="text-secondary font-medium text-body-sm flex items-center gap-1">
              <span class="material-symbols-outlined text-[18px]">add</span> Add Profile
            </button>
          </div>
          <div id="settings-profiles-list" class="divide-y divide-outline-variant text-body-md">
            <div class="p-4 text-center text-on-surface-variant text-body-sm">Memuat...</div>
          </div>
          <!-- inline add/edit form -->
          <div id="settings-profile-form" class="hidden border-t border-outline-variant p-4 bg-surface-container-low">
            <p id="settings-profile-form-title" class="font-medium text-primary text-body-md mb-3">Tambah Profile</p>
            <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-3">
              <div>
                <label class="text-[11px] text-on-surface-variant block mb-1">Nama Profile</label>
                <input id="pf-name" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2" type="text" placeholder="Contoh: Ollama Lokal"/>
              </div>
              <div>
                <label class="text-[11px] text-on-surface-variant block mb-1">Base URL</label>
                <input id="pf-url" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2" type="text" placeholder="http://localhost:11434"/>
              </div>
              <div>
                <label class="text-[11px] text-on-surface-variant block mb-1">Model</label>
                <select id="pf-model" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2">
                  <option value="">Klik Check Connection untuk melihat model tersedia</option>
                </select>
              </div>
              <div>
                <label class="text-[11px] text-on-surface-variant block mb-1">API Key <span class="text-on-surface-variant font-normal">(opsional)</span></label>
                <input id="pf-apikey" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 font-data-mono" type="password" placeholder="Kosongkan jika tidak ada" autocomplete="off"/>
              </div>
            </div>
            <div class="flex items-center gap-3 mb-3">
              <button id="pf-check-connection" type="button" class="px-3 py-1.5 border border-outline-variant text-primary font-medium text-body-sm rounded-md hover:bg-surface-container transition-colors flex items-center gap-1">
                <span class="material-symbols-outlined text-[16px]">wifi_tethering</span> Check Connection
              </button>
              <span id="pf-check-status" class="text-body-sm text-on-surface-variant"></span>
            </div>
            <div class="flex gap-2">
              <button id="pf-save" class="px-4 py-2 bg-secondary text-white font-medium text-body-sm rounded-md hover:bg-secondary/90 transition-colors">Simpan</button>
              <button id="pf-cancel" class="px-4 py-2 border border-outline-variant text-on-surface-variant font-medium text-body-sm rounded-md hover:bg-surface-container transition-colors">Batal</button>
              <span id="pf-error" class="text-red-600 text-body-sm self-center"></span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Memory -->
    <div class="settings-pane hidden" id="settings-content-memory">
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden shadow-sm">
        <div class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
          <div>
            <h3 class="font-title-sm text-title-sm text-primary">Router Context Facts</h3>
            <p class="text-[11px] text-on-surface-variant">Long-term semantic memory for network topology.</p>
          </div>
          <button id="settings-memory-refresh" class="px-3 py-1 bg-primary text-white text-body-sm font-medium rounded hover:bg-primary/90 transition-colors flex items-center gap-1">
            <span class="material-symbols-outlined text-[18px]">refresh</span> Refresh
          </button>
        </div>
        <div id="settings-memory-body" class="p-4">${loadingHtml('Memuat memori...')}</div>
      </div>
    </div>
  </div>`;

  const tabsEl = $('settings-tabs');
  if (tabsEl) tabsEl.onclick = e => {
    const btn = e.target.closest('[data-stab]');
    if (btn) settingsTab(btn.dataset.stab);
  };

  async function loadMemory() {
    const body = $('settings-memory-body');
    if (body) body.innerHTML = loadingHtml('Memuat memori...');
    try {
      const r = await apiGet('/api/memory');
      if (body) body.innerHTML = `<div class="max-h-[500px] overflow-auto">${preHtml(r.result || 'Belum ada fakta tersimpan.')}</div>`;
    } catch (e) {
      if (body) body.innerHTML = errorHtml('Gagal memuat memori: ' + e.message);
    }
  }

  const memBtn = $('settings-memory-refresh');
  if (memBtn) memBtn.onclick = loadMemory;

  // ── LLM Profiles ─────────────────────────────────────────────────────────

  // editingProfileId = null means "add", number means "edit"
  let editingProfileId = null;

  function showProfileForm(profile = null) {
    editingProfileId = profile ? profile.id : null;
    const form = $('settings-profile-form');
    const title = $('settings-profile-form-title');
    if (!form) return;
    $('pf-name').value = profile ? profile.name : '';
    $('pf-url').value = profile ? profile.base_url : '';
    setModelSelect($('pf-model'), [], profile ? profile.model : '');
    $('pf-apikey').value = '';
    $('pf-apikey').placeholder = profile ? (profile.api_key_set ? 'Kosongkan untuk tidak mengubah' : 'Kosongkan jika tidak ada') : 'Kosongkan jika tidak ada';
    $('pf-error').textContent = '';
    $('pf-check-status').textContent = '';
    if (title) title.textContent = profile ? 'Edit Profile' : 'Tambah Profile';
    form.classList.remove('hidden');
    $('pf-name').focus();
    if (profile) autoPopulateProfileModels(profile.id, profile.model);
  }

  function hideProfileForm() {
    const form = $('settings-profile-form');
    if (form) form.classList.add('hidden');
    editingProfileId = null;
  }

  async function loadProfiles() {
    const list = $('settings-profiles-list');
    if (!list) return;
    try {
      const r = await apiGet('/api/config/llm/profiles');
      const profiles = r.profiles || [];
      if (!profiles.length) {
        list.innerHTML = `<div class="p-4 text-center text-on-surface-variant text-body-sm">Belum ada profile. Klik "Add Profile".</div>`;
        return;
      }
      list.innerHTML = profiles.map(p => `
        <div class="flex items-center gap-3 p-3 hover:bg-surface-container transition-colors" data-profile-id="${p.id}" data-profile='${JSON.stringify({id:p.id,name:p.name,base_url:p.base_url,model:p.model,api_key_set:p.api_key_set})}'>
          <div class="w-2 h-2 rounded-full flex-shrink-0 ${p.is_active ? 'bg-green-500' : 'bg-outline'}"></div>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-primary truncate">${esc(p.name)}${p.is_active ? ' <span class="text-[10px] font-semibold uppercase text-green-700 bg-green-100 px-1.5 py-0.5 rounded-full ml-1">Active</span>' : ''}</div>
            <div class="text-[11px] text-on-surface-variant font-data-mono truncate">${esc(p.base_url)}&nbsp;·&nbsp;${esc(p.model)}</div>
          </div>
          <div class="flex gap-1 flex-shrink-0">
            ${p.is_active
              ? `<button data-pact="deactivate" class="px-2 py-1 border border-outline-variant text-on-surface-variant text-body-sm rounded hover:bg-surface-container-low transition-colors">Deactivate</button>`
              : `<button data-pact="activate" class="px-2 py-1 bg-primary text-white text-body-sm rounded hover:bg-primary/90 transition-colors">Activate</button>`}
            <button data-pact="edit" class="px-2 py-1 bg-primary-container text-on-primary-container text-body-sm rounded hover:opacity-90 transition-colors">Edit</button>
            <button data-pact="delete" class="px-2 py-1 border border-red-400 text-red-600 text-body-sm rounded hover:bg-red-50 transition-colors">Del</button>
          </div>
        </div>`).join('');
    } catch (e) {
      list.innerHTML = `<div class="p-4 text-red-600 text-body-sm">Gagal memuat profiles: ${esc(e.message)}</div>`;
    }
  }

  const profilesList = $('settings-profiles-list');
  if (profilesList) profilesList.onclick = async ev => {
    const btn = ev.target.closest('button[data-pact]');
    if (!btn) return;
    const row = btn.closest('[data-profile-id]');
    if (!row) return;
    const id = parseInt(row.dataset.profileId, 10);
    const act = btn.dataset.pact;
    if (act === 'edit') {
      const profile = JSON.parse(row.dataset.profile);
      showProfileForm(profile);
      return;
    }
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = '...';
    try {
      if (act === 'activate') {
        await apiPost(`/api/config/llm/profiles/${id}/activate`, {});
        await loadProfiles();
      } else if (act === 'deactivate') {
        await apiPost(`/api/config/llm/profiles/${id}/deactivate`, {});
        await loadProfiles();
      } else if (act === 'delete') {
        const ok = await confirmDialog({
          title: 'Hapus profile?', message: 'Profile LLM ini akan dihapus permanen.',
          confirmLabel: 'Hapus', danger: true,
        });
        if (ok) {
          await apiDelete(`/api/config/llm/profiles/${id}`);
          await loadProfiles();
        }
      }
    } catch (e) {
      await alertDialog('Gagal: ' + e.message, 'Terjadi Kesalahan');
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  };

  const addProfileBtn = $('settings-add-profile');
  if (addProfileBtn) addProfileBtn.onclick = () => showProfileForm(null);

  const pfSaveBtn = $('pf-save');
  if (pfSaveBtn) pfSaveBtn.onclick = async () => {
    const name = $('pf-name').value.trim();
    const base_url = $('pf-url').value.trim();
    const model = $('pf-model').value.trim();
    const api_key = $('pf-apikey').value.trim() || undefined;
    const errEl = $('pf-error');
    if (!name || !base_url || !model) {
      if (errEl) errEl.textContent = 'Nama, Base URL, dan Model wajib diisi.';
      return;
    }
    pfSaveBtn.disabled = true;
    pfSaveBtn.textContent = 'Menyimpan...';
    try {
      if (editingProfileId !== null) {
        await apiPut(`/api/config/llm/profiles/${editingProfileId}`, { name, base_url, model, api_key });
      } else {
        await apiPost('/api/config/llm/profiles', { name, base_url, model, api_key: api_key || '' });
      }
      hideProfileForm();
      await loadProfiles();
    } catch (e) {
      if (errEl) errEl.textContent = 'Gagal: ' + e.message;
    } finally {
      pfSaveBtn.disabled = false;
      pfSaveBtn.textContent = 'Simpan';
    }
  };

  const pfCancelBtn = $('pf-cancel');
  if (pfCancelBtn) pfCancelBtn.onclick = hideProfileForm;

  const pfCheckBtn = $('pf-check-connection');
  if (pfCheckBtn) pfCheckBtn.onclick = async () => {
    const urlInput = $('pf-url');
    const modelInput = $('pf-model');
    const apiKeyInput = $('pf-apikey');
    const statusEl = $('pf-check-status');
    const base_url = urlInput ? urlInput.value.trim() : '';
    const api_key = apiKeyInput ? apiKeyInput.value.trim() : '';
    const currentModel = modelInput ? modelInput.value.trim() : '';

    pfCheckBtn.disabled = true;
    const origHtml = pfCheckBtn.innerHTML;
    pfCheckBtn.innerHTML = `<span class="material-symbols-outlined text-[16px] animate-spin">progress_activity</span> Checking...`;
    if (statusEl) { statusEl.textContent = ''; statusEl.className = 'text-body-sm text-on-surface-variant'; }

    try {
      const r = await apiPost('/api/llm/models', { base_url: base_url || undefined, api_key: api_key || undefined });
      if (r.ok) {
        setModelSelect(modelInput, r.models, currentModel || r.models[0] || '');
        if (statusEl) {
          statusEl.className = 'text-body-sm text-green-700';
          statusEl.textContent = `${r.models.length} model ditemukan (${r.latency_ms} ms). Pilih dari dropdown Model.`;
        }
      } else if (statusEl) {
        statusEl.className = 'text-body-sm text-red-600';
        statusEl.textContent = `Koneksi gagal: ${r.error || 'Unknown error'}`;
      }
    } catch (e) {
      if (statusEl) {
        statusEl.className = 'text-body-sm text-red-600';
        statusEl.textContent = 'Gagal menghubungi backend: ' + e.message;
      }
    } finally {
      pfCheckBtn.disabled = false;
      pfCheckBtn.innerHTML = origHtml;
    }
  };

  // ── end LLM Profiles ──────────────────────────────────────────────────────

  function setModelSelect(selectEl, models, currentValue) {
    if (!selectEl) return;
    const values = [...models];
    if (currentValue && !values.includes(currentValue)) values.unshift(currentValue);
    selectEl.innerHTML = values.length
      ? values.map(m => `<option value="${esc(m)}">${esc(m)}</option>`).join('')
      : `<option value="">Klik Check Connection untuk melihat model tersedia</option>`;
    if (currentValue) selectEl.value = currentValue;
  }

  // Profile sudah tersimpan → langsung fetch daftar model pakai kredensial
  // tersimpan di server, operator tidak perlu klik Check Connection manual.
  async function autoPopulateProfileModels(profileId, currentModel) {
    const statusEl = $('pf-check-status');
    if (statusEl) { statusEl.className = 'text-body-sm text-on-surface-variant'; statusEl.textContent = 'Memuat model tersedia...'; }
    try {
      const r = await apiPost(`/api/config/llm/profiles/${profileId}/models`, {});
      if (r.ok) {
        setModelSelect($('pf-model'), r.models, currentModel || r.models[0] || '');
        if (statusEl) {
          statusEl.className = 'text-body-sm text-green-700';
          statusEl.textContent = `${r.models.length} model ditemukan (${r.latency_ms} ms).`;
        }
      } else if (statusEl) {
        statusEl.className = 'text-body-sm text-red-600';
        statusEl.textContent = `Koneksi gagal: ${r.error || 'Unknown error'}`;
      }
    } catch (e) {
      if (statusEl) { statusEl.className = 'text-body-sm text-red-600'; statusEl.textContent = 'Gagal menghubungi backend: ' + e.message; }
    }
  }

  loadMemory();
  loadProfiles();
}

export function settingsTab(tabId) {
  document.querySelectorAll('.settings-pane').forEach(p => p.classList.add('hidden'));
  document.querySelectorAll('[data-stab]').forEach(t => {
    t.classList.remove('border-b-2', 'border-primary', 'text-primary', 'font-semibold');
    t.classList.add('text-on-surface-variant');
  });
  const pane = document.getElementById('settings-content-' + tabId);
  if (pane) pane.classList.remove('hidden');
  const btn = document.querySelector(`[data-stab="${tabId}"]`);
  if (btn) {
    btn.classList.add('border-b-2', 'border-primary', 'text-primary', 'font-semibold');
    btn.classList.remove('text-on-surface-variant');
  }
}
