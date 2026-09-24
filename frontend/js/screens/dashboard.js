import { $, esc, cardHtml, pageHeader, loadingHtml, fmtFullDateTime, badge, alertDialog } from '../utils.js';
import { activeBackend } from '../backends/index.js';

function emptyBody(msg) {
  return `<div class="h-full flex items-center justify-center"><p class="text-body-sm text-on-surface-variant text-center">${msg}</p></div>`;
}

function statCard(label, body) {
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-4 shadow-sm">
    <p class="font-label-caps text-label-caps text-on-surface-variant mb-1">${label}</p>
    ${body}
  </div>`;
}

export async function screenDashboard(c) {
  const backend = activeBackend();
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    ${pageHeader(
      'Overview',
      `Ringkasan backend aktif (<b>${esc(backend.label)}</b>), pengecekan berkala, dan aktivitas agent.`,
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
  const backend = activeBackend();
  const body = $('dash-body');
  const btn = $('btn-dash-refresh');
  if (btn) { btn.disabled = true; btn.querySelector('.material-symbols-outlined').classList.add('animate-spin'); }

  const cap = backend.capabilities;
  // Each source fails independently so one unreachable endpoint doesn't blank the page.
  // Capability-gated sources resolve to null when the backend doesn't offer them.
  const [health, threads, skills, jobs, devices, activity] = await Promise.allSettled([
    backend.health(), backend.listThreads(), backend.listSkills(),
    cap.jobs ? backend.listJobs() : null,
    cap.devices ? backend.listDevices() : null,
    cap.activity ? backend.listActivity() : null,
  ]);

  if (body) body.innerHTML = `
    <div class="grid grid-cols-4 gap-6 mb-6">
      ${statBackend(backend, health)}
      ${statModel(health)}
      ${cap.jobs ? statJobs(jobs) : cap.devices ? statCount('PERANGKAT', devices, 'terdaftar di inventori') : statCount('THREADS', threads, 'tersimpan di server')}
      ${statCount('SKILLS', skills, 'terpasang')}
    </div>
    <div class="grid grid-cols-2 gap-6 ${activity.value ? 'mb-6' : ''}">
      ${cap.jobs ? jobsHtml(jobs) : cap.devices ? devicesHtml(devices) : ''}
      ${recentThreadsHtml(threads)}
    </div>
    ${cap.activity ? activityHtml(activity) : ''}`;
  bindJobActions(backend);
  document.querySelectorAll('[data-goto]').forEach(el => {
    el.onclick = () => { location.hash = el.dataset.goto; };
  });
  if (btn) { btn.disabled = false; btn.querySelector('.material-symbols-outlined').classList.remove('animate-spin'); }
}

function statBackend(backend, health) {
  const ok = health.status === 'fulfilled' && health.value.ok;
  const [dot, text] = health.status === 'rejected'
    ? ['bg-red-500', 'tidak terjangkau']
    : ok ? ['bg-green-500', 'terhubung'] : ['bg-amber-500', 'status tidak OK'];
  const title = health.status === 'rejected' ? health.reason.message : '';
  return statCard('BACKEND', `
    <p class="text-title-sm font-title-sm text-primary">${esc(backend.label)}</p>
    <p class="text-[11px] mt-1 flex items-center gap-1.5" title="${esc(title)}"><span class="w-2 h-2 rounded-full ${dot}"></span>${text}</p>`);
}

function statModel(health) {
  const h = health.status === 'fulfilled' ? health.value : null;
  return statCard('MODEL', `
    <p class="text-title-sm font-title-sm text-primary truncate" title="${esc(h?.model || '')}">${esc(h?.model || '—')}</p>
    <p class="text-[11px] text-on-surface-variant mt-1 truncate" title="${esc(h?.detail || '')}">${esc(h?.detail || '')}</p>`);
}

function statCount(label, result, caption) {
  if (result.status === 'rejected') {
    return statCard(label, `<p class="text-display-lg font-display-lg text-outline">—</p>
      <p class="text-[11px] text-red-700 mt-1 truncate" title="${esc(result.reason.message)}">gagal dimuat</p>`);
  }
  return statCard(label, `<p class="text-display-lg font-display-lg text-primary">${result.value.length}</p>
    <p class="text-[11px] text-on-surface-variant mt-1">${caption}</p>`);
}

function recentThreadsHtml(threads) {
  if (threads.status === 'rejected') {
    return cardHtml('Thread Terakhir', emptyBody('Gagal memuat thread: ' + esc(threads.reason.message)));
  }
  const list = threads.value.slice(0, 8);
  if (!list.length) return cardHtml('Thread Terakhir', emptyBody('Belum ada percakapan.'));
  const rows = list.map(t => `
    <div data-goto="chat/${esc(t.id)}" class="px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <div class="flex justify-between items-baseline gap-2">
        <span class="text-body-sm font-medium text-primary truncate">${esc(t.title)}</span>
        <span class="text-[10px] text-outline tabular-nums shrink-0">${esc(fmtFullDateTime(t.updatedAt))}</span>
      </div>
      <p class="text-[11px] text-on-surface-variant truncate mt-0.5">${esc(t.lastMessage || '—')}</p>
    </div>`).join('');
  return cardHtml('Thread Terakhir', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}</div>`);
}

