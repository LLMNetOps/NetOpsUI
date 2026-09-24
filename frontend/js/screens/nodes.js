import { esc, pageHeader, $ } from '../utils.js';
import { activeBackend } from '../backends/index.js';

const FIELDS = [
  { id: 'name',         label: 'Nama',         placeholder: 'core-gw-01', required: true },
  { id: 'mgmt_ip',      label: 'IP Manajemen', placeholder: '192.168.99.1', required: true, mono: true },
  { id: 'manufacture',  label: 'Vendor',       placeholder: 'mikrotik', list: ['mikrotik'], required: true },
  { id: 'os_version',   label: 'Versi OS',     placeholder: 'ros7', list: ['ros6', 'ros7'], required: true },
  { id: 'role',         label: 'Role',         placeholder: 'gateway', list: ['gateway', 'core', 'distribution', 'access'], required: true },
  { id: 'network_type', label: 'Tipe Jaringan', placeholder: 'kampus', required: true },
  { id: 'username', required: true,     label: 'Username SSH', placeholder: 'admin', mono: true },
  { id: 'password', required: true,     label: 'Password SSH', type: 'password', mono: true },
  { id: 'username_env', required: true, label: 'Username env', placeholder: 'NODE_USER', mono: true },
  { id: 'password_env', required: true, label: 'Password env', placeholder: 'NODE_PASS', mono: true },
];

// Nodes are registered through the active backend's POST /devices. NetOps
// Agent has no list/update/delete endpoint yet, so this screen only adds nodes
// and remembers the ones added since the page was opened.
export async function screenNodes(c) {
  const backend = activeBackend();
  if (!backend.capabilities.devices) {
    c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
      ${pageHeader('Nodes', 'Kelola node jaringan.')}
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-8 text-center text-body-sm text-on-surface-variant">
        Backend aktif (<b>${esc(backend.label)}</b>) belum menyediakan API node. Pilih NetOps Agent di Settings.
      </div></div>`;
    return;
  }

  const added = [];
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    ${pageHeader('Nodes', 'Daftarkan perangkat jaringan ke NetOps Agent.')}
    <form id="nd-form" class="bg-surface-container-lowest border border-outline-variant rounded-lg p-5 grid grid-cols-1 md:grid-cols-2 gap-4" autocomplete="off">
      ${FIELDS.map(f => `<label class="text-label-md text-on-surface-variant">${f.label}${f.required ? ' *' : ''}
        <input id="nd-${f.id}" name="${f.id}" type="${f.type || 'text'}" ${f.required ? 'required' : ''}
          ${f.list ? `list="nd-${f.id}-list"` : ''} placeholder="${esc(f.placeholder || '')}"
          class="mt-1 w-full border border-outline-variant rounded-md px-3 py-2 text-body-sm ${f.mono ? 'font-data-mono' : ''}"/>
        ${f.list ? `<datalist id="nd-${f.id}-list">${f.list.map(v => `<option value="${esc(v)}">`).join('')}</datalist>` : ''}
      </label>`).join('')}
      <div class="md:col-span-2 flex items-center gap-3">
        <button id="nd-save" type="submit" class="px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 disabled:opacity-50">Tambah Node</button>
        <span id="nd-msg" class="text-body-sm"></span>
      </div>
    </form>
    <div id="nd-added" class="mt-6"></div>
  </div>`;

  function renderAdded() {
    $('nd-added').innerHTML = added.length ? `<h3 class="text-title-sm font-title-sm text-primary mb-2">Ditambahkan pada sesi ini</h3>
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <table class="w-full text-body-sm"><thead class="bg-surface-container text-left"><tr>
          <th class="px-3 py-2">Nama</th><th class="px-3 py-2">IP</th><th class="px-3 py-2">Vendor</th><th class="px-3 py-2">OS</th><th class="px-3 py-2">Role</th><th class="px-3 py-2">Jaringan</th><th class="px-3 py-2">Port</th></tr></thead>
        <tbody>${added.map(d => `<tr class="border-t border-outline-variant">
          <td class="px-3 py-2 font-medium">${esc(d.name)}</td><td class="px-3 py-2 font-data-mono">${esc(d.mgmt_ip)}</td>
          <td class="px-3 py-2">${esc(d.manufacture)}</td><td class="px-3 py-2">${esc(d.os_version)}</td>
          <td class="px-3 py-2">${esc(d.role)}</td><td class="px-3 py-2">${esc(d.network_type)}</td><td class="px-3 py-2">${esc(String(d.port ?? ''))}</td></tr>`).join('')}
        </tbody></table></div>` : '';
  }

  $('nd-form').addEventListener('submit', async e => {
    e.preventDefault();
    const body = {};
    for (const f of FIELDS) {
      const v = $('nd-' + f.id).value.trim();
      if (v) body[f.id] = v;
    }
    const msg = $('nd-msg'), btn = $('nd-save');
    btn.disabled = true;
    msg.className = 'text-body-sm text-on-surface-variant';
    msg.textContent = 'Menyimpan…';
    try {
      const d = await backend.addDevice(body);
      added.unshift(d);
      renderAdded();
      $('nd-form').reset();
      msg.className = 'text-body-sm text-green-700';
      msg.textContent = `Node ${d.name} ditambahkan.`;
    } catch (err) {
      msg.className = 'text-body-sm text-red-700';
      msg.textContent = err.message;
    } finally {
      btn.disabled = false;
    }
  });
}
