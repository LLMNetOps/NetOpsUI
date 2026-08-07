export function esc(str) {
  const d = document.createElement('div');
  d.textContent = str;
  return d.innerHTML;
}

export function fmtTime(date) {
  const d = date || new Date();
  const pad = n => String(n).padStart(2, '0');
  return pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
}

export function $(id) { return document.getElementById(id); }

export function badge(label, v = 'green') {
  const c = {
    green: 'bg-green-50 text-green-700 border-green-100',
    amber: 'bg-amber-50 text-amber-700 border-amber-100',
    red:   'bg-red-50 text-red-700 border-red-100',
    blue:  'bg-blue-50 text-blue-700 border-blue-100',
    gray:  'bg-surface-container text-on-surface-variant border-outline-variant',
  }[v] || 'bg-surface-container text-on-surface-variant border-outline-variant';
  return `<span class="inline-flex items-center gap-1 px-2 py-0.5 text-label-caps font-label-caps font-bold border rounded-full ${c}">${label}</span>`;
}

export function agentCardHtml(alias, role, state, detail) {
  const styles = {
    standby: { dot: 'bg-gray-300',  text: 'text-on-surface-variant', label: 'STANDBY', bl: '' },
    running: { dot: 'bg-green-500', text: 'text-green-700',          label: 'RUNNING', bl: 'border-l-[3px] border-l-green-500' },
    waiting: { dot: 'bg-amber-500', text: 'text-amber-700',          label: 'WAITING', bl: 'border-l-[3px] border-l-amber-500' },
    done:    { dot: 'bg-gray-400',  text: 'text-on-surface-variant', label: 'DONE',    bl: '' },
    failed:  { dot: 'bg-red-500',   text: 'text-red-700',            label: 'FAILED',  bl: 'border-l-[3px] border-l-red-500' },
  };
  const st = styles[state] || styles.standby;
  const pulse = state === 'running' ? 'pulse-green' : '';
  return `<div class="bg-surface-container-lowest border border-outline-variant ${st.bl} rounded-lg p-3 transition-all">
    <div class="flex justify-between items-center">
      <div><span class="text-xs font-bold uppercase text-primary">${alias}</span>
      <span class="text-[10px] text-on-surface-variant ml-1">${role}</span></div>
      <div class="flex items-center gap-1.5">
        <span class="w-2 h-2 rounded-full ${st.dot} ${pulse}"></span>
        <span class="text-label-caps font-label-caps ${st.text}">${st.label}</span>
      </div>
    </div>
    ${detail ? `<p class="text-[10px] text-on-surface-variant font-data-mono-sm mt-1 truncate">${esc(detail)}</p>` : ''}
  </div>`;
}

export function cardHtml(title, body, headerRight) {
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm">
    <div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant">
      <h3 class="text-title-sm font-title-sm font-bold text-primary">${title}</h3>
      ${headerRight || ''}
    </div>
    <div class="p-6">${body}</div>
  </div>`;
}

export function statCardHtml(label, value, trend, trendColor) {
  const tc = trendColor === 'red' ? 'text-red-600' : 'text-green-600';
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
    <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">${label}</p>
    <div class="flex items-baseline gap-2">
      <span class="text-display-lg font-display-lg text-primary">${value}</span>
      ${trend ? `<span class="text-data-mono-sm font-data-mono-sm ${tc}">${trend}</span>` : ''}
    </div>
  </div>`;
}

export function preHtml(text) {
  return `<pre class="font-data-mono text-data-mono text-sm whitespace-pre-wrap">${esc(text || '')}</pre>`;
}

export function resultCard(title, text, headerRight) {
  return cardHtml(title, preHtml(text), headerRight);
}

export function loadingHtml(msg = 'Loading...') {
  return `<div class="flex items-center justify-center gap-3 py-12 text-on-surface-variant">
    <span class="material-symbols-outlined animate-spin">progress_activity</span>
    <span class="text-body-sm">${esc(msg)}</span>
  </div>`;
}

export function errorHtml(msg) {
  return `<div class="flex items-center gap-2 px-4 py-2 mb-4 bg-red-50 border border-red-100 rounded-lg text-red-700 text-body-sm">
    <span class="material-symbols-outlined text-[18px]">error</span>
    <span>${esc(msg)}</span>
  </div>`;
}

export function pageHeader(title, subtitle, actions) {
  return `<div class="flex justify-between items-end mb-stack_gap_lg">
    <div>
      <h2 class="font-headline-md text-headline-md text-primary">${title}</h2>
      <p class="text-on-surface-variant text-body-md">${subtitle}</p>
    </div>
    ${actions ? `<div class="flex gap-stack_gap_md">${actions}</div>` : ''}
  </div>`;
}

export function parseRouterList(text) {
  if (!text) return [];
  const out = [];
  for (const raw of text.split('\n')) {
    const line = raw.trim();
    if (!line || line.startsWith('Router yang tersedia')) continue;
    const m = line.match(/^(\S+)\s+(\S+)\s+ROS\s+(v\d+)/i);
    if (!m) continue;
    const role = (line.match(/role=(\S+)/) || [])[1] || '';
    const servers = (line.split('servers:')[1] || '').trim();
    out.push({ name: m[1], host: m[2], ros: m[3], role, servers });
  }
  return out;
}
