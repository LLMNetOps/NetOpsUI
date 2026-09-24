import { esc, pageHeader, $, confirmDialog } from '../utils.js';
import { activeBackend } from '../backends/index.js';

const FIELDS = [
  { id: 'name',         label: 'Nama',         placeholder: 'core-gw-01', required: true },
  { id: 'mgmt_ip',      label: 'IP Manajemen', placeholder: '192.168.99.1', required: true, mono: true },
  { id: 'manufacture',  label: 'Vendor',       placeholder: 'mikrotik', list: ['mikrotik'], required: true },
  { id: 'os_version',   label: 'Versi OS',     placeholder: 'ros7', list: ['ros6', 'ros7'], required: true },
  { id: 'role',         label: 'Role',         placeholder: 'gateway', list: ['gateway', 'core', 'distribution', 'access'], required: true },
  { id: 'network_type', label: 'Tipe Jaringan', placeholder: 'kampus', required: true },
  { id: 'port',         label: 'Port SSH',     placeholder: '22', type: 'number', mono: true },
  { id: 'username', required: true,     label: 'Username SSH', placeholder: 'admin', mono: true, credential: true },
  { id: 'password', required: true,     label: 'Password SSH', type: 'password', mono: true, credential: true },
  { id: 'username_env', required: true, label: 'Username env', placeholder: 'NODE_USER', mono: true },
  { id: 'password_env', required: true, label: 'Password env', placeholder: 'NODE_PASS', mono: true },
];

const INPUT_CLS = 'w-full px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary disabled:bg-surface-container disabled:text-on-surface-variant';

