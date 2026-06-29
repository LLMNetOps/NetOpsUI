import { store, AGENTS } from '../store.js'
import { fetchInfo } from '../api.js'
import { statCard, card, statusBadge, agentCard } from '../components.js'

export function mount(container) {
  loadData()
  render(container)
}

async function loadData() {
  try {
    store.systemStatus = await fetchInfo()
  } catch { /* offline */ }
}

function render(container) {
  const status = store.systemStatus || {}

  const agentCards = AGENTS.map(a =>
    `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-3 shadow-sm text-center min-w-[120px]">
      <span class="material-symbols-outlined text-2xl text-primary mb-1">${a.icon}</span>
      <p class="text-xs font-bold uppercase text-primary">${a.alias}</p>
      <p class="text-[10px] text-on-surface-variant">${a.role}</p>
    </div>`
  ).join('')

  container.innerHTML = `
    <div class="p-6 max-w-[1600px] mx-auto">
      <!-- Page Header -->
      <div class="flex justify-between items-end mb-6">
        <div>
          <h2 class="text-headline-md font-headline-md text-primary">Network Overview</h2>
          <p class="text-body-md text-on-surface-variant">Real-time status of autonomous agents and campus infrastructure.</p>
        </div>
      </div>

      <!-- Stats Row -->
      <div class="grid grid-cols-4 gap-6 mb-6">
        ${statCard('LLM MODEL', status.model || '...', '')}
        ${statCard('OLLAMA', status.ollama_host ? 'Online' : '...', '', 'green')}
        ${statCard('SKILLS LOADED', status.skills_loaded || '...', '')}
        ${statCard('AGENTS', '8', '7 active')}
      </div>

      <!-- Agent Registry -->
      ${card('Agent Registry', `
        <div class="flex gap-3 overflow-x-auto pb-2">${agentCards}</div>
      `)}

      <!-- Bottom Row -->
      <div class="grid grid-cols-2 gap-6 mt-6">
        <!-- Router Health -->
        ${card('Router Health', `
          <table class="w-full text-left">
            <thead class="bg-surface-container-low">
              <tr>
                <th class="px-4 py-2 text-label-caps font-label-caps text-outline">ROUTER</th>
                <th class="px-4 py-2 text-label-caps font-label-caps text-outline">HOST</th>
                <th class="px-4 py-2 text-label-caps font-label-caps text-outline">STATUS</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-outline-variant text-body-sm">
              <tr><td class="px-4 py-2 font-medium">—</td><td class="px-4 py-2 font-data-mono text-data-mono">—</td><td class="px-4 py-2">${statusBadge('PENDING', 'gray')}</td></tr>
            </tbody>
          </table>
          <p class="text-[11px] text-on-surface-variant mt-3">Connect to backend to load router data.</p>
        `)}

        <!-- Quick Actions -->
        ${card('Quick Actions', `
          <div class="grid grid-cols-2 gap-3">
            <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
              <span class="material-symbols-outlined text-lg">health_and_safety</span>
              Health Check
            </button>
            <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
              <span class="material-symbols-outlined text-lg">shield</span>
              Security Audit
            </button>
            <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
              <span class="material-symbols-outlined text-lg">backup</span>
              Backup All
            </button>
            <button onclick="location.hash='chat'" class="flex items-center gap-2 px-4 py-3 bg-surface-container-lowest border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors text-body-sm font-medium text-primary">
              <span class="material-symbols-outlined text-lg">router</span>
              DHCP Audit
            </button>
          </div>
        `)}
      </div>
    </div>`
}