function failedMsg(what, r) {
  return cardHtml(what, emptyBody('Gagal memuat: ' + esc(r.reason.message)));
}

function isPaused(j) { return j.enabled === false || j.state === 'paused'; }
function isFailing(j) { return j.last_status === 'error' || j.state === 'error'; }

function statJobs(r) {
  if (r.status === 'rejected') return statCount('JOB TERJADWAL', r, '');
  const jobs = r.value;
  const active = jobs.filter(j => !isPaused(j)).length;
  const failing = jobs.filter(isFailing).length;
  const cap = !jobs.length ? 'belum ada job terjadwal' : failing
    ? `<span class="text-red-700 font-medium">${failing} gagal</span> pada eksekusi terakhir`
    : 'aktif, eksekusi terakhir OK';
  return statCard('JOB TERJADWAL', `<p class="text-display-lg font-display-lg text-primary">${active}</p>
    <p class="text-[11px] text-on-surface-variant mt-1">${cap}</p>`);
}

function jobStatusBadge(j) {
  if (isPaused(j)) return badge('dijeda', 'gray');
  if (isFailing(j)) return badge('gagal', 'red');
  if (j.last_status) return badge('OK', 'green');
  return badge('belum jalan', 'gray');
}

function jobsHtml(r) {
  if (r.status === 'rejected') return failedMsg('Pengecekan Berkala', r);
  const jobs = r.value;
  if (!jobs.length) return cardHtml('Pengecekan Berkala', emptyBody('Belum ada job terjadwal. Buat lewat Hermes (cron).'));
  const btn = 'px-2 py-1 border border-outline-variant rounded text-[11px] text-primary hover:bg-surface-container-low transition-colors';
  const rows = jobs.map(j => `
    <tr class="border-t border-outline-variant align-top">
      <td class="px-4 py-2.5">
        <p class="text-body-sm font-medium text-primary">${esc(j.name || j.id)}</p>
        <p class="text-[11px] text-on-surface-variant">${esc(j.schedule_display || '')}</p>
        ${isFailing(j) && j.last_error ? `<p class="text-[11px] text-red-700 truncate max-w-[280px]" title="${esc(j.last_error)}">${esc(j.last_error)}</p>` : ''}
      </td>
      <td class="px-4 py-2.5">${jobStatusBadge(j)}</td>
      <td class="px-4 py-2.5 text-[11px] text-on-surface-variant tabular-nums">${j.last_run_at ? esc(fmtFullDateTime(j.last_run_at)) : '—'}</td>
      <td class="px-4 py-2.5 text-[11px] text-on-surface-variant tabular-nums">${!isPaused(j) && j.next_run_at ? esc(fmtFullDateTime(j.next_run_at)) : '—'}</td>
      <td class="px-4 py-2.5 text-right whitespace-nowrap">
        <button class="${btn}" data-job="run" data-id="${esc(j.id)}">Jalankan</button>
        <button class="${btn}" data-job="${isPaused(j) ? 'resume' : 'pause'}" data-id="${esc(j.id)}">${isPaused(j) ? 'Lanjutkan' : 'Jeda'}</button>
      </td>
    </tr>`).join('');
  return cardHtml('Pengecekan Berkala', `<div class="-m-6 overflow-x-auto"><table class="w-full text-left">
    <thead><tr class="font-label-caps text-label-caps text-on-surface-variant">
      <th class="px-4 py-2">JOB</th><th class="px-4 py-2">STATUS</th><th class="px-4 py-2">TERAKHIR</th><th class="px-4 py-2">BERIKUTNYA</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table></div>`);
}

