import { apiPost } from '../api.js';
import { $, esc, pageHeader, loadingHtml, errorHtml } from '../utils.js';

export async function screenDHCP(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('DHCP Monitor', 'Pool utilization, active leases, and device lookup across all DHCP servers.', `
      <button id="dhcp-refresh" class="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded text-primary font-body-md hover:bg-surface-container transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">refresh</span> Refresh
      </button>`)}
    <div id="dhcp-pools" class="mb-stack_gap_lg">${loadingHtml('Memuat pool DHCP...')}</div>
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-lg">
        <div class="px-6 py-4 border-b border-outline-variant">
          <h3 class="font-title-sm text-title-sm text-primary">Pencarian Device</h3>
        </div>
        <div class="p-6">
          <form id="dhcp-lookup-form" class="flex gap-3">
            <input id="dhcp-lookup-input" type="text" placeholder="MAC address atau nama host..." class="flex-1 px-3 py-2 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus:outline-none focus:ring-1 focus:ring-primary">
            <button type="submit" class="px-4 py-2 bg-primary text-white rounded text-body-sm font-medium hover:bg-primary/90 transition-colors">Cari</button>
          </form>
          <div id="dhcp-lookup-result" class="mt-4"></div>
        </div>
      </div>
      <div class="col-span-12 xl:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Active Leases</h3>
          <span id="dhcp-lease-count" class="text-label-caps font-label-caps text-on-surface-variant">—</span>
        </div>
        <div id="dhcp-leases" class="overflow-y-auto max-h-[420px]">${loadingHtml('Memuat leases...')}</div>
      </div>
    </div>
  </div>`;

  async function loadPools() {
    const el = $('dhcp-pools');
    if (!el) return;
    try {
      const r = await apiPost('/api/tools/call', { tool: 'audit_dhcp_pools', params: {} });
      const txt = (r.result || r.output || '').trim();
      if (!txt) { el.innerHTML = errorHtml('Tidak ada data pool.'); return; }

      const barColor = v => v >= 90 ? 'bg-red-600' : v >= 75 ? 'bg-amber-500' : 'bg-green-600';
      const sections = txt.split(/(?=Router:)/i).filter(s => s.trim());
      let html = '<div class="grid grid-cols-12 gap-stack_gap_md">';
      for (const sec of sections) {
        const lines = sec.trim().split('\n');
        const routerName = (lines[0] || '').replace(/^Router:\s*/i, '').trim() || 'Unknown';
        const pools = [];
        for (const pl of lines.slice(1)) {
          const m = pl.match(/(\S+)\s+(\d+)\/(\d+)\s+\((\d+)%\)/);
          if (m) pools.push({ name: m[1], used: parseInt(m[2]), total: parseInt(m[3]), pct: parseInt(m[4]) });
        }
        if (!pools.length) continue;
        html += `<div class="col-span-12 md:col-span-6 xl:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-lg p-5">
          <div class="flex items-center gap-2 mb-4">
            <span class="material-symbols-outlined text-primary text-[18px]">router</span>
            <h4 class="font-title-sm text-title-sm text-primary">${esc(routerName)}</h4>
          </div>
          ${pools.map(p => `<div class="mb-3">
            <div class="flex justify-between text-label-caps font-label-caps mb-1">
              <span class="text-on-surface-variant">${esc(p.name)}</span>
              <span class="${p.pct >= 90 ? 'text-red-700' : p.pct >= 75 ? 'text-amber-700' : 'text-green-700'}">${p.used}/${p.total} (${p.pct}%)</span>
            </div>
            <div class="h-2 bg-surface-container-highest rounded-full overflow-hidden">
              <div class="h-full ${barColor(p.pct)} transition-all" style="width:${p.pct}%;"></div>
            </div>
          </div>`).join('')}
        </div>`;
      }
      html += '</div>';
      el.innerHTML = (sections.length && html.includes('mb-3')) ? html : errorHtml('Tidak ada pool DHCP yang berhasil di-parse.');
    } catch (e) {
      el.innerHTML = errorHtml('Gagal memuat pool: ' + e.message);
    }
  }

  async function loadLeases() {
    const el = $('dhcp-leases');
    const countEl = $('dhcp-lease-count');
    if (!el) return;
    try {
      const r = await apiPost('/api/tools/call', { tool: 'get_dhcp_leases', params: {} });
      const txt = (r.result || r.output || '').trim();
      const lines = txt.split('\n').filter(l => l.trim() && !/^Router:|^-+$|^Active DHCP/i.test(l));
      if (!lines.length) {
        el.innerHTML = `<div class="px-6 py-8 text-center text-on-surface-variant text-body-sm">Tidak ada lease aktif.</div>`;
        return;
      }
      if (countEl) countEl.textContent = `${lines.length} leases`;
      el.innerHTML = lines.map(line => {
        const parts = line.trim().split(/\s+/);
        const mac = parts.find(p => /([0-9A-Fa-f]{2}:){5}/.test(p)) || '—';
        const ip = parts.find(p => /^\d+\.\d+\.\d+\.\d+$/.test(p)) || '—';
        const name = parts.filter(p => p !== mac && p !== ip).join(' ') || '—';
        return `<div class="flex items-center px-6 py-2.5 border-b border-outline-variant hover:bg-surface-container-low transition-colors text-body-sm">
          <span class="w-36 font-data-mono text-data-mono text-primary shrink-0">${esc(ip)}</span>
          <span class="flex-1 truncate text-on-surface-variant">${esc(name)}</span>
          <span class="w-40 font-data-mono-sm text-data-mono-sm text-on-surface-variant shrink-0 text-right">${esc(mac)}</span>
        </div>`;
      }).join('');
    } catch (e) {
      el.innerHTML = errorHtml('Gagal memuat leases: ' + e.message);
    }
  }

  const lkForm = $('dhcp-lookup-form');
  if (lkForm) lkForm.onsubmit = async e => {
    e.preventDefault();
    const q = ($('dhcp-lookup-input') || {}).value || '';
    if (!q.trim()) return;
    const res = $('dhcp-lookup-result');
    if (res) res.innerHTML = loadingHtml('Mencari...');
    try {
      const r = await apiPost('/api/tools/call', { tool: 'find_dhcp_device', params: { query: q.trim() } });
      const txt = (r.result || r.output || '').trim();
      if (res) res.innerHTML = txt
        ? `<div class="bg-surface-container-low rounded-lg p-4 font-data-mono-sm text-data-mono-sm whitespace-pre-wrap">${esc(txt)}</div>`
        : `<div class="text-on-surface-variant text-body-sm">Tidak ditemukan.</div>`;
    } catch (err) {
      if (res) res.innerHTML = errorHtml(err.message);
    }
  };

  const refreshBtn = $('dhcp-refresh');
  if (refreshBtn) refreshBtn.onclick = () => { loadPools(); loadLeases(); };

  loadPools();
  loadLeases();
}
