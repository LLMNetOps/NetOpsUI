import { S } from '../state.js';
import { $, esc, fmtTime, fmtShortDate, fmtFullDateTime, copyToClipboard, renderMarkdown, confirmDialog, alertDialog } from '../utils.js';
import { activeBackend } from '../backends/index.js';

let _chatEl = null;
let _elapsedIv = null;
let _threadsIv = null;     // polls the shared thread list so other operators' chats show up
let _requestStartTs = null; // wall-clock start of the current request leg (reset per send/resume)
let _lastEventTs = null;    // used to compute per-step gaps between console entries

function fmtDelta(ms) {
  if (ms < 1000) return `+${Math.round(ms)}ms`;
  return `+${(ms / 1000).toFixed(1)}s`;
}

// ── Process console persistence — scoped per thread, survives page reload ────
// Keyed by backend + thread id so each chat session has its own independent
// log, not one shared across every conversation. S.console always points at (by reference,
// not copy) _consoleStore[S.threadId] so pushes/clears stay in sync with the
// persisted store without an extra write-back step.
const CONSOLE_STORAGE_KEY = 'llmnetops-console-v3';
const CONSOLE_MAX_ENTRIES = 500;
const CONSOLE_MAX_THREADS = 30;

let _consoleStore = {};

(function consoleHydrate() {
  try {
    const raw = localStorage.getItem(CONSOLE_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    for (const [key, entries] of Object.entries(parsed)) {
      const tid = key.replace(/^palapa:/, 'netops:'); // backend id used before the rename
      _consoleStore[tid] = entries.map(e => ({ ...e, ts: new Date(e.ts) }));
    }
  } catch { /* corrupt or unavailable — start empty */ }
})();

function consoleSave() {
  try {
    localStorage.setItem(CONSOLE_STORAGE_KEY, JSON.stringify(_consoleStore));
  } catch { /* storage full/unavailable — degrade to in-memory only */ }
}

function consoleKey(threadId) {
  return `${activeBackend().id}:${threadId}`;
}

function consoleForThread(threadId) {
  const key = consoleKey(threadId);
  if (!_consoleStore[key]) {
    const keys = Object.keys(_consoleStore);
    if (keys.length >= CONSOLE_MAX_THREADS) delete _consoleStore[keys[0]]; // evict oldest tracked thread
    _consoleStore[key] = [];
  }
  return _consoleStore[key];
}

function threadFromSummary(t) {
  return { id: t.id, title: t.title || 'New Chat', ts: t.updatedAt, createdAt: t.createdAt, lastMessage: t.lastMessage || '', owner: t.owner || '', running: !!t.running };
}

// Creates a thread on the active backend and makes it current. Returns false
// (after telling the operator) when the backend refuses or is unreachable.
async function chatNewThread() {
  try {
    const t = threadFromSummary(await activeBackend().createThread());
    S.threads.unshift(t);
    S.threadId = t.id;
    return true;
  } catch (e) {
    await alertDialog(`Gagal membuat thread di ${activeBackend().label}: ${e.message}`, 'Backend Tidak Terjangkau');
    return false;
  }
}

export async function screenChat(c, threadIdParam) {
  const backend = activeBackend();
  let loadError = null;
  if (S.threadsBackend !== backend.id) {
    // Threads belong to one backend; switching backends starts from its list.
    S.threads = []; S.threadId = null; S.messages = [];
    try {
      S.threads = (await backend.listThreads()).map(threadFromSummary);
      S.threadsBackend = backend.id;
    } catch (e) {
      loadError = e.message;
    }
  }

  let targetThreadId = threadIdParam || S.threadId;
  if (!targetThreadId) {
    if (S.threads.length > 0) {
      targetThreadId = S.threads[0].id;
    } else if (!loadError && await chatNewThread()) {
      targetThreadId = S.threadId;
    }
  } else if (!S.threads.some(t => t.id === targetThreadId)) {
    // Deep link to a thread not yet in our local list (e.g. shared link opened fresh) — placeholder entry
    S.threads.unshift({ id: targetThreadId, title: 'Shared Chat', ts: new Date(), createdAt: new Date(), lastMessage: '' });
  }

  const threadChanged = targetThreadId !== S.threadId;
  S.threadId = targetThreadId || null;
  S.console = S.threadId ? consoleForThread(S.threadId) : [];
  chatSyncUrl();

  c.innerHTML = `
  <div class="flex flex-col h-[calc(100vh-56px)] overflow-hidden">
    <div class="flex flex-1 min-h-0 overflow-hidden">
      <aside class="w-64 border-r border-outline-variant bg-surface-container-low flex flex-col shrink-0">
        <div class="p-4 border-b border-outline-variant flex justify-between items-center">
          <span class="text-label-caps font-label-caps text-on-surface-variant">Active Threads</span>
          <div class="flex items-center gap-1">
            <button id="btn-copy-link" title="Copy link to this chat" class="material-symbols-outlined text-sm text-on-surface-variant hover:bg-surface-container rounded p-1 transition-colors">link</button>
            <button id="btn-new-thread" title="New thread" class="material-symbols-outlined text-sm text-primary hover:bg-surface-container rounded p-1 transition-colors">add_box</button>
          </div>
        </div>
        ${loadError ? `<div class="m-3 p-3 rounded bg-red-50 border border-red-100 text-red-700 text-[11px]">Gagal memuat thread dari ${esc(backend.label)}: ${esc(loadError)}</div>` : ''}
        <div class="flex-1 overflow-y-auto chat-scroll p-3 space-y-1" id="thread-list"></div>
      </aside>
      <section class="flex-1 flex flex-col min-w-0">
        <div id="chat-messages" class="flex-1 overflow-y-auto chat-scroll p-6 space-y-6 flex flex-col"></div>
        <div class="border-t border-outline-variant bg-surface-container-lowest p-4 shrink-0">
          <div class="flex items-center gap-3 max-w-[900px] mx-auto">
            <input id="chat-input" type="text" class="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-4 py-2.5 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all" placeholder="Type a command or ask a question..." autocomplete="off" spellcheck="false">
            <button id="btn-send" class="px-5 py-2.5 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed">Send</button>
            <button id="btn-stop" title="Hentikan eksekusi" class="hidden px-5 py-2.5 bg-red-600 text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity items-center gap-1.5">
              <span class="material-symbols-outlined text-base leading-none">stop_circle</span>Stop
            </button>
          </div>
          <p class="text-[10px] text-on-surface-variant mt-2 text-center">[Enter] Kirim &middot; [Ctrl+L] Clear</p>
        </div>
      </section>
      <aside class="w-72 border-l border-outline-variant bg-surface-container-low flex flex-col shrink-0">
        <div class="p-4 border-b border-outline-variant">
          <p class="text-label-caps font-label-caps text-on-surface-variant">Backend</p>
          <a href="#settings" class="text-body-sm font-medium text-primary hover:underline">${esc(backend.label)}</a>
          ${backend.capabilities.approval ? '' : '<p class="text-[10px] text-on-surface-variant mt-0.5">Tanpa approval &middot; tool read-only</p>'}
        </div>
        <div class="px-4 pt-4 pb-2 flex justify-between items-center">
          <span class="text-label-caps font-label-caps text-on-surface-variant">Tool Activity</span>
          <span id="tool-count" class="text-[10px] text-outline tabular-nums"></span>
        </div>
        <div id="tool-panel" class="flex-1 overflow-y-auto chat-scroll px-3 pb-3 space-y-2"></div>
        <div class="p-4 border-t border-outline-variant">
          <p class="text-label-caps font-label-caps text-on-surface-variant mb-1">Active Query</p>
          <p id="active-query" class="text-[11px] text-on-surface-variant truncate">—</p>
          <p id="elapsed-display" class="text-[11px] text-primary tabular-nums mt-1"></p>
        </div>
      </aside>
    </div>
    <div id="debug-console" class="border-t border-outline-variant shrink-0 flex flex-col" style="height:${S.consoleOpen ? S.consoleHeight : 36}px">
      <div id="console-resize-handle" class="h-1 shrink-0 cursor-ns-resize hover:bg-primary/30 transition-colors"></div>
      <div id="console-header" class="flex items-center justify-between px-3 h-8 shrink-0 cursor-pointer select-none border-b border-outline-variant bg-surface-container-low">
        <div class="flex items-center gap-2">
          <span id="console-toggle-icon" class="material-symbols-outlined text-base text-on-surface-variant">${S.consoleOpen ? 'expand_more' : 'expand_less'}</span>
          <span class="text-label-caps font-label-caps text-on-surface-variant">Process Console</span>
          <span id="console-count" class="text-[10px] text-outline tabular-nums">(${S.console.length})</span>
        </div>
        <button id="btn-console-clear" class="text-[10px] text-on-surface-variant hover:text-primary transition-colors">Clear</button>
      </div>
      <div id="debug-console-body" class="flex-1 overflow-y-auto chat-scroll font-data-mono text-data-mono p-3 space-y-1.5" style="background:#191c1e; display:${S.consoleOpen ? '' : 'none'}"></div>
    </div>
  </div>
  <div id="approval-overlay" class="hidden fixed inset-0 bg-black/30 backdrop-blur-sm z-[200] flex items-center justify-center">
    <div class="bg-surface-container-lowest rounded-xl shadow-xl max-w-[560px] w-full mx-4 overflow-hidden">
      <div class="bg-amber-50 px-6 py-3 flex items-center gap-2 border-b border-amber-200">
        <span class="material-symbols-outlined text-amber-700">warning</span>
        <span class="text-label-caps font-label-caps text-amber-800">APPROVAL REQUIRED</span>
      </div>
      <div class="p-6">
        <h3 class="text-title-sm font-title-sm font-bold text-on-surface mb-2">Confirm System Operation</h3>
        <p class="text-body-sm text-on-surface-variant mb-4">An automated agent has requested permission to perform a high-impact task.</p>
        <div class="border border-outline-variant rounded-lg divide-y divide-outline-variant text-body-sm">
          <div class="px-4 py-2.5"><p class="text-label-caps font-label-caps text-on-surface-variant mb-1">ACTION</p><pre id="m-action" class="font-data-mono text-data-mono whitespace-pre-wrap break-all">—</pre></div>
          <div id="m-desc-row" class="px-4 py-2.5"><p class="text-label-caps font-label-caps text-on-surface-variant mb-1">ALASAN</p><p id="m-desc">—</p></div>
        </div>
      </div>
      <div class="px-6 pb-6 flex items-center justify-between gap-3">
        <span class="text-[10px] text-on-surface-variant">[Y] Sekali &middot; [N] Tolak</span>
        <div id="approval-choices" class="flex flex-wrap justify-end gap-2"></div>
      </div>
    </div>
  </div>`;

  _chatEl = $('chat-messages');
  // Messages are re-rendered wholesale while streaming, so the copy button is handled by delegation.
  _chatEl.onclick = async e => {
    const btn = e.target.closest('[data-copy-msg]');
    if (!btn) return;
    const text = S.messages[+btn.dataset.copyMsg]?.content;
    if (!text) return;
    const ok = await copyToClipboard(text);
    btn.querySelector('.material-symbols-outlined').textContent = ok ? 'check' : 'error';
    btn.title = ok ? 'Tersalin' : 'Gagal menyalin';
    setTimeout(() => {
      if (!btn.isConnected) return;
      btn.querySelector('.material-symbols-outlined').textContent = 'content_copy';
      btn.title = 'Salin jawaban';
    }, 1500);
  };
  chatRenderThreads();
  chatRenderTools();
  consoleRender();
  if (!S.threadId) {
    chatRenderMessages();
  } else if (threadChanged || S.messages.length === 0) {
    await chatLoadHistory(S.threadId);
  } else {
    chatRenderMessages();
  }
  chatBindEvents();
  chatBindConsole();
  chatStartThreadPoll();
}

function chatSyncUrl() {
  if (!S.threadId) return;
  const target = '#chat/' + encodeURIComponent(S.threadId);
  if (location.hash !== target) history.replaceState(null, '', target);
}

async function chatLoadHistory(threadId, { attach = true } = {}) {
  chatRenderMessages();
  try {
    const msgs = await activeBackend().loadMessages(threadId);
    if (threadId !== S.threadId) return; // switched away while loading
    S.messages = msgs.map(m => ({ role: m.role, content: m.content, ts: m.ts || null, streaming: false }));
  } catch (e) {
    consolePush('error', 'Gagal memuat riwayat: ' + e.message);
  }
  chatRenderMessages();
  // A question without an answer on a thread flagged "running" means the run is
  // still going on the server (page refreshed, or another operator started it).
  const last = S.messages[S.messages.length - 1];
  const t = S.threads.find(x => x.id === threadId);
  // Not awaited: it lasts as long as the run, and screenChat() still has to bind the UI.
  if (attach && t?.running && last?.role === 'user') chatAttach(threadId);
}

// Re-attaches to a run that is already in progress on the server.
async function chatAttach(threadId) {
  const backend = activeBackend();
  if (!backend.resume || S.chatState !== 'idle' || threadId !== S.threadId) return;
  const lastUser = [...S.messages].reverse().find(m => m.role === 'user');
  S.activeQuery = lastUser ? lastUser.content : '';
  S.messages.push({ role: 'agent', content: '', ts: new Date(), streaming: true });
  chatResetTools();
  chatStartElapsed();
  _requestStartTs = Date.now();
  _lastEventTs = null;
  S.chatState = 'streaming';
  consolePush('note', 'Tersambung ke proses yang sedang berjalan di server.');
  chatRenderMessages(); chatUpdateUI();
  const emit = ev => { if (threadId === S.threadId) chatHandleEvent(ev); };
  try { await backend.resume(threadId, emit); }
  catch (e) { emit({ type: 'error', text: e.message || 'Connection failed' }); }
  if (threadId !== S.threadId) return; // left the thread; its run continues on the server
  chatFinish();
  // The server stored the final answer; show that copy and refresh the thread list.
  if (threadId === S.threadId) {
    try {
      S.threads = (await backend.listThreads()).map(threadFromSummary);
      chatRenderThreads();
    } catch { /* next poll */ }
    await chatLoadHistory(threadId, { attach: false });
  }
}

function chatBindEvents() {
  const inp = $('chat-input'), btnS = $('btn-send'), btnT = $('btn-stop'), btnN = $('btn-new-thread'), btnL = $('btn-copy-link');

  async function send() {
    const text = inp.value.trim();
    if (!text || S.chatState !== 'idle') return;
    if (!S.threadId && !(await chatNewThread())) return;
    const backend = activeBackend();
    const threadId = S.threadId;
    inp.value = '';
    S.activeQuery = text;
    S.messages.push({ role: 'user', content: text, ts: new Date() });
    S.messages.push({ role: 'agent', content: '', ts: new Date(), streaming: true });
    chatResetTools();
    chatStartElapsed();
    _requestStartTs = Date.now();
    _lastEventTs = null;
    S.chatState = 'streaming';
    chatTouchThread(threadId, text);
    chatRenderMessages(); chatUpdateUI();
    // Events from a thread the operator has since left must not touch the visible one.
    const emit = ev => { if (threadId === S.threadId) chatHandleEvent(ev); };
    try { await backend.send(threadId, text, emit); }
    catch (e) { emit({ type: 'error', text: e.message || 'Connection failed' }); }
    if (threadId === S.threadId) chatFinish();
  }

  btnS.onclick = send;
  btnT.onclick = async () => {
    if (S.chatState !== 'streaming' || S.stopRequested) return;
    S.stopRequested = true;
    chatUpdateUI();
    consolePush('stopped', 'Permintaan stop dikirim...');
    try {
      const r = await activeBackend().stop(S.threadId);
      if (!r || r.ok === false) {
        consolePush('stopped', 'Tidak ada proses aktif untuk dihentikan (kemungkinan sudah selesai).');
        S.stopRequested = false;
        chatUpdateUI();
      }
    } catch (e) {
      consolePush('error', 'Gagal mengirim permintaan stop: ' + (e.message || 'unknown'));
      S.stopRequested = false;
      chatUpdateUI();
    }
  };
  inp.onkeydown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    if (e.key === 'l' && e.ctrlKey) { e.preventDefault(); chatClear(); }
  };
  btnN.onclick = async () => {
    if (S.chatState !== 'idle' || !(await chatNewThread())) return;
    S.console = consoleForThread(S.threadId);
    chatSyncUrl();
    chatClear();
    consoleRender();
  };
  btnL.onclick = async () => {
    const url = location.origin + location.pathname + '#chat/' + encodeURIComponent(S.threadId);
    const ok = await copyToClipboard(url);
    btnL.textContent = ok ? 'check' : 'error';
    setTimeout(() => { btnL.textContent = 'link'; }, 1200);
    if (!ok) window.prompt('Salin link chat ini:', url);
  };
  $('approval-choices').onclick = e => {
    const b = e.target.closest('[data-choice]');
    if (b) chatResolveApproval(b.dataset.choice);
  };

  if (!_approvalKeysBound) {
    _approvalKeysBound = true;
    document.addEventListener('keydown', e => {
      if (!S.pendingApproval) return;
      if (e.key === 'y' || e.key === 'Y') chatResolveApproval('once');
      if (e.key === 'n' || e.key === 'N') chatResolveApproval('deny');
    });
  }
}

