import { apiGet, apiPost } from '../api.js';
import { $, esc, badge, pageHeader, loadingHtml, errorHtml, parseRouterList } from '../utils.js';

export async function screenNetwork(c) {
  let routers = [
    { name: 'Core-RT01',  host: '10.0.0.1',     status: 'gray', st: 'CONFIGURED', rtt: '—', cpu: 0, ram: 0, up: '—' },
    { name: 'Dist-SW02',  host: '10.5.10.2',    status: 'gray', st: 'CONFIGURED', rtt: '—', cpu: 0, ram: 0, up: '—' },
    { name: 'Edge-GW04',  host: '172.16.2.254', status: 'gray', st: 'CONFIGURED', rtt: '—', cpu: 0, ram: 0, up: '—' },
  ];
  let netErr = '';
  try {
    const r = await apiGet('/api/tools/routers');
    const parsed = parseRouterList(r.result);
    if (parsed.length) {
      routers = parsed.map(p => ({ name: p.name, host: p.host, status: 'gray', st: 'CONFIGURED', rtt: '—', cpu: 0, ram: 0, up: '—' }));
    }
  } catch (e) { netErr = 'Gagal memuat daftar router: ' + e.message; }

  const barColor = v => v >= 80 ? 'bg-red-600' : v >= 60 ? 'bg-amber-500' : 'bg-green-600';
  const cell = v => `<td class="py-3 px-2">
    <div class="flex items-center gap-2 w-32">
      <div class="flex-1 h-1.5 bg-surface-container-highest rounded-full overflow-hidden">
        <div class="h-full ${barColor(v)}" style="width:${v}%;"></div>
      </div>
      <span class="font-data-mono-sm text-data-mono-sm w-8 text-right">${v}%</span>
    </div>
  </td>`;

  const rows = routers.map(r => `<tr class="hover:bg-surface-container-low transition-colors group">
    <td class="py-3 px-2"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-outline text-[18px]">router</span><span class="font-data-mono text-data-mono font-medium text-primary">${esc(r.name)}</span></div></td>
    <td class="py-3 px-2 font-data-mono text-data-mono text-on-surface-variant">${esc(r.host)}</td>
    <td class="py-3 px-2">${badge(r.st, r.status)}</td>
    <td class="py-3 px-2 font-data-mono text-data-mono">${esc(r.rtt)}</td>
    ${cell(r.cpu)}${cell(r.ram)}
    <td class="py-3 px-2 font-data-mono-sm text-data-mono-sm text-on-surface-variant">${esc(r.up)}</td>
  </tr>`).join('');

  const ifaces = [
    { iface: 'ether1 (Uplink)',   rx: '842 Mbps', tx: '118 Mbps', pct: 84 },
    { iface: 'ether2 (Core-A)',   rx: '312 Mbps', tx: '298 Mbps', pct: 31 },
    { iface: 'sfp-sfpplus1',      rx: '1.2 Gbps', tx: '940 Mbps', pct: 62 },
    { iface: 'vlan100 (Faculty)', rx: '88 Mbps',  tx: '44 Mbps',  pct: 12 },
  ];
  const ifaceRows = ifaces.map(i => `<div class="flex items-center justify-between gap-4 py-2.5 border-b border-outline-variant last:border-0">
    <div class="w-40 shrink-0"><p class="font-data-mono text-data-mono font-medium text-primary truncate">${esc(i.iface)}</p></div>
    <div class="flex-1 flex items-center gap-2">
      <div class="flex-1 h-1.5 bg-surface-container-highest rounded-full overflow-hidden"><div class="h-full ${barColor(i.pct)}" style="width:${i.pct}%;"></div></div>
      <span class="font-data-mono-sm text-data-mono-sm w-8 text-right">${i.pct}%</span>
    </div>
    <div class="flex gap-6 w-48 justify-end font-data-mono-sm text-data-mono-sm">
      <span class="text-green-700">▼ ${esc(i.rx)}</span>
      <span class="text-blue-700">▲ ${esc(i.tx)}</span>
    </div>
  </div>`).join('');

  const talkers = [
    { host: '10.0.10.45',     name: 'MEDIA-SRV-01',    bytes: '48.2 GB', flows: '12,401' },
    { host: '172.16.50.112',  name: 'MKTG-DELL-XPS-04', bytes: '22.9 GB', flows: '8,210'  },
    { host: '10.100.40.12',   name: 'BACKUP-NAS-A',     bytes: '18.4 GB', flows: '1,902'  },
    { host: '192.168.200.8',  name: 'IOT-GATEWAY',      bytes: '9.1 GB',  flows: '44,108' },
  ];
  const talkerRows = talkers.map((t, idx) => `<tr class="${idx % 2 ? 'bg-[#F8FAFC]' : 'bg-white'} hover:bg-surface-container-low transition-colors">
    <td class="py-2.5 px-4 font-data-mono text-data-mono text-primary">${esc(t.host)}</td>
    <td class="py-2.5 px-4 text-body-sm">${esc(t.name)}</td>
    <td class="py-2.5 px-4 text-right font-data-mono text-data-mono">${esc(t.bytes)}</td>
    <td class="py-2.5 px-4 text-right font-data-mono-sm text-data-mono-sm text-on-surface-variant">${esc(t.flows)}</td>
  </tr>`).join('');

  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Network Monitor', 'Real-time reachability, resource load, and traffic across managed routers.', `
      <button id="net-refresh" class="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded text-primary font-body-md hover:bg-surface-container transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">refresh</span> Refresh
      </button>
      <button id="net-healthcheck" class="px-4 py-2 bg-secondary text-white rounded font-body-md hover:bg-secondary/90 transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">monitoring</span> Run Health Check
      </button>`)}
    ${netErr ? errorHtml(netErr) : ''}
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg mb-stack_gap_lg overflow-hidden">
      <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
        <h3 class="font-title-sm text-title-sm text-primary">Router Overview</h3>
        <span class="text-label-caps font-label-caps text-on-surface-variant">Live Updates</span>
      </div>
      <div class="overflow-x-auto px-6 pb-2">
        <table class="w-full text-left border-collapse">
          <thead><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
            <th class="py-3 px-2">Router</th><th class="py-3 px-2">Host</th><th class="py-3 px-2">Status</th>
            <th class="py-3 px-2">RTT</th><th class="py-3 px-2">CPU</th><th class="py-3 px-2">RAM</th><th class="py-3 px-2">Uptime</th>
          </tr></thead>
          <tbody id="net-router-body" class="divide-y divide-outline-variant">${rows}</tbody>
        </table>
      </div>
    </div>
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-lg">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Interface Traffic — Core-RT01</h3>
          <span class="text-label-caps font-label-caps text-on-surface-variant">RX / TX</span>
        </div>
        <div class="px-6 py-2">${ifaceRows}</div>
      </div>
      <div class="col-span-12 xl:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Top Talkers</h3>
          <span class="text-label-caps font-label-caps text-on-surface-variant">Last 1h</span>
        </div>
        <div class="overflow-x-auto">
          <table class="w-full text-left border-collapse">
            <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
              <th class="py-3 px-4">Host</th><th class="py-3 px-4">Name</th>
              <th class="py-3 px-4 text-right">Volume</th><th class="py-3 px-4 text-right">Flows</th>
            </tr></thead>
            <tbody class="divide-y divide-outline-variant">${talkerRows}</tbody>
          </table>
        </div>
      </div>
    </div>
  </div>`;

  async function runReachability() {
    const body = $('net-router-body');
    const btn = $('net-refresh');
    if (btn) btn.disabled = true;
    if (body) body.innerHTML = `<tr><td class="py-6 px-2 text-center text-on-surface-variant" colspan="7">${loadingHtml('Memeriksa reachability...')}</td></tr>`;
    try {
      const r = await apiPost('/api/tools/reachability/all', {});
      const results = r.results || {};
      const newRows = routers.map(rt => {
        const txt = results[rt.name] || '';
        const ok = /reachable|up|online|berhasil|ping ok|alive|0% packet loss|success/i.test(txt) && !/unreachable|gagal|fail|timeout|100% packet loss/i.test(txt);
        const down = /unreachable|gagal|fail|timeout|100% packet loss/i.test(txt);
        const status = down ? 'red' : ok ? 'green' : 'amber';
        const st = down ? 'OFFLINE' : ok ? 'ONLINE' : 'UNKNOWN';
        return `<tr class="hover:bg-surface-container-low transition-colors group">
          <td class="py-3 px-2"><div class="flex items-center gap-2"><span class="material-symbols-outlined text-outline text-[18px]">router</span><span class="font-data-mono text-data-mono font-medium text-primary">${esc(rt.name)}</span></div></td>
          <td class="py-3 px-2 font-data-mono text-data-mono text-on-surface-variant">${esc(rt.host)}</td>
          <td class="py-3 px-2">${badge(st, status)}</td>
          <td class="py-3 px-2 font-data-mono-sm text-data-mono-sm text-on-surface-variant truncate max-w-[260px]" title="${esc(txt)}">${esc((txt || '—').split('\n')[0].slice(0, 60))}</td>
          <td class="py-3 px-2 text-on-surface-variant" colspan="3">—</td>
        </tr>`;
      }).join('');
      if (body) body.innerHTML = newRows;
    } catch (e) {
      if (body) body.innerHTML = `<tr><td class="py-4 px-2 text-red-700 text-body-sm" colspan="7">Gagal: ${esc(e.message)}</td></tr>`;
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  const refreshBtn = $('net-refresh');
  if (refreshBtn) refreshBtn.onclick = runReachability;
  const hcBtn = $('net-healthcheck');
  if (hcBtn) hcBtn.onclick = () => { location.hash = 'chat'; };
}
