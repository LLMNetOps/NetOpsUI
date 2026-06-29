export function icon(name, cls = '') {
  return `<span class="material-symbols-outlined ${cls}">${name}</span>`
}

export function statusBadge(label, variant = 'green') {
  const colors = {
    green:  'bg-green-50 text-green-700 border-green-100',
    amber:  'bg-amber-50 text-amber-700 border-amber-100',
    red:    'bg-red-50 text-red-700 border-red-100',
    blue:   'bg-blue-50 text-blue-700 border-blue-100',
    gray:   'bg-surface-container text-on-surface-variant border-outline-variant',
  }
  const c = colors[variant] || colors.gray
  return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-label-caps font-label-caps font-bold border rounded-full ${c}">${label}</span>`
}

export function statCard(label, value, trend = '', trendColor = 'green') {
  const tc = trendColor === 'red' ? 'text-red-600' : 'text-green-600'
  return `
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
      <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">${label}</p>
      <div class="flex items-baseline gap-2">
        <span class="text-display-lg font-display-lg text-primary">${value}</span>
        ${trend ? `<span class="text-data-mono-sm font-data-mono-sm ${tc}">${trend}</span>` : ''}
      </div>
    </div>`
}

export function card(title, content, headerRight = '') {
  return `
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm">
      <div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
        <h3 class="text-title-sm font-title-sm font-bold text-primary">${title}</h3>
        ${headerRight}
      </div>
      <div class="p-6">${content}</div>
    </div>`
}

export function agentCard(alias, role, state, detail = '') {
  const stateColors = {
    standby:  { dot: 'bg-gray-300',   text: 'text-on-surface-variant', label: 'STANDBY',  border: '' },
    running:  { dot: 'bg-green-500',  text: 'text-green-700',          label: 'RUNNING',  border: 'border-l-green-500' },
    waiting:  { dot: 'bg-amber-500',  text: 'text-amber-700',          label: 'WAITING',  border: 'border-l-amber-500' },
    done:     { dot: 'bg-gray-400',   text: 'text-on-surface-variant', label: 'DONE',     border: '' },
    failed:   { dot: 'bg-red-500',    text: 'text-red-700',            label: 'FAILED',   border: 'border-l-red-500' },
    nonaktif: { dot: 'bg-gray-200',   text: 'text-on-surface-variant', label: 'DISABLED', border: '' },
  }
  const s = stateColors[state] || stateColors.standby
  const pulse = state === 'running' ? 'pulse-green' : ''
  return `
    <div class="bg-surface-container-lowest border border-outline-variant ${s.border ? 'border-l-[3px] ' + s.border : ''} rounded-lg p-3 transition-all">
      <div class="flex justify-between items-center">
        <div>
          <span class="text-xs font-bold uppercase text-primary">${alias}</span>
          <span class="text-[10px] text-on-surface-variant ml-1">${role}</span>
        </div>
        <div class="flex items-center gap-1.5">
          <span class="w-2 h-2 rounded-full ${s.dot} ${pulse}"></span>
          <span class="text-label-caps font-label-caps ${s.text}">${s.label}</span>
        </div>
      </div>
      ${detail ? `<p class="text-[10px] text-on-surface-variant font-data-mono-sm mt-1 truncate">${escapeHtml(detail)}</p>` : ''}
    </div>`
}

export function escapeHtml(str) {
  const d = document.createElement('div')
  d.textContent = str
  return d.innerHTML
}

export function formatTime(date) {
  const d = date || new Date()
  const pad = n => String(n).padStart(2, '0')
  return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