let _approvalKeysBound = false;

// Keeps the thread list ordering/preview in sync with a message just sent,
// without refetching the list from the backend.
function chatTouchThread(threadId, text) {
  const t = S.threads.find(x => x.id === threadId);
  if (!t) return;
  if (!t.title || t.title === 'New Chat') t.title = text.slice(0, 60);
  t.lastMessage = text.slice(0, 120);
  t.ts = new Date();
  S.threads = [t, ...S.threads.filter(x => x !== t)];
  chatRenderThreads();
}

// Normalized backend events — see the adapter contract in backends/index.js.
function chatHandleEvent(ev) {
  const last = S.messages[S.messages.length - 1];
  const agentMsg = last && last.role === 'agent' ? last : null;
  switch (ev.type) {
    case 'delta':
      if (agentMsg) agentMsg.content += ev.text;
      break;
    case 'tool_start':
      S.tools.push({ name: ev.name, detail: ev.detail, state: 'running', durationMs: null });
      S.toolCount++;
      consolePush('tool_call', `${ev.name}${ev.detail ? ' ' + ev.detail : ''}`);
      chatRenderTools();
      break;
    case 'tool_end': {
      // Hermes announces tool_start first; NetOps Agent only reports completed calls.
      const running = [...S.tools].reverse().find(t => t.name === ev.name && t.state === 'running');
      const state = ev.error ? 'failed' : 'done';
      if (running) Object.assign(running, { state, durationMs: ev.durationMs });
      else { S.tools.push({ name: ev.name, detail: ev.detail, source: ev.source, state, durationMs: ev.durationMs }); S.toolCount++; }
      consolePush(ev.error ? 'error' : 'tool_result',
        `${ev.name} (${fmtDelta(ev.durationMs || 0).slice(1)})${ev.detail ? ' → ' + ev.detail : ''}`);
      chatRenderTools();
      break;
    }
    case 'approval':
      S.pendingApproval = ev.data;
      consolePush('approval_required', ev.data.action);
      chatShowApproval();
      break;
    case 'stopped':
      consolePush('stopped', ev.text);
      if (agentMsg && !agentMsg.content) agentMsg.content = `_${ev.text}_`;
      break;
    case 'error':
      consolePush('error', ev.text);
      if (agentMsg && !agentMsg.content) agentMsg.content = `**Error:** ${ev.text}`;
      break;
    default: // note, thinking
      consolePush(ev.type, ev.text);
  }
  chatRenderMessages(); chatUpdateUI();
}

