import { AGENTS } from '../config.js';
import { S } from '../state.js';
import { apiGet } from '../api.js';
import { esc, badge, cardHtml, statCardHtml, parseRouterList } from '../utils.js';

export async function screenDashboard(c) {
  const ICONS = {};
  AGENTS.forEach(a => { ICONS[a.name] = a.icon; });

  const [statusR, agentsR, routersR] = await Promise.allSettled([
    apiGet('/api/status'),
    apiGet('/api/agents'),
    apiGet('/api/tools/routers'),
  ]);

  let st = statusR.status === 'fulfilled' ? statusR.value : (S.systemStatus || {});
  if (statusR.status === 'fulfilled') S.systemStatus = st;
  st = st || {};

  let agentList = AGENTS.map(a => ({ name: a.name, alias: a.alias, role: a.role, icon: a.icon }));
  if (agentsR.status === 'fulfilled' && Array.isArray(agentsR.value.agents) && agentsR.value.agents.length) {
    agentList = agentsR.value.agents.map(a => ({
      name: a.name,
      alias: a.alias || a.name,
      role: (a.description || '').split('.')[0].slice(0, 28) || a.name,
      icon: ICONS[a.name] || 'smart_toy',
    }));
  }
  const agentCount = agentList.length;
  const agentCards = agentList.map(a =>
    `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-3 shadow-sm text-center min-w-[120px]">
      <span class="material-symbols-outlined text-2xl text-primary mb-1">${a.icon}</span>
      <p class="text-xs font-bold uppercase text-primary">${esc(a.alias)}</p>
      <p class="text-[10px] text-on-surface-variant truncate">${esc(a.role)}</p>
    </div>`
  ).join('');

  let routerRowsHtml = `<tr><td class="px-4 py-2 font-medium">—</td><td class="px-4 py-2 font-data-mono text-data-mono">—</td><td class="px-4 py-2">${badge('PENDING', 'gray')}</td></tr>`;
  let routerNote = 'Connect to backend to load router data.';
  if (routersR.status === 'fulfilled') {
    const rows = parseRouterList(routersR.value.result);
    if (rows.length) {
      routerRowsHtml = rows.map(r => `<tr>
        <td class="px-4 py-2 font-medium">${esc(r.name)}</td>
        <td class="px-4 py-2 font-data-mono text-data-mono">${esc(r.host || '—')}</td>
        <td class="px-4 py-2">${badge('CONFIGURED', 'blue')}</td>
      </tr>`).join('');
      routerNote = `${rows.length} router(s) configured. Open Network to run reachability checks.`;
    } else {
      routerNote = 'No routers configured.';
    }
  } else {
    routerNote = 'Backend unavailable — showing placeholder.';
  }

  const ollamaTxt = st.ollama_url ? 'Online' : (st.ollama_host ? 'Online' : '—');

  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    <div class="flex justify-between items-end mb-6">
      <div>
        <h2 class="text-headline-md font-headline-md text-primary">Network Overview</h2>
        <p class="text-body-md text-on-surface-variant">Real-time status of autonomous agents and campus infrastructure.</p>
      </div>
    </div>
    <div class="grid grid-cols-4 gap-6 mb-6">
      ${statCardHtml('LLM MODEL', esc(st.model || '—'), '')}
      ${statCardHtml('OLLAMA', ollamaTxt, '', 'green')}
      ${statCardHtml('SKILLS', st.skills_loaded != null ? st.skills_loaded : '—', '')}
      ${statCardHtml('AGENTS', String(agentCount), agentCount ? `${agentCount} loaded` : '')}
    </div>
    ${cardHtml('Agent Registry', `<div class="flex gap-3 overflow-x-auto pb-2">${agentCards}</div>`)}
    <div class="grid grid-cols-2 gap-6 mt-6">
      ${cardHtml('Router Health', `
        <table class="w-full text-left">
          <thead class="bg-surface-container-low"><tr>
            <th class="px-4 py-2 text-label-caps font-label-caps text-outline">ROUTER</th>
            <th class="px-4 py-2 text-label-caps font-label-caps text-outline">HOST</th>
            <th class="px-4 py-2 text-label-caps font-label-caps text-outline">STATUS</th>
          </tr></thead>
          <tbody class="divide-y divide-outline-variant text-body-sm">${routerRowsHtml}</tbody>
        </table>
        <p class="text-[11px] text-on-surface-variant mt-3">${esc(routerNote)}</p>
      `)}
      ${cardHtml('Quick Actions', `
        <div class="grid grid-cols-2 gap-3">
          <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
            <span class="material-symbols-outlined text-lg">health_and_safety</span>Health Check</button>
          <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
            <span class="material-symbols-outlined text-lg">shield</span>Security Audit</button>
          <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
            <span class="material-symbols-outlined text-lg">backup</span>Backup All</button>
          <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
            <span class="material-symbols-outlined text-lg">router</span>DHCP Audit</button>
        </div>
      `)}
    </div>
  </div>`;
}
