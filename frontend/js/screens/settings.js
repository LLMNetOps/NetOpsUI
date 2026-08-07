import { apiGet, apiPost, apiPut, apiDelete } from '../api.js';
import { $, esc, pageHeader, loadingHtml, errorHtml, preHtml } from '../utils.js';
import { AGENTS } from '../config.js';

export async function screenSettings(c) {
  const tab = (id, label, active) =>
    `<button data-stab="${id}" class="pb-3 px-1 text-body-md transition-all ${active ? 'border-b-2 border-primary text-primary font-semibold' : 'text-on-surface-variant hover:text-primary'}">${label}</button>`;

  c.innerHTML = `<div class="p-container_gutter max-w-[1400px] mx-auto">
    ${pageHeader('System Settings', 'Configure global parameters for autonomous network operations.', `
      <button id="settings-discard" class="px-4 py-2 border border-primary text-primary font-medium text-body-md rounded-md hover:bg-surface-container transition-colors">Discard changes</button>
      <button id="settings-save" class="px-4 py-2 bg-secondary text-white font-medium text-body-md rounded-md hover:bg-secondary/90 transition-colors">Save changes</button>`)}
    <div class="border-b border-outline-variant mb-stack_gap_lg flex gap-8" id="settings-tabs">
      ${tab('routers', 'Routers', true)}
      ${tab('agents', 'Agents', false)}
      ${tab('environment', 'Environment', false)}
      ${tab('netbox', 'NetBox', false)}
      ${tab('memory', 'Memory', false)}
    </div>

    <!-- Routers -->
    <div class="settings-pane" id="settings-content-routers">
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="p-4 border-b border-outline-variant flex justify-between items-center bg-surface-container-low">
          <h3 class="font-title-sm text-title-sm text-primary">Managed Router Hosts</h3>
          <button id="settings-add-router" class="text-secondary font-medium text-body-sm flex items-center gap-1">
            <span class="material-symbols-outlined text-[18px]">add</span> Add Host
          </button>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead class="bg-surface-container-low">
              <tr class="text-label-caps font-label-caps text-on-surface-variant border-b border-outline-variant">
                <th class="p-3">Hostname</th>
                <th class="p-3">Management IP</th>
                <th class="p-3">SSH User</th>
                <th class="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody id="settings-router-body" class="text-body-md">
              <tr><td colspan="4" class="py-6">${loadingHtml('Memuat router...')}</td></tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Agents -->
    <div class="settings-pane hidden" id="settings-content-agents">
      <div id="settings-agents-grid" class="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        ${loadingHtml('Memuat agent...')}
      </div>
    </div>

    <!-- Environment -->
    <div class="settings-pane hidden" id="settings-content-environment">
      <div class="max-w-2xl bg-surface-container-lowest border border-outline-variant rounded-lg p-stack_gap_lg shadow-sm">
        <div class="flex items-center gap-4 mb-6">
          <div class="w-16 h-16 bg-primary/10 rounded-lg border border-outline-variant flex items-center justify-center">
            <span class="material-symbols-outlined text-primary text-3xl">dns</span>
          </div>
          <div>
            <h3 class="font-title-sm text-title-sm text-primary">Ollama Configuration</h3>
            <p class="text-body-sm text-on-surface-variant">Configure the local inference engine connection parameters.</p>
          </div>
        </div>
        <div class="space-y-6">
          <div>
            <label class="text-body-md font-medium text-primary block mb-2">Base API URL</label>
            <input id="settings-ollama-url" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 focus:ring-2 focus:ring-primary/10" type="text" value="http://localhost:11434"/>
            <p class="text-[11px] text-on-surface-variant mt-1">Disimpan di database (netops.db). Nilai awal diambil dari OLLAMA_BASE_URL di .env.</p>
          </div>
          <div>
            <label class="text-body-md font-medium text-primary block mb-2">Default Inference Model</label>
            <input id="settings-ollama-model" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 focus:ring-2 focus:ring-primary/10" type="text" value=""/>
            <p class="text-[11px] text-on-surface-variant mt-1">Dipakai sebagai fallback bila agent tidak menentukan model sendiri.</p>
          </div>
          <div class="flex items-center gap-3">
            <button id="settings-test-connection" class="px-4 py-2 bg-primary text-white font-medium text-body-sm rounded-md hover:bg-primary/90 transition-colors flex items-center gap-2">
              <span class="material-symbols-outlined text-[18px]">wifi_tethering</span> Test Connection
            </button>
            <span id="settings-test-status" class="text-body-sm text-on-surface-variant"></span>
          </div>
          <div id="settings-test-result" class="hidden p-4 rounded-lg border flex items-start gap-3"></div>
          <div class="p-4 bg-surface-container-low rounded-lg border border-outline-variant flex items-start gap-3">
            <span class="material-symbols-outlined text-on-secondary-container">info</span>
            <div class="text-body-sm text-on-surface-variant">Perubahan berlaku langsung untuk agent baru setelah <span class="font-bold">Save changes</span> — tanpa restart server.</div>
          </div>
        </div>
      </div>
    </div>

    <!-- NetBox -->
    <div class="settings-pane hidden" id="settings-content-netbox">
      <div class="max-w-2xl bg-surface-container-lowest border border-outline-variant rounded-lg p-stack_gap_lg shadow-sm">
        <div class="mb-6 border-b border-outline-variant pb-4">
          <h3 class="font-title-sm text-title-sm text-primary">Source of Truth (NetBox)</h3>
          <p class="text-body-sm text-on-surface-variant">Connect to your NetBox instance for topology discovery.</p>
        </div>
        <div class="space-y-6">
          <div>
            <label class="text-body-md font-medium text-primary block mb-1">Instance URL</label>
            <input class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2" type="text" placeholder="https://netbox.example.com"/>
          </div>
          <div>
            <label class="text-body-md font-medium text-primary block mb-1">API Token</label>
            <div class="relative">
              <input id="nb-token-input" class="w-full text-body-sm bg-surface-container-lowest border border-outline-variant rounded-md px-3 py-2 pr-10" type="password" placeholder="••••••••"/>
              <button onclick="document.getElementById('nb-token-input').type=document.getElementById('nb-token-input').type==='password'?'text':'password'" class="absolute right-3 top-1/2 -translate-y-1/2 text-on-surface-variant">
                <span class="material-symbols-outlined text-[20px]">visibility</span>
              </button>
            </div>
          </div>
          <div class="pt-4 flex items-center justify-between border-t border-outline-variant">
            <div class="flex items-center gap-2">
              <div class="w-2 h-2 rounded-full bg-outline"></div>
              <span class="text-body-sm text-on-surface-variant font-medium">Konfigurasi NetBox via .env</span>
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

  async function loadRouters() {
    const body = $('settings-router-body');
    if (body) body.innerHTML = `<tr><td colspan="4" class="py-6">${loadingHtml('Memuat router...')}</td></tr>`;
    try {
      const r = await apiGet('/api/config/routers');
      const routers = r.routers || [];
      const user = r.ssh_username || '';
      if (!routers.length) {
        if (body) body.innerHTML = `<tr><td colspan="4" class="p-4 text-center text-on-surface-variant text-body-sm">Belum ada router. Klik "Add Host".</td></tr>`;
        return;
      }
      if (body) body.innerHTML = routers.map(rt => `<tr class="even:bg-surface-container-low hover:bg-surface-container transition-colors" data-router="${esc(rt.name)}">
        <td class="p-3 border-b border-outline-variant font-medium text-primary">${esc(rt.name)}</td>
        <td class="p-3 border-b border-outline-variant font-data-mono text-data-mono">
          <input data-field="host" class="bg-transparent border-none focus:ring-0 w-full p-0" type="text" value="${esc(rt.host || '')}"/>
        </td>
        <td class="p-3 border-b border-outline-variant text-on-surface-variant">${esc(user)}</td>
        <td class="p-3 border-b border-outline-variant text-right whitespace-nowrap">
          <button data-act="test" class="px-3 py-1 bg-primary-container text-on-primary-container text-body-sm rounded hover:bg-primary hover:text-white transition-colors">Test</button>
          <button data-act="save" class="px-3 py-1 ml-1 bg-secondary text-white text-body-sm rounded hover:opacity-90 transition-colors">Save</button>
          <button data-act="delete" class="px-3 py-1 ml-1 border border-red-400 text-red-600 text-body-sm rounded hover:bg-red-50 transition-colors">Delete</button>
        </td>
      </tr>`).join('');
    } catch (e) {
      if (body) body.innerHTML = `<tr><td colspan="4" class="p-4">${errorHtml('Gagal memuat router: ' + e.message)}</td></tr>`;
    }
  }

  const routerBody = $('settings-router-body');
  if (routerBody) routerBody.onclick = async ev => {
    const btn = ev.target.closest('button[data-act]');
    if (!btn) return;
    const tr = btn.closest('tr[data-router]');
    if (!tr) return;
    const name = tr.dataset.router;
    const hostInput = tr.querySelector('input[data-field="host"]');
    const act = btn.dataset.act;
    btn.disabled = true;
    const orig = btn.textContent;
    btn.textContent = '...';
    try {
      if (act === 'test') {
        const r = await apiPost('/api/tools/reachability', { router_name: name });
        alert(`${name}:\n` + (r.result || 'no result'));
      } else if (act === 'save') {
        await apiPut('/api/config/routers/' + encodeURIComponent(name), { field: 'host', value: hostInput.value });
        alert(`Router ${name} diperbarui.`);
      } else if (act === 'delete') {
        if (confirm(`Hapus router ${name}?`)) {
          await apiDelete('/api/config/routers/' + encodeURIComponent(name));
          await loadRouters();
          return;
        }
      }
    } catch (e) {
      alert('Gagal: ' + e.message);
    } finally {
      btn.disabled = false;
      btn.textContent = orig;
    }
  };

  const addBtn = $('settings-add-router');
  if (addBtn) addBtn.onclick = async () => {
    const name = prompt('Nama router:');
    if (!name) return;
    const host = prompt('Host / IP:');
    if (!host) return;
    try {
      await apiPost('/api/config/routers', { name, host, ros_version: 7, dhcp_servers: [] });
      await loadRouters();
    } catch (e) { alert('Gagal menambah router: ' + e.message); }
  };

  const AGENT_ICONS = {};
  AGENTS.forEach(a => { AGENT_ICONS[a.name] = a.icon; });

  async function loadAgents() {
    const grid = $('settings-agents-grid');
    if (!grid) return;
    try {
      const r = await apiGet('/api/agents');
      const agents = r.agents || [];
      if (!agents.length) {
        grid.innerHTML = `<p class="text-body-sm text-on-surface-variant">Tidak ada agent terdaftar.</p>`;
        return;
      }
      grid.innerHTML = agents.map(a => `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-stack_gap_md flex flex-col shadow-sm">
        <div class="flex items-center gap-3 mb-4">
          <div class="w-10 h-10 bg-primary/10 rounded flex items-center justify-center">
            <span class="material-symbols-outlined text-primary">${AGENT_ICONS[a.name] || 'smart_toy'}</span>
          </div>
          <h4 class="font-title-sm text-title-sm text-primary">${esc(a.name)}${a.alias ? ` <span class="text-on-surface-variant font-normal text-body-sm">(${esc(a.alias)})</span>` : ''}</h4>
        </div>
        <div class="space-y-4 flex-1">
          <p class="text-body-sm text-on-surface-variant">${esc(a.description || '')}</p>
          <div><label class="text-label-caps text-on-surface-variant block mb-1">Base Model</label>
            <input class="w-full text-body-sm bg-surface-container-low border border-outline-variant rounded p-2" type="text" value="${esc(a.model || '')}" readonly/></div>
          <div class="grid grid-cols-2 gap-3">
            <div><label class="text-label-caps text-on-surface-variant block mb-1">Context Length</label>
              <input class="w-full text-body-sm bg-surface-container-low border border-outline-variant rounded p-2" type="number" value="${a.num_ctx || 0}" readonly/></div>
            <div><label class="text-label-caps text-on-surface-variant block mb-1">Timeout (s)</label>
              <input class="w-full text-body-sm bg-surface-container-low border border-outline-variant rounded p-2" type="number" value="${a.timeout || 0}" readonly/></div>
          </div>
          <div><label class="text-label-caps text-on-surface-variant block mb-1">Tools (${(a.tools || []).length})</label>
            <div class="flex flex-wrap gap-2 mt-1">${(a.tools || []).map(t => `<span class="px-2 py-1 bg-surface-container border border-outline-variant rounded text-[11px] font-medium">${esc(t)}</span>`).join('') || '<span class="text-[11px] text-on-surface-variant">—</span>'}</div>
          </div>
          ${(a.skills || []).length ? `<div><label class="text-label-caps text-on-surface-variant block mb-1">Skills</label>
            <div class="flex flex-wrap gap-2 mt-1">${a.skills.map(s => `<span class="px-2 py-1 bg-primary-container/40 border border-outline-variant rounded text-[11px] font-medium">${esc(s)}</span>`).join('')}</div></div>` : ''}
        </div>
      </div>`).join('');
    } catch (e) {
      grid.innerHTML = errorHtml('Gagal memuat agent: ' + e.message);
    }
  }

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

  async function loadEnv() {
    try {
      const cfg = await apiGet('/api/config/llm');
      const u = $('settings-ollama-url');
      const m = $('settings-ollama-model');
      if (u) u.value = cfg.base_url || '';
      if (m) m.value = cfg.model || '';
    } catch (_) {}
  }

  const testBtn = $('settings-test-connection');
  if (testBtn) testBtn.onclick = async () => {
    const urlInput = $('settings-ollama-url');
    const modelInput = $('settings-ollama-model');
    const statusEl = $('settings-test-status');
    const resultEl = $('settings-test-result');
    const base_url = urlInput ? urlInput.value.trim() : '';
    const model = modelInput ? modelInput.value.trim() : '';

    testBtn.disabled = true;
    const origHtml = testBtn.innerHTML;
    testBtn.innerHTML = `<span class="material-symbols-outlined text-[18px] animate-spin">progress_activity</span> Testing...`;
    if (statusEl) statusEl.textContent = '';
    if (resultEl) resultEl.classList.add('hidden');

    try {
      const r = await apiPost('/api/llm/test', { model: model || undefined, base_url: base_url || undefined });
      if (resultEl) {
        resultEl.classList.remove('hidden');
        if (r.ok) {
          resultEl.className = 'p-4 rounded-lg border flex items-start gap-3 bg-green-50 border-green-300 text-green-800';
          resultEl.innerHTML = `<span class="material-symbols-outlined">check_circle</span>
            <div class="text-body-sm">
              <div class="font-semibold">Koneksi berhasil</div>
              <div>Model <span class="font-data-mono">${esc(r.model)}</span> merespons dalam ${esc(String(r.latency_ms))} ms.</div>
            </div>`;
        } else {
          resultEl.className = 'p-4 rounded-lg border flex items-start gap-3 bg-red-50 border-red-300 text-red-800';
          resultEl.innerHTML = `<span class="material-symbols-outlined">error</span>
            <div class="text-body-sm">
              <div class="font-semibold">Koneksi gagal (${esc(String(r.latency_ms))} ms)</div>
              <div class="font-data-mono break-all">${esc(r.error || 'Unknown error')}</div>
            </div>`;
        }
      }
    } catch (e) {
      if (resultEl) {
        resultEl.classList.remove('hidden');
        resultEl.className = 'p-4 rounded-lg border flex items-start gap-3 bg-red-50 border-red-300 text-red-800';
        resultEl.innerHTML = `<span class="material-symbols-outlined">error</span>
          <div class="text-body-sm">
            <div class="font-semibold">Gagal menghubungi backend</div>
            <div>${esc(e.message)}</div>
          </div>`;
      }
    } finally {
      testBtn.disabled = false;
      testBtn.innerHTML = origHtml;
    }
  };

  const saveBtn = $('settings-save');
  if (saveBtn) saveBtn.onclick = async () => {
    const active = document.querySelector('.settings-pane:not(.hidden)');
    if (!active || active.id !== 'settings-content-environment') return;
    const urlInput = $('settings-ollama-url');
    const modelInput = $('settings-ollama-model');
    const orig = saveBtn.textContent;
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving...';
    try {
      await apiPut('/api/config/llm', {
        base_url: urlInput ? urlInput.value.trim() : undefined,
        model: modelInput ? modelInput.value.trim() : undefined,
      });
      await loadEnv();
    } catch (e) {
      alert('Gagal menyimpan konfigurasi LLM: ' + e.message);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = orig;
    }
  };

  const discardBtn = $('settings-discard');
  if (discardBtn) discardBtn.onclick = () => {
    const active = document.querySelector('.settings-pane:not(.hidden)');
    if (!active || active.id !== 'settings-content-environment') return;
    const resultEl = $('settings-test-result');
    if (resultEl) resultEl.classList.add('hidden');
    loadEnv();
  };

  loadRouters();
  loadAgents();
  loadMemory();
  loadEnv();
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