async function chatResolveApproval(choice) {
  const p = S.pendingApproval;
  if (!p) return;
  chatHideApproval();
  consolePush('approval_required', `Operator: ${choice === 'deny' ? 'DITOLAK' : 'DISETUJUI (' + choice + ')'}`);
  try {
    // The run's event stream stays open while waiting, so the turn simply
    // continues in send() once the backend accepts the decision.
    await activeBackend().respondApproval(S.threadId, choice, p.requestId);
  } catch (e) {
    consolePush('error', 'Gagal mengirim keputusan approval: ' + e.message);
  }
}

function chatFinish() {
  const last = S.messages[S.messages.length - 1];
  if (last) last.streaming = false;
  S.chatState = 'idle';
  chatStopElapsed();
  if (_requestStartTs) {
    consolePush('timing', `Total durasi: ${fmtDelta(Date.now() - _requestStartTs)}`);
    _requestStartTs = null;
  }
  S.tools.forEach(t => { if (t.state === 'running') t.state = 'done'; });
  chatHideApproval();
  chatRenderMessages(); chatRenderTools(); chatUpdateUI();
}

function chatClear() {
  S.messages = []; S.activeQuery = ''; S.chatState = 'idle';
  chatResetTools();
  chatStopElapsed();
  chatRenderMessages(); chatRenderThreads(); chatUpdateUI();
}

