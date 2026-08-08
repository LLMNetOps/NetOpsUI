import { AGENTS, ROLE_TO_ALIAS } from '../config.js';
import { S } from '../state.js';
import { $, esc, fmtTime, fmtShortDate, fmtFullDateTime, agentCardHtml, loadingHtml, copyToClipboard, renderMarkdown, confirmDialog, alertDialog } from '../utils.js';
import { apiGet, apiCreateSession, apiStreamChat, apiApprove, apiDelete, apiPut } from '../api.js';

let _chatEl = null;
let _elapsedIv = null;
let _requestStartTs = null; // wall-clock start of the current request leg (reset per send/resume)
let _lastEventTs = null;    // used to compute per-step gaps between console entries

function fmtDelta(ms) {
  if (ms < 1000) return `+${Math.round(ms)}ms`;
  return `+${(ms / 1000).toFixed(1)}s`;
}

// ── Process console persistence — scoped per thread, survives page reload ────
// Keyed by thread id so each chat session has its own independent log, not one
// shared across every conversation. S.console always points at (by reference,
// not copy) _consoleStore[S.threadId] so pushes/clears stay in sync with the
// persisted store without an extra write-back step.
const CONSOLE_STORAGE_KEY = 'llmnetops-console-v2';
const CONSOLE_MAX_ENTRIES = 500;
const CONSOLE_MAX_THREADS = 30;

let _consoleStore = {};

(function consoleHydrate() {
  try {
    const raw = localStorage.getItem(CONSOLE_STORAGE_KEY);
    if (!raw) return;
    const parsed = JSON.parse(raw);
    for (const [tid, entries] of Object.entries(parsed)) {
      _consoleStore[tid] = entries.map(e => ({ ...e, ts: new Date(e.ts) }));
    }
  } catch { /* corrupt or unavailable — start empty */ }
})();

function consoleSave() {
  try {
    localStorage.setItem(CONSOLE_STORAGE_KEY, JSON.stringify(_consoleStore));
  } catch { /* storage full/unavailable — degrade to in-memory only */ }
}

function consoleForThread(threadId) {
  if (!_consoleStore[threadId]) {
    const keys = Object.keys(_consoleStore);
    if (keys.length >= CONSOLE_MAX_THREADS) delete _consoleStore[keys[0]]; // evict oldest tracked thread
    _consoleStore[threadId] = [];
  }
  return _consoleStore[threadId];
}

