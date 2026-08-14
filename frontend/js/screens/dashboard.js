import { $, esc, badge, cardHtml, pageHeader, loadingHtml, errorHtml, fmtFullDateTime } from '../utils.js';
import { apiGet, apiPost } from '../api.js';

function timeAgo(iso) {
  if (!iso) return null;
  const d = new Date(iso);
  if (isNaN(d)) return null;
  const diffSec = Math.max(0, Math.floor((Date.now() - d.getTime()) / 1000));
  if (diffSec < 60) return `${diffSec}d lalu`;
  const diffMin = Math.floor(diffSec / 60);
  if (diffMin < 60) return `${diffMin} menit lalu`;
  const diffH = Math.floor(diffMin / 60);
  if (diffH < 24) return `${diffH} jam lalu`;
  return `${Math.floor(diffH / 24)} hari lalu`;
}

function emptyBody(msg) {
  return `<div class="h-full flex items-center justify-center"><p class="text-body-sm text-on-surface-variant text-center">${msg}</p></div>`;
}

const OUTCOME_BADGE = {
  executed: ['DIEKSEKUSI', 'green'],
  rejected: ['DITOLAK', 'amber'],
  error: ['ERROR', 'red'],
  unknown: ['?', 'gray'],
};

export async function screenDashboard(c) {
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    ${pageHeader(
      'Network Overview',
      'Ringkasan kondisi agent, node, dan aktivitas operator saat ini. Klik Refresh untuk memuat ulang data — status node hanya berubah saat dicek manual lewat tombol refresh di card Nodes.',
      `<button id="btn-dash-refresh" class="flex items-center gap-2 px-4 py-2 border border-outline-variant rounded-lg text-body-sm font-medium text-primary hover:bg-surface-container-low transition-colors">
        <span class="material-symbols-outlined text-lg">refresh</span>Refresh
      </button>`
    )}
    <div id="dash-body">${loadingHtml('Memuat dashboard...')}</div>
  </div>`;

  $('btn-dash-refresh').onclick = loadDashboard;
  await loadDashboard();
}

async function loadDashboard() {
  const body = $('dash-body');
  const btn = $('btn-dash-refresh');
  if (btn) { btn.disabled = true; btn.querySelector('.material-symbols-outlined').classList.add('animate-spin'); }
  try {
    const d = await apiGet('/api/dashboard');
    body.innerHTML = renderDashboard(d);
    bindDashboardEvents();
  } catch (e) {
    body.innerHTML = errorHtml('Gagal memuat dashboard: ' + e.message);
  } finally {
    if (btn) { btn.disabled = false; btn.querySelector('.material-symbols-outlined').classList.remove('animate-spin'); }
  }
}

function renderDashboard(d) {
  return `
    <div class="grid grid-cols-4 gap-6 mb-6">
      ${statLLM(d.llm)}
      ${statAgents(d.agents)}
      ${statSkills(d.skills)}
      ${statNodes(d.nodes)}
    </div>
    ${actionZoneHtml(d)}
    <div class="grid grid-cols-2 gap-6 mb-6">
      ${recentThreadsHtml(d.threads_recent)}
      ${recentWritesHtml(d.recent_writes)}
    </div>
    <div class="grid grid-cols-2 gap-6">
      ${backupsHtml(d.backups)}
      ${reportsHtml(d.reports)}
    </div>
  `;
}

function statCard(label, body) {
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
    <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">${label}</p>
    ${body}
  </div>`;
}