function chatResetTools() {
  S.tools = [];
  S.toolCount = 0;
  chatRenderTools();
}

// Tool arguments arrive as a raw JSON string. Show the one value that says what the
// call does (command, path, agent…) instead of the JSON; `{}` means no arguments.
const TOOL_KEYS = ['command', 'cmd', 'query', 'path', 'agent', 'device', 'host', 'name', 'task', 'url'];
function toolSummary(detail) {
  if (!detail) return '';
  let a;
  try { a = JSON.parse(detail); } catch { return detail; }
  if (!a || typeof a !== 'object') return String(a ?? '');
  const entries = Object.entries(a).filter(([, v]) => v !== '' && v != null);
  if (!entries.length) return '';
  const key = TOOL_KEYS.find(k => a[k]);
  const fmt = v => (typeof v === 'string' ? v : JSON.stringify(v));
  if (!key) return entries.map(([k, v]) => `${k}=${fmt(v)}`).join(' ');
  const head = a.action ? `${a.action} ` : '';
  return head + fmt(a[key]);
}
function toolFull(detail) {
  try { return JSON.stringify(JSON.parse(detail), null, 2); } catch { return detail || ''; }
}

function chatRenderTools() {
  const el = $('tool-panel'); if (!el) return;
  const cnt = $('tool-count'); if (cnt) cnt.textContent = S.toolCount ? `${S.toolCount} call` : '';
  if (!S.tools.length) {
    el.innerHTML = `<p class="text-[11px] text-on-surface-variant px-1">${S.chatState === 'streaming' ? 'Menunggu tool call...' : 'Belum ada tool call pada giliran ini.'}</p>`;
    return;
  }
  const styles = {
    running: { dot: 'bg-green-500 pulse-green', text: 'text-green-700', label: 'RUNNING', bl: 'border-l-[3px] border-l-green-500' },
    done:    { dot: 'bg-gray-400', text: 'text-on-surface-variant', label: 'DONE', bl: '' },
    failed:  { dot: 'bg-red-500', text: 'text-red-700', label: 'FAILED', bl: 'border-l-[3px] border-l-red-500' },
  };
  el.innerHTML = S.tools.map(t => {
    const st = styles[t.state] || styles.done;
    const summary = toolSummary(t.detail);
    const child = t.source && t.source !== 'main' ? t.source.replace(/^child:/, '') : '';
    const dur = t.durationMs != null ? ` &middot; ${fmtDelta(t.durationMs).slice(1)}` : '';
    return `<div class="bg-surface-container-lowest border border-outline-variant ${st.bl} rounded-lg p-3">
      <div class="flex justify-between items-center gap-2">
        <span class="text-xs font-bold text-primary font-data-mono-sm truncate" title="${esc(t.name)}">${child ? '↳ ' : ''}${esc(t.name)}${child ? ` <span class="font-normal text-outline">· ${esc(child)}</span>` : ''}</span>
        <span class="flex items-center gap-1.5 shrink-0"><span class="w-2 h-2 rounded-full ${st.dot}"></span><span class="text-label-caps font-label-caps ${st.text}">${st.label}</span></span>
      </div>
      ${summary ? `<details class="mt-1"><summary class="text-[10px] text-on-surface-variant font-data-mono-sm cursor-pointer truncate list-none" title="Klik untuk detail lengkap">${esc(summary)}</summary><pre class="text-[10px] text-on-surface-variant font-data-mono-sm mt-1 whitespace-pre-wrap break-all">${esc(toolFull(t.detail))}</pre></details>` : ''}
      ${dur ? `<p class="text-[10px] text-outline mt-0.5 tabular-nums">${dur.replace(' &middot; ', '')}</p>` : ''}
    </div>`;
  }).join('');
}