export async function screenChat(c, threadIdParam) {
  if (S.threads.length === 0) {
    try {
      const r = await apiGet('/api/sessions');
      if (r.sessions && r.sessions.length > 0) {
        S.threads = r.sessions.map(s => ({
          id: s.thread_id,
          title: s.title || 'New Chat',
          ts: new Date(s.updated_at || s.created_at),
          createdAt: new Date(s.created_at),
          lastMessage: s.last_message || '',
        }));
      }
    } catch { /* offline */ }
  }

  let targetThreadId = threadIdParam || S.threadId;
  if (!targetThreadId) {
    if (S.threads.length > 0) {
      targetThreadId = S.threads[0].id;
    } else {
      try {
        const r = await apiCreateSession();
        targetThreadId = r.thread_id;
        S.threads.unshift({ id: targetThreadId, title: 'New Chat', ts: new Date(), createdAt: new Date(), lastMessage: '' });
      } catch {
        targetThreadId = crypto.randomUUID();
        S.threads.unshift({ id: targetThreadId, title: 'Offline', ts: new Date(), createdAt: new Date(), lastMessage: '' });
      }
    }
  } else if (!S.threads.some(t => t.id === targetThreadId)) {
    // Deep link to a thread not yet in our local list (e.g. shared link opened fresh) — placeholder entry
    S.threads.unshift({ id: targetThreadId, title: 'Shared Chat', ts: new Date(), createdAt: new Date(), lastMessage: '' });
  }

  const threadChanged = targetThreadId !== S.threadId;
  S.threadId = targetThreadId;
  S.console = consoleForThread(S.threadId);
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
        <div class="flex-1 overflow-y-auto chat-scroll p-3 space-y-1" id="thread-list"></div>
      </aside>
      <section class="flex-1 flex flex-col min-w-0">
        <div id="chat-messages" class="flex-1 overflow-y-auto chat-scroll p-6 space-y-6 flex flex-col"></div>
        <div class="border-t border-outline-variant bg-surface-container-lowest p-4 shrink-0">
          <div class="flex items-center gap-3 max-w-[900px] mx-auto">
            <input id="chat-input" type="text" class="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-4 py-2.5 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all" placeholder="Type a command or ask a question..." autocomplete="off" spellcheck="false">
            <button id="btn-send" class="px-5 py-2.5 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed">Send</button>
          </div>
          <p class="text-[10px] text-on-surface-variant mt-2 text-center">[Enter] Kirim &middot; [Ctrl+L] Clear</p>
        </div>
      </section>
      <aside class="w-72 border-l border-outline-variant bg-surface-container-low flex flex-col shrink-0">
        <div class="p-4 border-b border-outline-variant">
          <span class="text-label-caps font-label-caps text-on-surface-variant">Active Network Agents</span>
        </div>
        <div id="agent-panel" class="flex-1 overflow-y-auto chat-scroll p-3 space-y-2"></div>
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
    <div class="bg-surface-container-lowest rounded-xl shadow-xl max-w-[500px] w-full mx-4 overflow-hidden">
      <div class="bg-amber-50 px-6 py-3 flex items-center gap-2 border-b border-amber-200">
        <span class="material-symbols-outlined text-amber-700">warning</span>
        <span class="text-label-caps font-label-caps text-amber-800">APPROVAL REQUIRED</span>
      </div>
      <div class="p-6">
        <h3 class="text-title-sm font-title-sm font-bold text-on-surface mb-2">Confirm System Operation</h3>
        <p class="text-body-sm text-on-surface-variant mb-4">An automated agent has requested permission to perform a high-impact task.</p>
        <div class="border border-outline-variant rounded-lg divide-y divide-outline-variant text-body-sm">
          <div class="flex justify-between px-4 py-2.5"><span class="text-label-caps font-label-caps text-on-surface-variant">AGENT</span><span id="m-agent" class="font-medium">—</span></div>
          <div class="flex justify-between px-4 py-2.5"><span class="text-label-caps font-label-caps text-on-surface-variant">ACTION</span><span id="m-action" class="font-data-mono text-data-mono">—</span></div>
          <div class="flex justify-between px-4 py-2.5"><span class="text-label-caps font-label-caps text-on-surface-variant">RISK LEVEL</span><span id="m-risk">—</span></div>
        </div>
      </div>
      <div class="px-6 pb-6 flex items-center justify-between">
        <span class="text-[10px] text-on-surface-variant">[Y] Approve &middot; [N] Reject</span>
        <div class="flex gap-3">
          <button id="btn-reject" class="px-4 py-2 border border-red-300 text-red-700 rounded-lg text-body-sm font-medium hover:bg-red-50 transition-colors">Reject</button>
          <button id="btn-approve" class="px-4 py-2 bg-green-700 text-white rounded-lg text-body-sm font-medium hover:bg-green-800 transition-colors">Approve</button>
        </div>
      </div>
    </div>
  </div>`;

  _chatEl = $('chat-messages');
  chatRenderThreads();
  chatRenderAgents();
  consoleRender();
  if (threadChanged || S.messages.length === 0) {
    await chatLoadHistory(S.threadId);
  } else {
    chatRenderMessages();
  }
  chatBindEvents();
  chatBindConsole();
}

function chatSyncUrl() {
  if (!S.threadId) return;
  const target = '#chat/' + encodeURIComponent(S.threadId);
  if (location.hash !== target) history.replaceState(null, '', target);
}

async function chatLoadHistory(threadId) {
  chatRenderMessages();
  try {
    const r = await apiGet('/api/threads/' + encodeURIComponent(threadId) + '/messages');
    S.messages = (r.messages || []).map(m => ({
      role: m.role, content: m.content, ts: new Date(), streaming: false,
    }));
  } catch { /* offline or new thread */ }
  chatRenderMessages();
}

function chatBindEvents() {
  const inp = $('chat-input'), btnS = $('btn-send'), btnN = $('btn-new-thread'), btnL = $('btn-copy-link');
  const btnA = $('btn-approve'), btnR = $('btn-reject');

  async function send() {
    const text = inp.value.trim();
    if (!text || S.chatState !== 'idle') return;
    inp.value = '';
    S.activeQuery = text;
    S.messages.push({ role: 'user', content: text, ts: new Date() });
    S.messages.push({ role: 'agent', content: '', ts: new Date(), streaming: true });
    chatResetAgents();
    chatStartElapsed();
    _requestStartTs = Date.now();
    _lastEventTs = null;
    S.chatState = 'streaming';
    chatRenderMessages(); chatUpdateUI();
    try { await apiStreamChat(S.threadId, text, chatHandleEvent); }
    catch (e) { chatHandleEvent('error', e.message || 'Connection failed'); }
    chatFinish();
  }

  btnS.onclick = send;
  inp.onkeydown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
    if (e.key === 'l' && e.ctrlKey) { e.preventDefault(); chatClear(); }
  };
  btnN.onclick = async () => {
    try {
      const r = await apiCreateSession();
      S.threadId = r.thread_id;
      S.threads.unshift({ id: r.thread_id, title: 'New Chat', ts: new Date(), createdAt: new Date(), lastMessage: '' });
    } catch { S.threadId = crypto.randomUUID(); }
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
  btnA.onclick = () => chatResolveApproval('approved');
  btnR.onclick = () => chatResolveApproval('rejected');

  document.addEventListener('keydown', function _ak(e) {
    if (S.chatState !== 'approval') return;
    if (e.key === 'y' || e.key === 'Y') chatResolveApproval('approved');
    if (e.key === 'n' || e.key === 'N') chatResolveApproval('rejected');
  });
}

function chatHandleEvent(type, content) {
  const last = S.messages[S.messages.length - 1];
  if (type === 'ai') {
    if (last && last.role === 'agent') last.content += (last.content ? '\n' : '') + content;
  } else if (type === 'approval_required') {
    S.chatState = 'approval';
    try { S.pendingApproval = JSON.parse(content); } catch { S.pendingApproval = { action: content }; }
    chatShowApproval();
  } else {
    consolePush(type, content);
    chatUpdateAgentFromEvent(type, content);
    if (type === 'tool_call') S.toolCount++;
  }
  chatRenderMessages(); chatUpdateUI();
}

async function chatResolveApproval(decision) {
  chatHideApproval();
  consolePush('routing', `Operator: ${decision === 'approved' ? 'DISETUJUI' : 'DITOLAK'}`);
  _requestStartTs = Date.now();
  _lastEventTs = null;
  S.chatState = 'streaming';
  chatRenderMessages();
  try { await apiApprove(S.threadId, decision, chatHandleEvent); }
  catch (e) { chatHandleEvent('error', e.message); }
  chatFinish();
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
  AGENTS.forEach(a => { if (S.agents[a.alias].state === 'running') S.agents[a.alias].state = 'done'; });
  chatRenderMessages(); chatRenderAgents(); chatUpdateUI();
}

function chatClear() {
  S.messages = []; S.activeQuery = ''; S.toolCount = 0; S.chatState = 'idle';
  Object.keys(S.agents).forEach(k => { S.agents[k] = { state: 'standby', detail: '', toolCount: 0 }; });
  chatStopElapsed();
  chatRenderMessages(); chatRenderAgents(); chatRenderThreads(); chatUpdateUI();
}

function chatResetAgents() {
  Object.keys(S.agents).forEach(k => { S.agents[k] = { state: 'standby', detail: '', toolCount: 0 }; });
  S.agents.bambang = { state: 'running', detail: 'routing...', toolCount: 0 };
  S.toolCount = 0;
  chatRenderAgents();
}

function chatUpdateAgentFromEvent(type, content) {
  const m = content.match(/^\[(\w+)\]\s*(.*)/);
  if (!m) return;
  const alias = ROLE_TO_ALIAS[m[1]] || m[1];
  const msg = m[2];
  if (type === 'routing' && msg.startsWith('→')) {
    if (S.agents[alias]) S.agents[alias].state = 'done';
    const tgt = msg.match(/→\s*(\w+)/)?.[1];
    const ta = ROLE_TO_ALIAS[tgt];
    if (ta && S.agents[ta]) { S.agents[ta].state = 'running'; S.agents[ta].detail = ''; }
  } else if (type === 'tool_call') {
    if (S.agents[alias]) { S.agents[alias].state = 'running'; S.agents[alias].detail = msg.split('(')[0]; S.agents[alias].toolCount++; }
  } else if (type === 'error') {
    if (S.agents[alias]) S.agents[alias].state = 'failed';
  }
  chatRenderAgents();
}

function chatRenderMessages() {
  const el = $('chat-messages'); if (!el) return;
  if (S.messages.length === 0) {
    el.innerHTML = `<div class="flex-1 flex flex-col items-center justify-center text-center">
      <span class="material-symbols-outlined text-5xl text-outline-variant mb-3">hub</span>
      <h3 class="text-title-sm font-title-sm text-primary mb-1">LLMNetOps</h3>
      <p class="text-body-sm text-on-surface-variant max-w-xs">Type a command to start an operational session with the AI agent network.</p>
    </div>`;
    return;
  }
  el.innerHTML = S.messages.map(m => m.role === 'user' ? chatUserMsg(m) : chatAgentMsg(m)).join('');
  el.scrollTop = el.scrollHeight;
}

function chatUserMsg(m) {
  return `<div class="flex flex-col items-end max-w-[85%] self-end">
    <div class="flex items-center gap-2 mb-1">
      <span class="text-[10px] text-outline tabular-nums">${fmtTime(m.ts)}</span>
      <span class="bg-primary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">ANDA</span>
    </div>
    <div class="bg-primary-container text-white p-4 rounded-xl rounded-tr-none shadow-sm">
      <p class="text-body-md">${esc(m.content)}</p>
    </div>
  </div>`;
}

function chatAgentMsg(m) {
  const typing = m.streaming && !m.content ? `<div class="flex items-center gap-1 mt-2">
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div></div>` : '';
  const txt = m.content ? `<div class="md text-body-md text-on-surface leading-relaxed">${renderMarkdown(m.content)}</div>` : '';
  return `<div class="flex flex-col items-start max-w-[90%] self-start">
    <div class="flex items-center gap-2 mb-1">
      <span class="bg-secondary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">AGENT</span>
      <span class="text-[10px] text-outline tabular-nums">${fmtTime(m.ts)}</span>
    </div>
    <div class="bg-surface-container-lowest p-4 rounded-xl rounded-tl-none border border-outline-variant shadow-sm w-full">
      ${txt}${typing}
    </div>
  </div>`;
}

function chatEventLine(ev, isActive) {
  const c = {
    routing: { tag: '#fcd34d', l: 'ROUTING' },
    tool_call: { tag: '#60a5fa', l: 'TOOL_CALL' },
    tool_result: { tag: '#4ade80', l: 'RESULT' },
    approval_required: { tag: '#fbbf24', l: 'APPROVAL' },
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
      try { await apiPut('/api/threads/' + encodeURIComponent(threadId), { title }); }
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
    await apiDelete('/api/threads/' + encodeURIComponent(threadId));
  } catch (e) {
    await alertDialog('Gagal menghapus thread: ' + e.message, 'Terjadi Kesalahan');
    return;
  }

  S.threads = S.threads.filter(x => x.id !== threadId);
  delete _consoleStore[threadId];
  consoleSave();

  if (threadId !== S.threadId) {
    chatRenderThreads();
    return;
  }

  if (S.threads.length > 0) {
    await chatSwitchThread(S.threads[0].id);
  } else {
    try {
      const r = await apiCreateSession();
      S.threadId = r.thread_id;
      S.threads.unshift({ id: r.thread_id, title: 'New Chat', ts: new Date(), createdAt: new Date(), lastMessage: '' });
    } catch { S.threadId = crypto.randomUUID(); }
    S.console = consoleForThread(S.threadId);
    chatSyncUrl();
    chatClear();
    consoleRender();
  }
}
window.chatDeleteThread = chatDeleteThread;

async function chatSwitchThread(threadId) {
  if (threadId === S.threadId) return;
  S.threadId = threadId;
  S.console = consoleForThread(threadId);
  chatSyncUrl();
  S.activeQuery = '';
  S.chatState = 'idle';
  Object.keys(S.agents).forEach(k => { S.agents[k] = { state: 'standby', detail: '', toolCount: 0 }; });
  chatStopElapsed();
  chatRenderAgents();
  chatRenderThreads();
  chatUpdateUI();
  consoleRender();
  S.messages = [];
  await chatLoadHistory(threadId);
}
window.chatSwitchThread = chatSwitchThread;

function chatRenderAgents() {
  const el = $('agent-panel'); if (!el) return;
  el.innerHTML = AGENTS.map(a => agentCardHtml(a.alias, a.role, S.agents[a.alias].state, S.agents[a.alias].detail)).join('');
}

function chatShowApproval() {
  const o = $('approval-overlay'); if (!o) return; o.classList.remove('hidden');
  const p = S.pendingApproval || {};
  const ae = $('m-agent'), ac = $('m-action'), ar = $('m-risk');
  if (ae) ae.textContent = p.agent || 'config_agent';
  if (ac) ac.textContent = p.action || '—';
  if (ar) {
    const lv = (p.risk_level || 'medium').toUpperCase();
    const cls = lv === 'HIGH' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200';
    ar.innerHTML = `<span class="px-2 py-0.5 text-[10px] font-bold border rounded-full ${cls}">${lv}</span>`;
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
    if (el) { const mm = String(Math.floor(S.elapsed / 60)).padStart(2, '0'), ss = String(S.elapsed % 60).padStart(2, '0'); el.textContent = `⏱ ${mm}:${ss}`; }
  }, 1000);
}

function chatStopElapsed() { if (_elapsedIv) { clearInterval(_elapsedIv); _elapsedIv = null; } }
function chatUpdateUI() { const q = $('active-query'); if (q) q.textContent = S.activeQuery || '—'; }

export function chatUnmount() { chatStopElapsed(); }
