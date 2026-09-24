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

const _SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'Mei', 'Jun', 'Jul', 'Agu', 'Sep', 'Okt', 'Nov', 'Des'];

export function fmtShortDate(date) {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d)) return '—';
  return `${d.getDate()} ${_SHORT_MONTHS[d.getMonth()]} ${d.getFullYear()}`;
}

export function fmtFullDateTime(date) {
  const d = date instanceof Date ? date : new Date(date);
  if (isNaN(d)) return '—';
  return `${fmtShortDate(d)} ${fmtTime(d)}`;
}

export function $(id) { return document.getElementById(id); }

// ── Generic confirm/alert dialog — replaces native window.confirm/alert ──────
// Appended straight to <body> (not a screen's container) so it works from any
// screen and survives screen re-renders. Returns a Promise<boolean>, same
// call shape as window.confirm() so call sites just add `await`.
export function confirmDialog({ title = 'Konfirmasi', message = '', confirmLabel = 'OK', cancelLabel = 'Batal', danger = false } = {}) {
  return new Promise(resolve => {
    const overlay = document.createElement('div');
    overlay.className = 'fixed inset-0 bg-black/30 backdrop-blur-sm z-[300] flex items-center justify-center';
    const cancelBtn = cancelLabel
      ? `<button data-act="cancel" class="px-4 py-2 border border-outline-variant text-on-surface-variant rounded-lg text-body-sm font-medium hover:bg-surface-container transition-colors">${esc(cancelLabel)}</button>`
      : '';
    overlay.innerHTML = `
      <div class="bg-surface-container-lowest rounded-xl shadow-xl max-w-[420px] w-full mx-4 overflow-hidden">
        <div class="p-6">
          <div class="flex items-center gap-2 mb-2">
            <span class="material-symbols-outlined ${danger ? 'text-red-600' : 'text-primary'}">${danger ? 'warning' : 'help'}</span>
            <h3 class="text-title-sm font-title-sm font-bold text-on-surface">${esc(title)}</h3>
          </div>
          <p class="text-body-sm text-on-surface-variant whitespace-pre-wrap">${esc(message)}</p>
        </div>
        <div class="px-6 pb-6 flex justify-end gap-3">
          ${cancelBtn}
          <button data-act="confirm" class="px-4 py-2 ${danger ? 'bg-red-700 hover:bg-red-800' : 'bg-primary hover:opacity-90'} text-white rounded-lg text-body-sm font-medium transition-colors">${esc(confirmLabel)}</button>
        </div>
      </div>`;

    function close(result) {
      document.removeEventListener('keydown', onKey);
      overlay.remove();
      resolve(result);
    }
    function onKey(e) {
      if (e.key === 'Escape') close(false);
      if (e.key === 'Enter') close(true);
    }

    overlay.addEventListener('click', e => { if (e.target === overlay) close(false); });
    const cancelEl = overlay.querySelector('[data-act="cancel"]');
    if (cancelEl) cancelEl.onclick = () => close(false);
    overlay.querySelector('[data-act="confirm"]').onclick = () => close(true);
    document.addEventListener('keydown', onKey);

    document.body.appendChild(overlay);
    overlay.querySelector('[data-act="confirm"]').focus();
  });
}

export function alertDialog(message, title = 'Perhatian') {
  return confirmDialog({ title, message, confirmLabel: 'OK', cancelLabel: null, danger: false });
}

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