function chatRenderMessages() {
  const el = $('chat-messages'); if (!el) return;
  if (S.messages.length === 0) {
    el.innerHTML = `<div class="flex-1 flex flex-col items-center justify-center text-center">
      <span class="material-symbols-outlined text-5xl text-outline-variant mb-3">hub</span>
      <h3 class="text-title-sm font-title-sm text-primary mb-1">LLMNetOps</h3>
      <p class="text-body-sm text-on-surface-variant max-w-xs">Ketik perintah untuk memulai sesi dengan <b>${esc(activeBackend().label)}</b>.</p>
    </div>`;
    return;
  }
  el.innerHTML = S.messages.map(m => m.role === 'user' ? chatUserMsg(m) : chatAgentMsg(m)).join('');
  el.scrollTop = el.scrollHeight;
}

function chatUserMsg(m) {
  return `<div class="flex flex-col items-end max-w-[85%] self-end">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-[10px] text-outline tabular-nums">${m.ts ? fmtTime(m.ts) : ''}</span>
      <span class="bg-primary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">ANDA</span>
    </div>
    <div class="bg-primary-container text-white p-4 rounded-xl rounded-tr-none shadow-sm">
      <p class="text-body-md">${esc(m.content)}</p>
    </div>
  </div>`;
}

// Status line shown for as long as the agent is working, not only before the
// first token: a delegated sub-agent can run for minutes without emitting anything.
function workingStatus() {
  const running = [...S.tools].reverse().find(t => t.state === 'running');
  const done = S.tools.filter(t => t.state !== 'running').length;
  if (running) return `Menjalankan ${running.name}…`;
  if (S.elapsed >= 20) return done ? `${done} tool selesai — menunggu agent / sub-agent (delegasi bisa 1–3 menit)…` : 'Menunggu agent / sub-agent bekerja (bisa 1–3 menit)…';
  return done ? `${done} tool selesai — agent menyusun langkah berikutnya…` : 'Agent sedang memproses…';
}

function fmtElapsed(sec) {
  return `${String(Math.floor(sec / 60)).padStart(2, '0')}:${String(sec % 60).padStart(2, '0')}`;
}

