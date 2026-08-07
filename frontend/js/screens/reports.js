import { apiGet } from '../api.js';
import { $, esc, pageHeader, loadingHtml, errorHtml } from '../utils.js';

export async function screenReports(c) {
  c.innerHTML = `<div class="p-container_gutter max-w-[1600px] mx-auto">
    ${pageHeader('Reports', 'Archive of generated network operation reports.', `
      <button id="rpt-refresh" class="px-4 py-2 bg-surface-container-lowest border border-outline-variant rounded text-primary font-body-md hover:bg-surface-container transition-colors flex items-center">
        <span class="material-symbols-outlined mr-2 text-sm">refresh</span> Refresh
      </button>`)}
    <div class="grid grid-cols-12 gap-stack_gap_lg">
      <div class="col-span-12 xl:col-span-4 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary">Archive</h3>
          <span id="rpt-count" class="text-label-caps font-label-caps text-on-surface-variant">—</span>
        </div>
        <div id="rpt-list" class="overflow-y-auto max-h-[600px]">${loadingHtml('Memuat laporan...')}</div>
      </div>
      <div class="col-span-12 xl:col-span-8 bg-surface-container-lowest border border-outline-variant rounded-lg overflow-hidden">
        <div class="px-6 py-4 border-b border-outline-variant flex justify-between items-center">
          <h3 class="font-title-sm text-title-sm text-primary" id="rpt-viewer-title">Pilih laporan</h3>
          <button id="rpt-download" class="hidden px-3 py-1.5 bg-surface-container-lowest border border-outline-variant rounded text-label-caps font-label-caps text-primary hover:bg-surface-container transition-colors flex items-center gap-1">
            <span class="material-symbols-outlined text-sm">download</span> Unduh
          </button>
        </div>
        <div id="rpt-viewer" class="p-6 min-h-[400px] text-on-surface-variant text-body-sm">
          <p>Klik laporan di sebelah kiri untuk melihat isinya.</p>
        </div>
      </div>
    </div>
  </div>`;

  let _reports = [];

  async function loadList() {
    const el = $('rpt-list');
    const cntEl = $('rpt-count');
    if (!el) return;
    try {
      const r = await apiGet('/api/reports');
      _reports = r.reports || [];
      if (cntEl) cntEl.textContent = `${_reports.length} file`;
      if (!_reports.length) {
        el.innerHTML = `<div class="px-6 py-8 text-center text-on-surface-variant text-body-sm">Belum ada laporan.</div>`;
        return;
      }
      el.innerHTML = _reports.map((rpt, idx) => `<button data-rpt="${idx}" class="w-full text-left flex items-start gap-3 px-5 py-3.5 border-b border-outline-variant hover:bg-surface-container-low transition-colors group">
        <span class="material-symbols-outlined text-primary text-[20px] mt-0.5 shrink-0">description</span>
        <div class="min-w-0">
          <p class="font-data-mono-sm text-data-mono-sm text-primary truncate">${esc(rpt.name || rpt.filename)}</p>
          <p class="text-label-caps font-label-caps text-on-surface-variant mt-0.5">${esc(rpt.date || rpt.created_at || '—')}</p>
        </div>
      </button>`).join('');
      el.querySelectorAll('[data-rpt]').forEach(btn => {
        btn.onclick = () => viewReport(_reports[parseInt(btn.dataset.rpt)]);
      });
    } catch (e) {
      el.innerHTML = errorHtml('Gagal memuat laporan: ' + e.message);
    }
  }

  async function viewReport(rpt) {
    const viewer = $('rpt-viewer');
    const titleEl = $('rpt-viewer-title');
    const dlBtn = $('rpt-download');
    if (!viewer) return;
    if (titleEl) titleEl.textContent = rpt.name || rpt.filename;
    viewer.innerHTML = loadingHtml('Memuat isi laporan...');
    try {
      const r = await apiGet(`/api/reports/${encodeURIComponent(rpt.name || rpt.filename)}`);
      const content = r.content || '';
      viewer.innerHTML = `<pre class="font-data-mono-sm text-data-mono-sm whitespace-pre-wrap text-on-surface-variant leading-relaxed">${esc(content)}</pre>`;
      if (dlBtn) {
        dlBtn.classList.remove('hidden');
        dlBtn.onclick = () => {
          const blob = new Blob([content], { type: 'text/markdown' });
          const a = document.createElement('a');
          a.href = URL.createObjectURL(blob);
          a.download = rpt.name || rpt.filename || 'laporan.md';
          a.click();
        };
      }
    } catch (e) {
      viewer.innerHTML = errorHtml('Gagal memuat isi laporan: ' + e.message);
    }
  }

  const refreshBtn = $('rpt-refresh');
  if (refreshBtn) refreshBtn.onclick = loadList;

  loadList();
}