function statLLM(llm) {
  const model = llm?.model || '—';
  const health = llm?.health || {};

  if (!health.sample_size) {
    return statCard('LLM', `
      <p class="text-title-sm font-title-sm text-on-surface-variant">Belum ada panggilan tercatat</p>
      <p class="text-[10px] text-on-surface-variant truncate mt-1" title="${esc(model)}">Model aktif: ${esc(model)}</p>
    `);
  }
  if (!health.telemetry_available) {
    return statCard('LLM', `
      <p class="text-body-md font-medium text-on-surface-variant">Model tidak melaporkan jumlah token</p>
      <p class="text-[10px] text-on-surface-variant truncate mt-1" title="${esc(model)}">${esc(model)} &middot; pemakaian context tidak bisa dihitung dari ${health.sample_size} panggilan terakhir</p>
    `);
  }
  const ctx = health.avg_ctx_util;
  const color = ctx >= 85 ? 'text-red-600' : ctx >= 70 ? 'text-amber-600' : 'text-primary';
  const trunc = health.truncated_count || 0;
  return statCard('LLM &middot; PEMAKAIAN CONTEXT', `
    <div class="flex items-baseline gap-2">
      <span class="text-display-lg font-display-lg ${color}">${ctx}%</span>
      ${trunc > 0 ? `<span class="material-symbols-outlined text-[16px] text-red-600" title="${trunc} dari ${health.sample_size} respons terakhir terpotong karena context window penuh">warning</span>` : ''}
    </div>
    <p class="text-[10px] text-on-surface-variant truncate mt-1" title="${esc(model)}">${esc(model)} &middot; rata-rata dari ${health.sample_size} panggilan terakhir</p>
  `);
}

function statAgents(agents) {
  const total = agents?.total || 0, enabled = agents?.enabled || 0;
  return statCard('AGENTS', `
    <p class="text-display-lg font-display-lg text-primary">${enabled}<span class="text-body-md text-on-surface-variant">/${total}</span></p>
    <p class="text-[10px] text-on-surface-variant mt-1">aktif</p>
  `);
}

function statSkills(skills) {
  const total = skills?.total || 0, enabled = skills?.enabled || 0, pending = skills?.pending || 0;
  return statCard('SKILLS', `
    <p class="text-display-lg font-display-lg text-primary">${enabled}<span class="text-body-md text-on-surface-variant">/${total}</span></p>
    <p class="text-[10px] mt-1">${pending > 0 ? badge(`${pending} PENDING`, 'amber') : '<span class="text-on-surface-variant">tidak ada pending</span>'}</p>
  `);
}