function chatAgentMsg(m) {
  const typing = m.streaming ? `<div class="flex items-center gap-2 ${m.content ? 'mt-3 pt-3 border-t border-outline-variant' : 'mt-2'}">
    <div class="flex items-center gap-1">
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    </div>
    <span class="text-[11px] text-on-surface-variant">${esc(workingStatus())}</span>
    <span data-work-elapsed class="text-[11px] text-outline tabular-nums">${fmtElapsed(S.elapsed || 0)}</span></div>` : '';
  const txt = m.content ? `<div class="md text-body-md text-on-surface leading-relaxed">${renderMarkdown(m.content)}</div>` : '';
  // Copy only once the answer is complete (a streaming re-render would also reset the button's feedback).
  const copy = m.content && !m.streaming
    ? `<button data-copy-msg="${S.messages.indexOf(m)}" title="Salin jawaban" aria-label="Salin jawaban" class="ml-1 text-on-surface-variant hover:text-primary transition-colors"><span class="material-symbols-outlined text-[16px]">content_copy</span></button>`
    : '';
  return `<div class="flex flex-col items-start max-w-[90%] self-start">
    <div class="flex items-center gap-2 mb-1">
      <span class="bg-secondary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">AGENT</span>
      <span class="text-[10px] text-outline tabular-nums">${m.ts ? fmtTime(m.ts) : ''}</span>${copy}
    </div>
    <div class="bg-surface-container-lowest p-4 rounded-xl rounded-tl-none border border-outline-variant shadow-sm w-full">
      ${txt}${typing}
    </div>
  </div>`;
}

function chatEventLine(ev, isActive) {
  const c = {
    note: { tag: '#fcd34d', l: 'NOTE' },
    thinking: { tag: '#a78bfa', l: 'THINKING' },
    tool_call: { tag: '#60a5fa', l: 'TOOL_CALL' },
    tool_result: { tag: '#4ade80', l: 'RESULT' },
    approval_required: { tag: '#fbbf24', l: 'APPROVAL' },
    stopped: { tag: '#f87171', l: 'STOPPED' },
    error: { tag: '#f87171', l: 'ERROR' },
    timing: { tag: '#38bdf8', l: 'DURASI' },
  }[ev.type] || { tag: '#94a3b8', l: ev.type.toUpperCase() };
  const delta = ev.deltaMs != null
    ? `<span class="text-[9px] tabular-nums ml-2 shrink-0" style="color:#73777f" title="Jeda sejak entri sebelumnya">${fmtDelta(ev.deltaMs)}</span>`
    : '';
  const running = isActive && ev.type === 'tool_call'
    ? `<span class="inline-flex items-center gap-1 ml-2 shrink-0"><span class="w-1.5 h-1.5 rounded-full pulse-green" style="background:#94492d"></span><span class="text-[9px] uppercase tracking-wider" style="color:#94492d">running</span></span>`
    : '';
  return `<div class="flex items-start gap-2"><span class="font-bold whitespace-nowrap" style="color:${c.tag}">[${c.l}]</span><span class="break-all" style="color:#c3c6cf">${esc(ev.content)}</span>${delta}${running}</div>`;
}

function consolePush(type, content) {
  // Mutate in place (push/splice), not reassign — S.console and
  // _consoleStore[threadId] must stay the same array instance.
  const now = new Date();
  const deltaMs = _lastEventTs ? now.getTime() - _lastEventTs.getTime() : null;
  _lastEventTs = now;
  S.console.push({ type, content, ts: now, deltaMs });
  if (S.console.length > CONSOLE_MAX_ENTRIES) S.console.splice(0, S.console.length - CONSOLE_MAX_ENTRIES);
  consoleSave();
  consoleRender();
}

function consoleRender() {
  const el = $('debug-console-body');
  const countEl = $('console-count');
  if (countEl) countEl.textContent = `(${S.console.length})`;
  if (!el) return;
  const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40;
  el.innerHTML = S.console.length
    ? S.console.map((ev, i) => chatEventLine(ev, S.chatState === 'streaming' && i === S.console.length - 1)).join('')
    : `<div class="text-[11px]" style="color:#73777f">Belum ada aktivitas. Kirim pesan untuk mulai.</div>`;
  if (atBottom) el.scrollTop = el.scrollHeight;
}

let _consoleBound = false;

function chatBindConsole() {
  const header = $('console-header'), clearBtn = $('btn-console-clear');

  header.onclick = () => {
    S.consoleOpen = !S.consoleOpen;
    consoleApplyState();
    if (S.consoleOpen) consoleRender();
  };
  clearBtn.onclick = (e) => {
    e.stopPropagation();
    S.console.length = 0; // clear in place — keeps the _consoleStore[threadId] reference intact
    consoleSave();
    consoleRender();
  };

  if (_consoleBound) return;
  _consoleBound = true;
  let dragging = false, startY = 0, startH = 0;
  document.addEventListener('mousedown', (e) => {
    const handle = $('console-resize-handle');
    if (!handle || e.target !== handle || !S.consoleOpen) return;
    dragging = true; startY = e.clientY; startH = S.consoleHeight;
    document.body.style.cursor = 'ns-resize';
    e.preventDefault();
  });
  document.addEventListener('mousemove', (e) => {
    if (!dragging) return;
    const dy = startY - e.clientY;
    S.consoleHeight = Math.min(Math.max(startH + dy, 120), Math.floor(window.innerHeight * 0.7));
    consoleApplyState();
  });
  document.addEventListener('mouseup', () => {
    if (!dragging) return;
    dragging = false;
    document.body.style.cursor = '';
  });
}