// Nodes are managed through the active backend's /devices API. The list never
// carries credentials, so the detail view shows only the env var names and the
// edit form leaves username/password blank to mean "unchanged".
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

  let devices = [];
  let loadError = null;
  let mode = { type: 'add' }; // add | view | edit, the latter two carry `name`

  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Nodes', 'Kelola perangkat jaringan NetOps Agent. Pilih node di tabel untuk melihat detail.', `
      <button id="nd-new" class="px-4 py-2 bg-primary text-white rounded font-body-md hover:bg-primary/90 transition-colors flex items-center gap-2">
        <span class="material-symbols-outlined text-sm">add</span> Add Node
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg items-start">
      <div class="col-span-12 xl:col-span-5">
        <div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
          <div class="px-6 py-3 border-b border-outline-variant">
            <h3 class="font-title-sm text-title-sm text-primary">Managed Nodes <span id="nd-count" class="text-on-surface-variant font-normal"></span></h3>
          </div>
          <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
              <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
                <th class="py-3 px-4">Name</th><th class="py-3 px-4">Host</th><th class="py-3 px-4">Role / Network</th><th class="py-3 px-2"></th>
              </tr></thead>
              <tbody id="nd-tbody" class="divide-y divide-outline-variant"><tr><td class="py-8 px-4 text-center text-body-sm text-on-surface-variant" colspan="4">Memuat…</td></tr></tbody>
            </table>
          </div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-7"><div id="nd-panel"></div></div>
    </div>
  </div>`;

  const find = name => devices.find(d => d.name === name);
  const setMsg = (text, kind) => {
    const m = $('nd-msg');
    if (!m) return;
    m.className = 'text-body-sm ' + ({ ok: 'text-green-700', err: 'text-red-700' }[kind] || 'text-on-surface-variant');
    m.textContent = text;
  };

  function renderTable() {
    const tb = $('nd-tbody');
    $('nd-count').textContent = loadError ? '' : `(${devices.length})`;
    if (loadError) {
      tb.innerHTML = `<tr><td class="py-6 px-4 text-center text-body-sm text-red-700" colspan="4">Gagal memuat daftar node: ${esc(loadError)}</td></tr>`;
      return;
    }
    if (!devices.length) {
      tb.innerHTML = `<tr><td class="py-8 px-4 text-center text-body-sm text-on-surface-variant" colspan="4">Belum ada node. Klik "Add Node".</td></tr>`;
      return;
    }
    tb.innerHTML = devices.map(d => {
      const selected = mode.name === d.name;
      return `<tr data-row="${esc(d.name)}" class="cursor-pointer transition-colors ${selected ? 'bg-primary/5 border-l-[3px] border-l-primary' : 'hover:bg-surface-container-low border-l-[3px] border-l-transparent'}">
        <td class="py-2.5 px-4"><p class="font-medium text-primary truncate max-w-[160px]">${esc(d.name)}</p></td>
        <td class="py-2.5 px-4 font-data-mono text-data-mono text-on-surface-variant">${esc(d.mgmt_ip || '—')}${d.port && d.port !== 22 ? ':' + esc(String(d.port)) : ''}</td>
        <td class="py-2.5 px-4 text-body-sm text-on-surface-variant">${esc(d.role || '—')} / ${esc(d.network_type || '—')}</td>
        <td class="py-2.5 px-2 whitespace-nowrap text-right">
          <button data-edit="${esc(d.name)}" title="Edit" class="p-1 rounded hover:bg-surface-container text-on-surface-variant"><span class="material-symbols-outlined text-[18px]">edit</span></button>
          <button data-del="${esc(d.name)}" title="Hapus" class="p-1 rounded hover:bg-red-50 text-red-700"><span class="material-symbols-outlined text-[18px]">delete</span></button>
        </td></tr>`;
    }).join('');
    tb.querySelectorAll('[data-row]').forEach(tr => { tr.onclick = () => show({ type: 'view', name: tr.dataset.row }); });
    tb.querySelectorAll('[data-edit]').forEach(b => { b.onclick = e => { e.stopPropagation(); show({ type: 'edit', name: b.dataset.edit }); }; });
    tb.querySelectorAll('[data-del]').forEach(b => { b.onclick = e => { e.stopPropagation(); removeNode(b.dataset.del); }; });
  }

  function renderDetail(d) {
    const row = (label, value, mono) => `<div>
      <p class="text-label-caps font-label-caps text-on-surface-variant mb-1">${label}</p>
      <p class="text-body-sm ${mono ? 'font-data-mono' : ''}">${value ? esc(String(value)) : '—'}</p></div>`;
    $('nd-panel').innerHTML = `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
      <div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
        <div><h3 class="font-title-sm text-title-sm text-primary font-bold">${esc(d.name)}</h3>
          <p class="text-body-sm text-on-surface-variant">Detail node</p></div>
        <div class="flex gap-2">
          <button id="nd-edit" class="px-3 py-1.5 border border-outline-variant rounded text-body-sm font-medium hover:bg-surface-container flex items-center gap-1"><span class="material-symbols-outlined text-sm">edit</span>Edit</button>
          <button id="nd-del" class="px-3 py-1.5 border border-red-200 text-red-700 rounded text-body-sm font-medium hover:bg-red-50 flex items-center gap-1"><span class="material-symbols-outlined text-sm">delete</span>Hapus</button>
        </div>
      </div>
      <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4">
        ${row('IP Manajemen', d.mgmt_ip, true)}${row('Port SSH', d.port, true)}
        ${row('Vendor', d.manufacture)}${row('Versi OS', d.os_version)}
        ${row('Role', d.role)}${row('Tipe Jaringan', d.network_type)}
        ${row('Username env', d.username_env, true)}${row('Password env', d.password_env, true)}
      </div>
      <div class="px-6 py-3 border-t border-outline-variant text-body-sm text-on-surface-variant">
        Username dan password SSH tersimpan di backend dan tidak ditampilkan.</div>
    </div>`;
    $('nd-edit').onclick = () => show({ type: 'edit', name: d.name });
    $('nd-del').onclick = () => removeNode(d.name);
  }

  function renderForm(existing) {
    const editing = !!existing;
    $('nd-panel').innerHTML = `<form id="nd-form" class="bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden" autocomplete="off">
      <div class="px-6 py-4 border-b border-outline-variant">
        <h3 class="font-title-sm text-title-sm text-primary font-bold">${editing ? 'Edit ' + esc(existing.name) : 'Add Node'}</h3>
        <p class="text-body-sm text-on-surface-variant">${editing
          ? 'Nama tidak dapat diubah. Kosongkan username/password SSH untuk tidak mengubahnya.'
          : 'Kredensial SSH dikirim ke NetOps Agent dan tidak ditampilkan kembali.'}</p>
      </div>
      <div class="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
        ${FIELDS.map(f => {
          const required = f.required && !(editing && f.credential);
          const placeholder = editing && f.credential ? 'Tidak diubah' : f.placeholder || '';
          return `<div>
            <label for="nd-${f.id}" class="block text-label-caps font-label-caps text-on-surface-variant mb-1">${f.label}${required ? ' *' : ''}</label>
            <input id="nd-${f.id}" name="${f.id}" type="${f.type || 'text'}" ${required ? 'required' : ''} ${editing && f.id === 'name' ? 'disabled' : ''}
              ${f.list ? `list="nd-${f.id}-list"` : ''} placeholder="${esc(placeholder)}" value="${editing && !f.credential ? esc(String(existing[f.id] ?? '')) : ''}"
              class="${INPUT_CLS} ${f.mono ? 'font-data-mono' : ''}"/>
            ${f.list ? `<datalist id="nd-${f.id}-list">${f.list.map(v => `<option value="${esc(v)}">`).join('')}</datalist>` : ''}
          </div>`;
        }).join('')}
      </div>
      <div class="flex items-center justify-end gap-3 px-6 py-4 border-t border-outline-variant">
        <span id="nd-msg" class="text-body-sm"></span>
        ${editing ? '<button id="nd-cancel" type="button" class="px-4 py-2 border border-outline-variant rounded text-body-sm font-medium hover:bg-surface-container">Batal</button>' : ''}
        <button id="nd-save" type="submit" class="px-5 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-2 disabled:opacity-50">
          <span class="material-symbols-outlined text-sm">${editing ? 'save' : 'add'}</span>${editing ? 'Simpan' : 'Tambah Node'}
        </button>
      </div>
    </form>`;
    if (editing) $('nd-cancel').onclick = () => show({ type: 'view', name: existing.name });
    $('nd-form').addEventListener('submit', e => { e.preventDefault(); submit(existing); });
  }

  function show(next) {
    mode = next;
    const d = next.name ? find(next.name) : null;
    if (next.name && !d) mode = { type: 'add' };
    renderTable();
    if (mode.type === 'view') renderDetail(d);
    else renderForm(mode.type === 'edit' ? d : null);
  }

  async function refresh() {
    try {
      devices = await backend.listDevices();
      loadError = null;
    } catch (err) {
      devices = [];
      loadError = err.message;
    }
  }

  async function submit(existing) {
    const body = {};
    for (const f of FIELDS) {
      const v = $('nd-' + f.id).value.trim();
      if (!v) continue;
      body[f.id] = f.type === 'number' ? Number(v) : v;
    }
    const btn = $('nd-save');
    btn.disabled = true;
    setMsg('Menyimpan…');
    try {
      if (existing) {
        body.name = existing.name;
        await backend.updateDevice(existing.name, body);
        await refresh();
        show({ type: 'view', name: existing.name });
      } else {
        const d = await backend.addDevice(body);
        await refresh();
        show({ type: 'view', name: d.name });
      }
    } catch (err) {
      setMsg(explain(err, existing ? 'PUT' : 'POST'), 'err');
      btn.disabled = false;
    }
  }

  async function removeNode(name) {
    const ok = await confirmDialog({
      title: 'Hapus node',
      message: `Hapus node "${name}" dari inventory NetOps Agent?\nAgent tidak akan bisa lagi mengelola perangkat ini.`,
      confirmLabel: 'Hapus',
      danger: true,
    });
    if (!ok) return;
    try {
      await backend.deleteDevice(name);
    } catch (err) {
      await confirmDialog({ title: 'Gagal menghapus', message: explain(err, 'DELETE'), confirmLabel: 'OK', cancelLabel: null });
      return;
    }
    await refresh();
    show({ type: 'add' });
  }

  // FastAPI answers a route that does not exist with exactly {"detail":"Not Found"};
  // a real "node missing" error from the agent would carry its own message.
  function explain(err, method) {
    if (err.status === 405 || (err.status === 404 && err.message.endsWith(': Not Found'))) {
      return `NetOps Agent belum menyediakan endpoint ${method} /devices/{name}. (${err.message})`;
    }
    return err.message;
  }

  $('nd-new').onclick = () => show({ type: 'add' });
  renderTable();
  renderForm(null);
  await refresh();
  show({ type: 'add' });
}
