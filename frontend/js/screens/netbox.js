import { apiGet, apiPost } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml } from '../utils.js';

export async function screenNetBox(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('NetBox Sync', 'Device inventory, configuration drift detection, and VLAN management.', `
      <button id="nb-sync" class="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded text-primary font-body-md hover:bg-surface-container transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">sync</span> Sync All
      </button>
      <button id="nb-drift" class="px-4 py-2 bg-secondary text-white rounded font-body-md hover:bg-secondary/90 transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">difference</span> Detect Drift
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg mb-stack_gap_lg">
      <div id="nb-stat-devices" class="col-span-6 xl:col-span-3 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
        <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">DEVICES</p>
        <span class="text-display-lg font-display-lg text-primary" id="nb-count-devices">—</span>
      </div>
      <div class="col-span-6 xl:col-span-3 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
        <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">SYNCED</p>
        <span class="text-display-lg font-display-lg text-green-700" id="nb-count-synced">—</span>
      </div>
      <div class="col-span-6 xl:col-span-3 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
        <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">DRIFT</p>
        <span class="text-display-lg font-display-lg text-amber-600" id="nb-count-drift">—</span>
      </div>
      <div class="col-span-6 xl:col-span-3 bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
        <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">LAST SYNC</p>
        <span class="text-display-lg font-display-lg text-primary text-xl" id="nb-last-sync">—</span>
      </div>
    </div>
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Device Inventory</h3>
          <input id="nb-search" type="text" placeholder="Filter..." class="px-3 py-1.5 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary w-48">
        </div>
        <div id="nb-device-list" class="overflow-y-auto max-h-[460px]">${loadingHtml('Memuat inventory...')}</div>
      </div>
      <div class="col-span-12 xl:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant">
          <h3 class="font-title-sm text-title-sm text-primary">Config Drift</h3>
        </div>
        <div id="nb-drift-panel" class="p-6 text-on-surface-variant text-body-sm">Klik "Detect Drift" untuk memeriksa perbedaan konfigurasi antara NetBox dan router aktual.</div>
      </div>
    </div>
  </div>`;

  let _allDevices = [];

  async function loadInventory() {
    const el = $('nb-device-list');
    if (!el) return;
    try {
      const r = await apiGet('/api/netbox/devices');
      _allDevices = r.devices || [];
      renderDevices(_allDevices);
      const cEl = $('nb-count-devices');
      if (cEl) cEl.textContent = _allDevices.length;
      const syncEl = $('nb-count-synced');
      if (syncEl) syncEl.textContent = _allDevices.filter(d => d.status === 'active' || d.synced).length;
    } catch (e) {
      el.innerHTML = errorHtml('Gagal memuat inventory: ' + e.message);
    }
  }

  function renderDevices(devices) {
    const el = $('nb-device-list');
    if (!el) return;
    if (!devices.length) {
      el.innerHTML = `<div class="px-6 py-8 text-center text-on-surface-variant text-body-sm">Tidak ada device.</div>`;
      return;
    }
    el.innerHTML = devices.map(d => {
      const st = (d.status || 'unknown').toLowerCase();
      const color = st === 'active' ? 'green' : st === 'planned' ? 'amber' : 'gray';
      return `<div class="flex items-center px-6 py-3 border-b border-outline-variant hover:bg-surface-container-low transition-colors group">
        <span class="material-symbols-outlined text-outline text-[18px] mr-3 shrink-0">dns</span>
        <div class="flex-1 min-w-0">
          <p class="font-data-mono text-data-mono text-primary truncate">${esc(d.name || '—')}</p>
          <p class="text-label-caps font-label-caps text-on-surface-variant truncate">${esc(d.role || d.device_role || '—')} · ${esc(d.site || '—')}</p>
        </div>
        <div class="flex items-center gap-3 ml-3 shrink-0">
          ${badge((d.status || 'unknown').toUpperCase(), color)}
          <button data-nb-toggle="${esc(d.name || '')}" class="opacity-0 group-hover:opacity-100 transition-opacity text-primary hover:text-primary/70" title="Toggle sync">
            <span class="material-symbols-outlined text-[18px]">sync</span>
          </button>
        </div>
      </div>`;
    }).join('');

    el.querySelectorAll('[data-nb-toggle]').forEach(btn => {
      btn.onclick = () => netboxToggle(btn.dataset.nbToggle);
    });
  }

  const searchEl = $('nb-search');
  if (searchEl) searchEl.oninput = () => {
    const q = searchEl.value.toLowerCase();
    renderDevices(_allDevices.filter(d =>
      (d.name || '').toLowerCase().includes(q) ||
      (d.role || d.device_role || '').toLowerCase().includes(q) ||
      (d.site || '').toLowerCase().includes(q)
    ));
  };

  const driftBtn = $('nb-drift');
  if (driftBtn) driftBtn.onclick = async () => {
    const el = $('nb-drift-panel');
    const cEl = $('nb-count-drift');
    if (el) el.innerHTML = loadingHtml('Mendeteksi drift...');
    try {
      const r = await apiPost('/api/tools/call', { tool: 'audit_config_drift', params: {} });
      const txt = (r.result || r.output || '').trim();
      const driftCount = (txt.match(/DRIFT|mismatch|berbeda/gi) || []).length;
      if (cEl) cEl.textContent = driftCount;
      if (el) el.innerHTML = txt
        ? `<pre class="font-data-mono-sm text-data-mono-sm whitespace-pre-wrap text-on-surface-variant">${esc(txt)}</pre>`
        : `<div class="text-green-700 text-body-sm">Tidak ada drift terdeteksi.</div>`;
    } catch (e) {
      if (el) el.innerHTML = errorHtml('Gagal deteksi drift: ' + e.message);
    }
  };

  const syncBtn = $('nb-sync');
  if (syncBtn) syncBtn.onclick = () => { loadInventory(); };

  loadInventory();
}

export async function netboxToggle(deviceName) {
  if (!deviceName) return;
  try {
    await apiPost('/api/tools/call', { tool: 'netbox_sync_device', params: { name: deviceName } });
  } catch (_) {}
}
