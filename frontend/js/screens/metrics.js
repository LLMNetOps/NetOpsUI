import { apiGet } from '../api.js';
import { $, esc, pageHeader, loadingHtml, errorHtml, statCardHtml } from '../utils.js';
import { AGENTS } from '../config.js';

export async function screenMetrics(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Metrics', 'Token usage, tool call analytics, and per-agent performance.')}
    <div id="metrics-stats" class="grid grid-cols-4 gap-stack_gap_lg mb-stack_gap_lg">${loadingHtml('Memuat metrik...')}</div>
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-7 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Per-Agent Token Usage</h3>
          <span class="text-label-caps font-label-caps text-on-surface-variant">Session Total</span>
        </div>
        <div id="metrics-agent-table" class="overflow-x-auto">${loadingHtml()}</div>
      </div>
      <div class="col-span-12 xl:col-span-5 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant">
          <h3 class="font-title-sm text-title-sm text-primary">Tool Call Frequency</h3>
        </div>
        <div id="metrics-tools" class="p-6 overflow-y-auto max-h-[400px]">${loadingHtml()}</div>
      </div>
    </div>
  </div>`;

  async function loadMetrics() {
    const statsEl = $('metrics-stats');
    const tableEl = $('metrics-agent-table');
    const toolsEl = $('metrics-tools');

    try {
      const r = await apiGet('/api/metrics');
      const m = r.metrics || r || {};

      const totalTokens = m.total_tokens || 0;
      const totalCalls = m.total_tool_calls || 0;
      const sessions = m.total_sessions || 0;
      const avgTokens = sessions > 0 ? Math.round(totalTokens / sessions) : 0;

      if (statsEl) statsEl.innerHTML = `
        ${statCardHtml('TOTAL TOKENS', totalTokens.toLocaleString(), '', '')}
        ${statCardHtml('TOOL CALLS', totalCalls.toLocaleString(), '', '')}
        ${statCardHtml('SESSIONS', sessions.toLocaleString(), '', '')}
        ${statCardHtml('AVG TOKENS/SESSION', avgTokens.toLocaleString(), '', '')}`;

      const agentStats = m.agents || {};
      const agentRows = AGENTS.map(a => {
        const s = agentStats[a.name] || agentStats[a.alias] || {};
        const input = s.input_tokens || 0;
        const output = s.output_tokens || 0;
        const calls = s.tool_calls || 0;
        const total = input + output;
        return `<tr class="hover:bg-surface-container-low transition-colors border-b border-outline-variant">
          <td class="py-3 px-4 font-data-mono text-data-mono text-primary">${esc(a.alias)}</td>
          <td class="py-3 px-4 text-body-sm text-on-surface-variant">${esc(a.name)}</td>
          <td class="py-3 px-4 text-right font-data-mono-sm text-data-mono-sm">${input.toLocaleString()}</td>
          <td class="py-3 px-4 text-right font-data-mono-sm text-data-mono-sm">${output.toLocaleString()}</td>
          <td class="py-3 px-4 text-right font-data-mono-sm text-data-mono-sm font-medium ${total > 50000 ? 'text-red-700' : total > 20000 ? 'text-amber-700' : ''}">${total.toLocaleString()}</td>
          <td class="py-3 px-4 text-right font-data-mono-sm text-data-mono-sm">${calls}</td>
        </tr>`;
      }).join('');

      if (tableEl) tableEl.innerHTML = `<table class="w-full text-left border-collapse">
        <thead class="bg-surface-container-low"><tr class="text-label-caps font-label-caps text-outline border-b border-outline-variant">
          <th class="py-3 px-4">Alias</th><th class="py-3 px-4">Agent</th>
          <th class="py-3 px-4 text-right">Input</th><th class="py-3 px-4 text-right">Output</th>
          <th class="py-3 px-4 text-right">Total</th><th class="py-3 px-4 text-right">Calls</th>
        </tr></thead>
        <tbody>${agentRows}</tbody>
      </table>`;

      const toolFreq = m.tool_frequency || {};
      const sortedTools = Object.entries(toolFreq).sort((a, b) => b[1] - a[1]).slice(0, 20);
      const maxCount = sortedTools[0]?.[1] || 1;

      if (toolsEl) toolsEl.innerHTML = sortedTools.length
        ? sortedTools.map(([name, count]) => `<div class="flex items-center gap-3 mb-2.5">
            <span class="w-40 font-data-mono-sm text-data-mono-sm text-primary truncate shrink-0" title="${esc(name)}">${esc(name)}</span>
            <div class="flex-1 h-2 bg-surface-container-highest rounded-full overflow-hidden">
              <div class="h-full bg-primary" style="width:${Math.round(count / maxCount * 100)}%;"></div>
            </div>
            <span class="font-data-mono-sm text-data-mono-sm text-on-surface-variant w-8 text-right">${count}</span>
          </div>`).join('')
        : `<div class="text-body-sm text-on-surface-variant">Belum ada data tool calls.</div>`;

    } catch (e) {
      const msg = errorHtml('Gagal memuat metrik: ' + e.message);
      if (statsEl) statsEl.innerHTML = `<div class="col-span-4">${msg}</div>`;
      if (tableEl) tableEl.innerHTML = msg;
      if (toolsEl) toolsEl.innerHTML = msg;
    }
  }

  loadMetrics();
}