function statNodes(nodes) {
  const total = nodes?.total || 0, reachable = nodes?.reachable || 0, down = nodes?.down || 0, unknown = nodes?.unknown || 0;
  const ago = timeAgo(nodes?.last_checked);
  const freshness = ago ? `dicek ${ago}` : 'belum pernah dicek';
  const detail = down > 0
    ? `<span class="text-red-600">${down} down</span>`
    : unknown > 0 ? `<span class="text-amber-600">${unknown} belum dicek</span>` : `<span class="text-green-600">semua up</span>`;
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
    <div class="flex justify-between items-center mb-1">
      <p class="font-label-caps text-label-caps text-on-surface-variant">NODES</p>
      <button id="btn-refresh-nodes" title="Cek reachability semua router sekarang" class="material-symbols-outlined text-[16px] leading-none text-on-surface-variant hover:text-primary hover:bg-surface-container rounded p-0.5 transition-colors">refresh</button>
    </div>
    <p class="text-display-lg font-display-lg text-primary">${reachable}<span class="text-body-md text-on-surface-variant">/${total}</span></p>
    <p class="text-[10px] mt-1">${detail} &middot; <span class="text-on-surface-variant">${freshness}</span></p>
  </div>`;
}

function actionItem(icon, text, hash, color = 'text-amber-700') {
  return `<div data-goto="${esc(hash)}" class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
    <span class="material-symbols-outlined text-[18px] ${color}">${icon}</span>
    <span class="text-body-sm text-on-surface flex-1">${text}</span>
    <span class="material-symbols-outlined text-[16px] text-on-surface-variant">chevron_right</span>
  </div>`;
}

function actionZoneHtml(d) {
  const items = [];
  for (const s of d.skills_pending_list || []) {
    items.push(actionItem('psychology', `Skill <b>${esc(s)}</b> menunggu persetujuan`, 'skills'));
  }
  for (const n of (d.nodes?.list || []).filter(n => n.status === 'down')) {
    items.push(actionItem('error', `Router <b>${esc(n.name)}</b> down — tidak merespons ping`, 'nodes', 'text-red-700'));
  }
  for (const r of d.backups?.never_backed_up || []) {
    items.push(actionItem('backup', `<b>${esc(r)}</b> belum pernah di-backup sama sekali`, 'backups'));
  }
  const staleDays = d.backups?.stale_threshold_days || 7;
  for (const s of d.backups?.stale || []) {
    items.push(actionItem('schedule', `Backup <b>${esc(s.router)}</b> sudah ${s.age_days} hari (lebih dari ${staleDays} hari, sebaiknya di-backup ulang)`, 'backups'));
  }

  if (items.length === 0) return '';

  const shown = items.slice(0, 8);
  const more = items.length > 8 ? `<p class="text-[11px] text-on-surface-variant px-4 pt-1">+${items.length - 8} lainnya</p>` : '';
  return `<div class="mb-6">
    ${cardHtml('Perlu Tindakan', `<div class="-m-6 divide-y divide-outline-variant">${shown.join('')}</div>${more}`)}
  </div>`;
}

function recentThreadsHtml(threads) {
  if (!threads || threads.length === 0) {
    return cardHtml('Thread Terakhir', emptyBody('Belum ada percakapan.'));
  }
  const rows = threads.map(t => `
    <div data-goto="chat/${esc(t.thread_id)}" class="px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <div class="flex justify-between items-baseline gap-2">
        <span class="text-body-sm font-medium text-primary truncate">${esc(t.title)}</span>
        <span class="text-[10px] text-outline tabular-nums shrink-0">${esc(fmtFullDateTime(t.updated_at))}</span>
      </div>
      <p class="text-[11px] text-on-surface-variant truncate mt-0.5">${esc(t.last_message || '—')}</p>
    </div>`).join('');
  return cardHtml('Thread Terakhir', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function recentWritesHtml(writes) {
  if (!writes || writes.length === 0) {
    return cardHtml('Operasi Write Terakhir', emptyBody('Belum ada operasi write (backup/config) yang tercatat.'));
  }
  const rows = writes.map(w => {
    const [label, color] = OUTCOME_BADGE[w.outcome] || OUTCOME_BADGE.unknown;
    return `<div data-goto="chat/${esc(w.thread_id)}" class="px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <div class="flex justify-between items-center gap-2">
        <span class="font-data-mono-sm text-data-mono-sm text-on-surface truncate" title="${esc(w.action)}">${esc(w.action)}</span>
        ${badge(label, color)}
      </div>
      <p class="text-[10px] text-on-surface-variant mt-1">${esc(w.agent || '—')} &middot; ${esc(w.thread_title)} &middot; ${esc(w.time || '—')}</p>
    </div>`;
  }).join('');
  return cardHtml('Operasi Write Terakhir', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function backupsHtml(backups) {
  const recent = backups?.recent || [];
  if (recent.length === 0) {
    return cardHtml('Backup Terbaru', emptyBody('Belum ada backup tersimpan.'));
  }
  const rows = recent.map(b => `
    <div class="flex justify-between items-center px-4 py-2 text-body-sm">
      <span class="font-medium text-primary">${esc(b.router)}</span>
      <span class="text-[11px] text-on-surface-variant font-data-mono-sm">${esc(fmtFullDateTime(b.mtime))} &middot; ${b.age_days} hari lalu</span>
    </div>`).join('');
  return cardHtml('Backup Terbaru', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function reportsHtml(reports) {
  if (!reports || reports.length === 0) {
    return cardHtml('Laporan Terbaru', emptyBody('Belum ada laporan.'));
  }
  const rows = reports.map(r => `
    <div class="flex justify-between items-center px-4 py-2 text-body-sm">
      <span class="text-primary truncate max-w-[70%]" title="${esc(r.filename)}">${esc(r.filename)}</span>
      <span class="text-[11px] text-on-surface-variant">${r.size_kb} KB</span>
    </div>`).join('');
  return cardHtml('Laporan Terbaru', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function bindDashboardEvents() {
  document.querySelectorAll('[data-goto]').forEach(el => {
    el.onclick = () => { location.hash = el.dataset.goto; };
  });
  const btnNodes = $('btn-refresh-nodes');
  if (btnNodes) {
    btnNodes.onclick = async (e) => {
      e.stopPropagation();
      btnNodes.disabled = true;
      btnNodes.classList.add('animate-spin');
      try { await apiPost('/api/tools/reachability/all', {}); } catch { /* keep last known state */ }
      await loadDashboard();
    };
  }
}