function bindJobActions(backend) {
  document.querySelectorAll('[data-job]').forEach(el => {
    el.onclick = async () => {
      el.disabled = true;
      try {
        const fn = { run: 'runJob', pause: 'pauseJob', resume: 'resumeJob' }[el.dataset.job];
        await backend[fn](el.dataset.id);
      } catch (e) {
        alertDialog(e.message);
      }
      loadDashboard();
    };
  });
}

function devicesHtml(r) {
  if (r.status === 'rejected') return failedMsg('Perangkat', r);
  const list = r.value;
  if (!list.length) return cardHtml('Perangkat', emptyBody('Belum ada perangkat terdaftar.'));
  const rows = list.slice(0, 10).map(d => `
    <div data-goto="nodes" class="flex items-center gap-3 px-4 py-2.5 hover:bg-surface-container-low rounded-lg cursor-pointer transition-colors">
      <span class="material-symbols-outlined text-[18px] text-outline">router</span>
      <div class="flex-1 min-w-0">
        <p class="text-body-sm font-medium text-primary truncate">${esc(d.name)}</p>
        <p class="text-[11px] text-on-surface-variant font-mono">${esc(d.mgmt_ip)}</p>
      </div>
      <span class="text-[11px] text-on-surface-variant">${esc(d.role || '')}${d.network_type ? ' · ' + esc(d.network_type) : ''}</span>
    </div>`).join('');
  const more = list.length > 10 ? `<p class="px-4 py-2 text-[11px] text-outline">+${list.length - 10} lainnya di halaman Nodes</p>` : '';
  return cardHtml('Perangkat', `<div class="-m-6 py-2 divide-y divide-outline-variant">${rows}${more}</div>`);
}

function activityHtml(r) {
  if (r.status === 'rejected') return failedMsg('Aktivitas Agent', r);
  const turns = r.value;
  if (!turns.length) return cardHtml('Aktivitas Agent', emptyBody('Belum ada aktivitas tercatat. Pastikan <code>memory.trace_path</code> diisi di config NetOps Agent.'));
  const calls = turns.reduce((n, t) => n + t.toolCalls, 0);
  const errs = turns.reduce((n, t) => n + t.errors + t.timeouts, 0);
  const rate = calls ? Math.round((errs / calls) * 100) : 0;
  const stat = (label, val) => `<div><p class="font-label-caps text-label-caps text-on-surface-variant">${label}</p>
    <p class="text-title-sm font-title-sm text-primary">${val}</p></div>`;
  const rows = turns.slice(0, 8).map(t => `
    <div class="flex items-center gap-3 px-4 py-2 text-body-sm">
      <span class="text-[10px] text-outline tabular-nums shrink-0 w-28">${esc(fmtFullDateTime(t.at))}</span>
      <span class="flex-1 truncate text-on-surface">${esc(t.message || '—')}</span>
      <span class="text-[11px] text-on-surface-variant tabular-nums shrink-0">${t.toolCalls} tool · ${t.durationS.toFixed(1)}s</span>
      ${t.errors + t.timeouts ? badge(`${t.errors + t.timeouts} error`, 'red') : ''}
    </div>`).join('');
  return cardHtml(`Aktivitas Agent <span class="font-normal text-on-surface-variant text-body-sm">(${turns.length} turn terakhir)</span>`, `
    <div class="flex gap-10 mb-4">${stat('TURN', turns.length)}${stat('TOOL CALL', calls)}${stat('ERROR / TIMEOUT', `${errs} (${rate}%)`)}</div>
    <div class="-mx-6 -mb-6 border-t border-outline-variant divide-y divide-outline-variant">${rows}</div>`);
}
