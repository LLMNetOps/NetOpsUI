import { apiGet, apiPost, apiPut, apiDelete } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml, confirmDialog, alertDialog } from '../utils.js';

const ROLES = ['access', 'backbone', 'gate_idren', 'lab'];
const NETWORKS = ['kampus', 'idren', 'lab'];

let _routersCache = [];
let _selectedName = null; // name of node shown in detail panel (edit mode)
let _creating = false;    // true while the detail panel shows the "new node" form
let _globalSSH = null;    // cached /api/config/ssh response

export async function screenNodes(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Nodes', 'Kelola router yang dikelola platform ini beserta kredensial SSH-nya. Pilih node di tabel untuk edit.', `
      <button id="btn-add-node" class="px-4 py-2 bg-primary text-white rounded font-body-md hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">add</span> Add Node
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg items-start">
      <div class="col-span-12 xl:col-span-5">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-6 py-3 border-b border-outline-variant">
            <h3 class="font-title-sm text-title-sm text-primary">Managed Nodes</h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
                <th class="py-3 px-4">Name</th>
                <th class="py-3 px-4">Host</th>
                <th class="py-3 px-4">Role / Network</th>
                <th class="py-3 px-4">SSH</th>
              </tr></thead>
              <tbody id="nodes-tbody" class="divide-y divide-outline-variant"><tr><td class="py-8 text-center" colspan="4">${loadingHtml()}</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-7">
        <div id="node-detail-panel" class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          ${loadingHtml('Memuat pengaturan SSH...')}
        </div>
      </div>
    </div>
  </div>`;

  const addBtn = $('btn-add-node');
  if (addBtn) addBtn.onclick = startCreate;

  _selectedName = null;
  _creating = false;
  await Promise.all([loadRouters(), loadGlobalSSH()]);
}

// ── Table ────────────────────────────────────────────────────────────────────

async function loadRouters() {
  const tb = $('nodes-tbody');
  try {
    const r = await apiGet('/api/config/routers');
    _routersCache = r.routers || [];
    renderRows();
  } catch (e) {
    if (tb) tb.innerHTML = `<tr><td class="py-6 px-4 text-center" colspan="4">${errorHtml('Gagal memuat nodes: ' + e.message)}</td></tr>`;
  }
}

function renderRows() {
  const tb = $('nodes-tbody');
  if (!tb) return;

  if (!_routersCache.length) {
    tb.innerHTML = `<tr><td class="py-8 px-4 text-center text-on-surface-variant text-body-sm" colspan="4">Belum ada node. Klik "Add Node".</td></tr>`;
    return;
  }

  tb.innerHTML = _routersCache.map(rt => {
    const isSelected = !_creating && _selectedName === rt.name;
    const sshBadge = rt.ssh_username
      ? badge('OVERRIDE', 'blue')
      : badge('DEFAULT', 'gray');
    return `<tr data-row-select="${esc(rt.name)}" class="cursor-pointer transition-colors ${isSelected ? 'bg-primary/5 border-l-[3px] border-l-primary' : 'hover:bg-surface-container-low border-l-[3px] border-l-transparent'}">
      <td class="py-2.5 px-4"><p class="font-medium text-primary truncate max-w-[160px]">${esc(rt.name)}</p></td>
      <td class="py-2.5 px-4 font-data-mono text-data-mono text-on-surface-variant">${esc(rt.host || '—')}</td>
      <td class="py-2.5 px-4 text-body-sm text-on-surface-variant">${esc(rt.role || '—')} / ${esc(rt.network || '—')}</td>
      <td class="py-2.5 px-4">${sshBadge}</td>
    </tr>`;
  }).join('');

  tb.querySelectorAll('[data-row-select]').forEach(row => {
    row.onclick = () => selectNode(row.dataset.rowSelect);
  });
}

// ── Detail panel — global SSH settings (default view) ────────────────────────

async function loadGlobalSSH() {
  try {
    _globalSSH = await apiGet('/api/config/ssh');
  } catch (e) {
    _globalSSH = { username: '', port: 22, timeout: 15, password_set: false, password_preview: '' };
  }
  if (!_selectedName && !_creating) renderSSHPanel();
}

function renderSSHPanel() {
  const panel = $('node-detail-panel');
  if (!panel) return;
  const cfg = _globalSSH || { username: '', port: 22, timeout: 15, password_set: false, password_preview: '' };
  panel.innerHTML = `<div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
    <div>
      <h3 class="font-title-sm text-title-sm text-primary font-bold">Default SSH Settings</h3>
      <p class="text-body-sm text-on-surface-variant">Kredensial default untuk login ke semua node. Node bisa override kredensial ini masing-masing.</p>
    </div>
  </div>
  <div class="p-6 space-y-4">
    <div id="ssh-error" class="hidden"></div>
    <div class="grid grid-cols-2 gap-4">
      <div class="col-span-2">
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Username</label>
        <input id="ssh-username" type="text" value="${esc(cfg.username || '')}" placeholder="netadmin" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div class="col-span-2">
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Password</label>
        <input id="ssh-password" type="password" autocomplete="off" placeholder="${cfg.password_set ? 'Kosongkan untuk tidak mengubah' : 'Belum diatur'}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Port</label>
        <input id="ssh-port" type="number" value="${esc(String(cfg.port ?? 22))}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Timeout (detik)</label>
        <input id="ssh-timeout" type="number" value="${esc(String(cfg.timeout ?? 15))}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
    </div>
  </div>
  <div class="flex justify-end px-6 py-4 border-t border-outline-variant">
    <button id="ssh-save" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
      <span class="material-symbols-outlined text-sm">save</span>Simpan
    </button>
  </div>`;

  $('ssh-save').onclick = async () => {
    const errEl = $('ssh-error');
    const saveBtn = $('ssh-save');
    const username = $('ssh-username').value.trim();
    const password = $('ssh-password').value;
    const port = parseInt($('ssh-port').value, 10) || 22;
    const timeout = parseInt($('ssh-timeout').value, 10) || 15;

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Menyimpan...';
    try {
      _globalSSH = await apiPut('/api/config/ssh', { username, password: password || undefined, port, timeout });
      renderSSHPanel();
    } catch (e) {
      errEl.innerHTML = errorHtml(e.message || 'Gagal menyimpan SSH settings.');
      errEl.classList.remove('hidden');
      saveBtn.disabled = false;
      saveBtn.innerHTML = '<span class="material-symbols-outlined text-sm">save</span>Simpan';
    }
  };
}

// ── Detail panel — node create/edit form ──────────────────────────────────────

async function startCreate() {
  _creating = true;
  _selectedName = null;
  renderRows();
  const panel = $('node-detail-panel');
  panel.innerHTML = nodeFormHtml(null, false);
  wireNodeForm(null, false);
}

function selectNode(name) {
  _creating = false;
  _selectedName = name;
  renderRows();
  const router = _routersCache.find(r => r.name === name);
  const panel = $('node-detail-panel');
  if (!router) {
    panel.innerHTML = errorHtml('Node tidak ditemukan.');
    return;
  }
  panel.innerHTML = nodeFormHtml(router, true);
  wireNodeForm(router, true);
}

function closeDetail() {
  _creating = false;
  _selectedName = null;
  renderRows();
  renderSSHPanel();
}

function nodeFormHtml(router, isEdit) {
  const opts = (list, current) => list.map(v => `<option value="${v}" ${v === current ? 'selected' : ''}>${v}</option>`).join('');
  return `<div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
    <h3 class="font-title-sm text-title-sm text-primary font-bold">${isEdit ? esc(router.name) : 'New Node'}</h3>
    <button id="nf-close" class="text-on-surface-variant hover:text-primary transition-colors p-1 rounded" title="Tutup"><span class="material-symbols-outlined text-[20px]">close</span></button>
  </div>
  <div class="p-6 space-y-4 max-h-[75vh] overflow-y-auto">
    <div id="nf-error" class="hidden"></div>
    <div class="grid grid-cols-2 gap-4">
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Name *</label>
        <input id="nf-name" type="text" value="${esc(router?.name || '')}" ${isEdit ? 'readonly' : ''} placeholder="e.g. FILKOM-2" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary ${isEdit ? 'bg-surface-container-low text-on-surface-variant' : ''}">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Host / IP *</label>
        <input id="nf-host" type="text" value="${esc(router?.host || '')}" placeholder="10.x.x.x" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Role</label>
        <select id="nf-role" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">${opts(ROLES, router?.role || 'backbone')}</select>
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Network</label>
        <select id="nf-network" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">${opts(NETWORKS, router?.network || 'kampus')}</select>
      </div>
      <div>
        <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">RouterOS Version</label>
        <select id="nf-ros" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">${opts(['6', '7'], String(router?.ros_version ?? 7))}</select>
      </div>
    </div>
    <div class="pt-2 border-t border-outline-variant">
      <p class="text-body-sm font-medium text-primary mb-1">SSH Credentials</p>
      <p class="text-[11px] text-on-surface-variant mb-3">Kosongkan Username untuk memakai Default SSH Settings global.</p>
      <div class="grid grid-cols-2 gap-4">
        <div>
          <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Username</label>
          <input id="nf-ssh-username" type="text" value="${esc(router?.ssh_username || '')}" placeholder="Pakai default global" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
        </div>
        <div>
          <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1">Password</label>
          <input id="nf-ssh-password" type="password" autocomplete="off" placeholder="${isEdit && router?.ssh_password_set ? 'Kosongkan untuk tidak mengubah' : 'Pakai default global'}" class="w-full px-3 py-2 border border-outline-variant rounded text-body-sm font-data-mono bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
        </div>
      </div>
    </div>
  </div>
  <div class="flex justify-between items-center px-6 py-4 border-t border-outline-variant">
    <div class="flex gap-3">
      ${isEdit ? `<button id="nf-test" class="px-4 py-2 border border-outline-variant text-on-surface-variant rounded text-body-sm hover:bg-surface-container-low transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">wifi_tethering</span>Test
      </button>
      <button id="nf-delete" class="px-4 py-2 border border-red-200 text-red-600 rounded text-body-sm hover:bg-red-50 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">delete</span>Hapus
      </button>` : ''}
    </div>
    <div class="flex gap-3">
      <button id="nf-cancel" class="px-4 py-2 border border-outline-variant rounded text-body-sm text-on-surface-variant hover:bg-surface-container-low transition-colors">${isEdit ? 'Reset' : 'Batal'}</button>
      <button id="nf-save" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Node'}
      </button>
    </div>
  </div>`;
}

function wireNodeForm(router, isEdit) {
  $('nf-close').onclick = closeDetail;

  $('nf-cancel').onclick = () => {
    if (isEdit) {
      $('node-detail-panel').innerHTML = nodeFormHtml(router, true);
      wireNodeForm(router, true);
    } else {
      closeDetail();
    }
  };

  const testBtn = $('nf-test');
  if (testBtn) testBtn.onclick = async () => {
    testBtn.disabled = true;
    const orig = testBtn.innerHTML;
    testBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Testing...';
    try {
      const r = await apiPost('/api/tools/reachability', { router_name: router.name });
      await alertDialog(r.result || 'no result', router.name);
    } catch (e) {
      await alertDialog('Gagal: ' + e.message, 'Terjadi Kesalahan');
    } finally {
      testBtn.disabled = false;
      testBtn.innerHTML = orig;
    }
  };

  const deleteBtn = $('nf-delete');
  if (deleteBtn) deleteBtn.onclick = async () => {
    const ok = await confirmDialog({
      title: 'Hapus node?', message: `Node "${router.name}" akan dihapus permanen dari database.`,
      confirmLabel: 'Hapus', danger: true,
    });
    if (!ok) return;
    try {
      await apiDelete('/api/config/routers/' + encodeURIComponent(router.name));
      closeDetail();
      await loadRouters();
    } catch (e) {
      await alertDialog('Gagal menghapus: ' + e.message, 'Terjadi Kesalahan');
    }
  };

  $('nf-save').onclick = async () => {
    const errEl = $('nf-error');
    const saveBtn = $('nf-save');
    const name = ($('nf-name').value || '').trim();
    const host = ($('nf-host').value || '').trim();
    const role = $('nf-role').value;
    const network = $('nf-network').value;
    const ros_version = parseInt($('nf-ros').value, 10);
    const ssh_username = ($('nf-ssh-username').value || '').trim();
    const ssh_password = $('nf-ssh-password').value;

    if (!name) { errEl.innerHTML = errorHtml('Name wajib diisi.'); errEl.classList.remove('hidden'); return; }
    if (!host) { errEl.innerHTML = errorHtml('Host wajib diisi.'); errEl.classList.remove('hidden'); return; }

    errEl.classList.add('hidden');
    saveBtn.disabled = true;
    saveBtn.innerHTML = '<span class="material-symbols-outlined animate-spin text-sm">progress_activity</span> Menyimpan...';

    try {
      if (isEdit) {
        await apiPut('/api/config/routers/' + encodeURIComponent(router.name), {
          host, role, network, ros_version,
          ssh_username, ssh_password: ssh_password || undefined,
        });
      } else {
        await apiPost('/api/config/routers', {
          name, host, role, network, ros_version, ssh_username, ssh_password,
        });
        _creating = false;
        _selectedName = name;
      }
      await loadRouters();
      if (_selectedName) selectNode(_selectedName);
    } catch (e) {
      errEl.innerHTML = errorHtml(e.message || 'Gagal menyimpan node.');
      errEl.classList.remove('hidden');
      saveBtn.disabled = false;
      saveBtn.innerHTML = `<span class="material-symbols-outlined text-sm">save</span>${isEdit ? 'Simpan Perubahan' : 'Buat Node'}`;
    }
  };
}