export function cardHtml(title, body, headerRight) {
  return `<div class="bg-surface-container-lowest border border-outline-variant rounded-lg shadow-sm flex flex-col h-full">
    <div class="flex justify-between items-center px-6 py-4 border-b border-outline-variant shrink-0">
      <h3 class="text-title-sm font-title-sm font-bold text-primary">${title}</h3>
      ${headerRight || ''}
    </div>
    <div class="p-6 flex-1">${body}</div>
  </div>`;
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

export async function copyToClipboard(text) {
  if (navigator.clipboard && window.isSecureContext) {
    try { await navigator.clipboard.writeText(text); return true; } catch { /* fall through to legacy path */ }
  }
  try {
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.focus(); ta.select();
    const ok = document.execCommand('copy');
    document.body.removeChild(ta);
    return ok;
  } catch { return false; }
}

// ── Minimal markdown renderer for agent chat responses ───────────────────────
// Escape-first design: every chunk of raw text is passed through esc() before
// any HTML tag is added, so the only HTML in the output is tags we generate
// ourselves — safe even if agent output echoes router banners or LLM text
// containing "<", ">", "&". Deliberately not using Tailwind's CDN typography
// plugin here: content renders via innerHTML rewrites on every streaming
// event, and the Tailwind CDN's JIT scanner was observed (elsewhere in this
// app) to unreliably miss styles under that churn — plain static CSS (the
// .md-* rules in app.css) doesn't have that failure mode.

function mdInline(escapedText) {
  let s = escapedText;
  s = s.replace(/`([^`]+)`/g, '<code class="md-code">$1</code>');
  s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
  s = s.replace(/(^|[^*])\*([^*\n]+)\*(?!\*)/g, '$1<em>$2</em>');
  return s;
}

export function renderMarkdown(raw) {
  const lines = (raw || '').replace(/\r\n/g, '\n').split('\n');
  const out = [];
  let para = [];
  let i = 0;

  function flushPara() {
    if (para.length) {
      out.push(`<p>${mdInline(esc(para.join(' ')))}</p>`);
      para = [];
    }
  }

  while (i < lines.length) {
    const line = lines[i];

    if (/^\s*```/.test(line)) {
      flushPara();
      const code = [];
      i++;
      while (i < lines.length && !/^\s*```/.test(lines[i])) { code.push(lines[i]); i++; }
      i++; // skip closing fence
      out.push(`<pre class="md-pre"><code>${esc(code.join('\n'))}</code></pre>`);
      continue;
    }

    if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?[\s:|-]+\|?\s*$/.test(lines[i + 1]) && lines[i + 1].includes('-')) {
      flushPara();
      const cells = l => l.trim().replace(/^\||\|$/g, '').split('|').map(c => c.trim());
      const head = cells(line);
      i += 2;
      const rows = [];
      while (i < lines.length && /^\s*\|/.test(lines[i])) { rows.push(cells(lines[i])); i++; }
      let tbl = '<div class="md-table-wrap"><table class="md-table"><thead><tr>';
      tbl += head.map(c => `<th>${mdInline(esc(c))}</th>`).join('');
      tbl += '</tr></thead><tbody>';
      for (const r of rows) tbl += '<tr>' + r.map(c => `<td>${mdInline(esc(c))}</td>`).join('') + '</tr>';
      tbl += '</tbody></table></div>';
      out.push(tbl);
      continue;
    }

    const h = line.match(/^(#{1,4})\s+(.*)$/);
    if (h) {
      flushPara();
      const level = h[1].length;
      out.push(`<h${level} class="md-h${level}">${mdInline(esc(h[2]))}</h${level}>`);
      i++;
      continue;
    }

    if (/^\s*[-*]\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*[-*]\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*[-*]\s+/, '')); i++; }
      out.push('<ul class="md-ul">' + items.map(it => `<li>${mdInline(esc(it))}</li>`).join('') + '</ul>');
      continue;
    }

    if (/^\s*\d+\.\s+/.test(line)) {
      flushPara();
      const items = [];
      while (i < lines.length && /^\s*\d+\.\s+/.test(lines[i])) { items.push(lines[i].replace(/^\s*\d+\.\s+/, '')); i++; }
      out.push('<ol class="md-ol">' + items.map(it => `<li>${mdInline(esc(it))}</li>`).join('') + '</ol>');
      continue;
    }

    if (line.trim() === '') { flushPara(); i++; continue; }

    para.push(line.trim());
    i++;
  }
  flushPara();
  return out.join('');
}