function consoleApplyState() {
  const panel = $('debug-console'), body = $('debug-console-body'), icon = $('console-toggle-icon');
  if (!panel) return;
  panel.style.height = (S.consoleOpen ? S.consoleHeight : 36) + 'px';
  if (body) body.style.display = S.consoleOpen ? '' : 'none';
  if (icon) icon.textContent = S.consoleOpen ? 'expand_more' : 'expand_less';
}

function chatRenderThreads() {
  const el = $('thread-list'); if (!el) return;
  el.innerHTML = S.threads.map(t => {
    const a = t.id === S.threadId;
    const preview = t.lastMessage ? `<p class="text-[10px] ${a ? 'text-on-surface-variant' : 'text-outline'} mt-0.5 truncate">${esc(t.lastMessage)}</p>` : '';
    const createdTitle = t.createdAt ? `Dibuat: ${esc(fmtFullDateTime(t.createdAt))}` : '';
    return `<div data-tid="${esc(t.id)}" title="${createdTitle}" class="${a ? 'bg-white border border-outline-variant shadow-sm' : 'hover:bg-surface-container'} group relative p-3 pr-14 rounded cursor-pointer transition-colors" onclick="chatSwitchThread('${esc(t.id)}')">
      <div class="absolute top-2 right-2 flex items-center gap-0.5">
        <button onclick="chatRenameThread('${esc(t.id)}', event)" title="Ubah nama" class="material-symbols-outlined text-[15px] text-on-surface-variant opacity-0 group-hover:opacity-100 hover:text-primary hover:bg-surface-container-low rounded p-0.5 transition-opacity">edit</button>
        <button onclick="chatDeleteThread('${esc(t.id)}', event)" title="Hapus thread" class="material-symbols-outlined text-[15px] text-on-surface-variant opacity-0 group-hover:opacity-100 hover:text-red-600 hover:bg-red-50 rounded p-0.5 transition-opacity">delete</button>
      </div>
      <p data-title-el class="${a ? 'font-bold text-primary' : 'font-medium text-on-surface-variant'} text-xs truncate">${esc(t.title)}</p>
      ${preview}
      <p class="text-[10px] ${a ? 'text-primary/60' : 'text-outline'} mt-0.5 tabular-nums">${fmtTime(t.ts)} &middot; dibuat ${esc(fmtShortDate(t.createdAt))}</p>
      ${t.owner || t.running ? `<p class="text-[10px] text-outline mt-0.5 truncate flex items-center gap-1" title="Pemilik thread">${t.running ? '<span class="w-1.5 h-1.5 rounded-full bg-green-500 pulse-green shrink-0" title="Sedang diproses"></span>' : ''}${esc(t.owner)}${t.running ? ' &middot; berjalan' : ''}</p>` : ''}
    </div>`;
  }).join('');
}

async function chatRenameThread(threadId, event) {
  if (event) event.stopPropagation();
  const row = document.querySelector(`[data-tid="${CSS.escape(threadId)}"]`);
  const titleEl = row && row.querySelector('[data-title-el]');
  if (!titleEl) return;

  const t = S.threads.find(x => x.id === threadId);
  const current = t ? t.title : '';

  const input = document.createElement('input');
  input.type = 'text';
  input.value = current;
  input.maxLength = 120;
  input.className = titleEl.className + ' bg-white border border-primary rounded px-1 py-0.5 w-full outline-none';
  titleEl.replaceWith(input);
  input.focus();
  input.select();

  let settled = false;
  async function commit() {
    if (settled) return; settled = true;
    const title = input.value.trim() || current || 'New Chat';
    if (t) t.title = title;
    if (title !== current) {
      try { await activeBackend().renameThread(threadId, title); }
      catch (e) { await alertDialog('Gagal mengubah nama: ' + e.message, 'Terjadi Kesalahan'); }
    }
    chatRenderThreads();
  }
  function cancel() {
    if (settled) return; settled = true;
    chatRenderThreads();
  }

  input.onclick = e => e.stopPropagation();
  input.addEventListener('keydown', e => {
    e.stopPropagation();
    if (e.key === 'Enter') { e.preventDefault(); commit(); }
    if (e.key === 'Escape') { e.preventDefault(); cancel(); }
  });
  input.addEventListener('blur', commit);
}
window.chatRenameThread = chatRenameThread;

async function chatDeleteThread(threadId, event) {
  if (event) event.stopPropagation();
  const t = S.threads.find(x => x.id === threadId);
  const ok = await confirmDialog({
    title: 'Hapus percakapan?',
    message: `"${t ? t.title : threadId}" akan dihapus permanen beserta seluruh riwayatnya. Tindakan ini tidak bisa dibatalkan.`,
    confirmLabel: 'Hapus',
    cancelLabel: 'Batal',
    danger: true,
  });
  if (!ok) return;

  try {
    await activeBackend().deleteThread(threadId);
  } catch (e) {
    await alertDialog('Gagal menghapus thread: ' + e.message, 'Terjadi Kesalahan');
    return;
  }

  S.threads = S.threads.filter(x => x.id !== threadId);
  delete _consoleStore[consoleKey(threadId)];
  consoleSave();

  if (threadId !== S.threadId) {
    chatRenderThreads();
    return;
  }

  if (S.threads.length > 0) {
    await chatSwitchThread(S.threads[0].id);
  } else {
    if (!(await chatNewThread())) S.threadId = null;
    S.console = S.threadId ? consoleForThread(S.threadId) : [];
    chatSyncUrl();
    chatClear();
    consoleRender();
  }
}
window.chatDeleteThread = chatDeleteThread;

async function chatSwitchThread(threadId) {
  if (threadId === S.threadId) return;
  if (S.chatState !== 'idle') {
    // A run in progress used to lock every other thread. Leave it running on the
    // server and stop following it; coming back re-attaches while it still runs.
    const backend = activeBackend();
    if (!backend.detach) return;
    backend.detach(S.threadId);
    S.chatState = 'idle';
    S.pendingApproval = null;
    chatHideApproval();
    _requestStartTs = null;
  }
  S.threadId = threadId;
  S.console = consoleForThread(threadId);
  chatSyncUrl();
  S.activeQuery = '';
  S.chatState = 'idle';
  chatResetTools();
  chatStopElapsed();
  chatRenderThreads();
  chatUpdateUI();
  consoleRender();
  S.messages = [];
  await chatLoadHistory(threadId);
}
window.chatSwitchThread = chatSwitchThread;

const APPROVAL_CHOICES = {
  once:    { label: 'Izinkan sekali', cls: 'bg-green-700 text-white hover:bg-green-800' },
  session: { label: 'Izinkan sesi ini', cls: 'border border-outline-variant text-primary hover:bg-surface-container' },
  always:  { label: 'Selalu izinkan', cls: 'border border-outline-variant text-primary hover:bg-surface-container' },
  deny:    { label: 'Tolak', cls: 'border border-red-300 text-red-700 hover:bg-red-50' },
};

function chatShowApproval() {
  const o = $('approval-overlay'); if (!o) return; o.classList.remove('hidden');
  const p = S.pendingApproval || {};
  const ac = $('m-action'), de = $('m-desc'), dr = $('m-desc-row'), ch = $('approval-choices');
  if (ac) ac.textContent = p.action || '—';
  if (de) de.textContent = p.description || '';
  if (dr) dr.classList.toggle('hidden', !p.description || p.description === p.action);
  if (ch) {
    // Deny first, most permissive last — matches the order operators scan.
    const order = ['deny', 'always', 'session', 'once'];
    ch.innerHTML = order.filter(c => (p.choices || ['once', 'deny']).includes(c)).map(c => {
      const s = APPROVAL_CHOICES[c];
      return `<button data-choice="${c}" class="px-4 py-2 rounded-lg text-body-sm font-medium transition-colors ${s.cls}">${s.label}</button>`;
    }).join('');
  }
}

function chatHideApproval() {
  const o = $('approval-overlay'); if (o) o.classList.add('hidden'); S.pendingApproval = null;
}

function chatStartElapsed() {
  S.elapsed = 0; chatStopElapsed(); const st = Date.now();
  _elapsedIv = setInterval(() => {
    S.elapsed = Math.floor((Date.now() - st) / 1000);
    const el = $('elapsed-display');
    if (el) el.textContent = `⏱ ${fmtElapsed(S.elapsed)}`;
    document.querySelectorAll('[data-work-elapsed]').forEach(n => { n.textContent = fmtElapsed(S.elapsed); });
    if (S.elapsed === 20) chatRenderMessages(); // switch the status line to the long-wait hint
  }, 1000);
}

function chatStopElapsed() { if (_elapsedIv) { clearInterval(_elapsedIv); _elapsedIv = null; } }
function chatUpdateUI() {
  const q = $('active-query'); if (q) q.textContent = S.activeQuery || '—';
  const running = S.chatState === 'streaming';
  if (!running) S.stopRequested = false;
  const btnS = $('btn-send'), btnT = $('btn-stop');
  if (btnS) btnS.classList.toggle('hidden', running);
  if (btnT) {
    btnT.classList.toggle('hidden', !running);
    btnT.classList.toggle('flex', running);
    btnT.disabled = S.stopRequested;
    btnT.innerHTML = S.stopRequested
      ? `<span class="material-symbols-outlined text-base leading-none animate-spin">progress_activity</span>Menghentikan...`
      : `<span class="material-symbols-outlined text-base leading-none">stop_circle</span>Stop`;
  }
}

// Refreshes the shared thread list (and the open thread when someone else
// added to it) while the operator is idle on this screen.
function chatStartThreadPoll() {
  chatStopThreadPoll();
  const backend = activeBackend();
  if (!backend.capabilities.serverThreads) return;
  _threadsIv = setInterval(async () => {
    if (document.hidden || S.chatState !== 'idle') return;
    try {
      const fresh = (await backend.listThreads()).map(threadFromSummary);
      if (S.screen !== 'chat' || backend.id !== activeBackend().id || S.chatState !== 'idle') return;
      const cur = S.threads.find(t => t.id === S.threadId);
      const now = fresh.find(t => t.id === S.threadId);
      const changed = cur && now && now.ts.getTime() !== cur.ts.getTime();
      const keep = S.threads.filter(t => !fresh.some(f => f.id === t.id) && t.id === S.threadId && !now && t.lastMessage === '');
      S.threads = [...fresh, ...keep];
      chatRenderThreads();
      if (changed) await chatLoadHistory(S.threadId);
    } catch { /* transient — try again on the next tick */ }
  }, 5000);
}

function chatStopThreadPoll() { if (_threadsIv) { clearInterval(_threadsIv); _threadsIv = null; } }

export function chatUnmount() { chatStopElapsed(); chatStopThreadPoll(); }
