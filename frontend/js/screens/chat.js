import { AGENTS, ROLE_TO_ALIAS } from '../config.js';
import { S } from '../state.js';
import { $, esc, fmtTime, agentCardHtml, loadingHtml } from '../utils.js';
import { apiGet, apiCreateSession, apiStreamChat, apiApprove } from '../api.js';

let _chatEl = null;
let _elapsedIv = null;

export async function screenChat(c) {
  if (S.threads.length === 0) {
    try {
      const r = await apiGet('/api/sessions');
      if (r.sessions && r.sessions.length > 0) {
        S.threads = r.sessions.map(s => ({
          id: s.thread_id,
          title: s.title || 'New Chat',
          ts: new Date(s.updated_at || s.created_at),
          lastMessage: s.last_message || '',
        }));
        if (!S.threadId) S.threadId = S.threads[0].id;
      }
    } catch { /* offline */ }
  }
  if (!S.threadId) {
    try {
      const r = await apiCreateSession();
      S.threadId = r.thread_id;
      S.threads.unshift({ id: r.thread_id, title: 'New Chat', ts: new Date(), lastMessage: '' });
    } catch {
      S.threadId = crypto.randomUUID();
      S.threads.unshift({ id: S.threadId, title: 'Offline', ts: new Date(), lastMessage: '' });
    }
  }

  c.innerHTML = `
  <div class="flex h-[calc(100vh-56px)] overflow-hidden">
    <aside class="w-64 border-r border-outline-variant bg-surface-container-low flex flex-col shrink-0">
      <div class="p-4 border-b border-outline-variant flex justify-between items-center">
        <span class="text-label-caps font-label-caps text-on-surface-variant">Active Threads</span>
        <button id="btn-new-thread" class="material-symbols-outlined text-sm text-primary hover:bg-surface-container rounded p-1 transition-colors">add_box</button>
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
  if (S.messages.length === 0) {
    await chatLoadHistory(S.threadId);
  } else {
    chatRenderMessages();
  }
  chatBindEvents();
}

async function chatLoadHistory(threadId) {
  chatRenderMessages();
  try {
    const r = await apiGet('/api/threads/' + encodeURIComponent(threadId) + '/messages');
    S.messages = (r.messages || []).map(m => ({
      role: m.role, content: m.content, ts: new Date(), events: [], streaming: false,
    }));
  } catch { /* offline or new thread */ }
  chatRenderMessages();
}

function chatBindEvents() {
  const inp = $('chat-input'), btnS = $('btn-send'), btnN = $('btn-new-thread');
  const btnA = $('btn-approve'), btnR = $('btn-reject');

  async function send() {
    const text = inp.value.trim();
    if (!text || S.chatState !== 'idle') return;
    inp.value = '';
    S.activeQuery = text;
    S.messages.push({ role: 'user', content: text, ts: new Date(), events: [] });
    S.messages.push({ role: 'agent', content: '', ts: new Date(), events: [], streaming: true });
    chatResetAgents();
    chatStartElapsed();
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
      S.threads.unshift({ id: r.thread_id, title: 'New Chat', ts: new Date(), lastMessage: '' });
    } catch { S.threadId = crypto.randomUUID(); }
    chatClear();
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
  if (!last || last.role !== 'agent') return;
  if (type === 'ai') {
    last.content += (last.content ? '\n' : '') + content;
  } else if (type === 'approval_required') {
    S.chatState = 'approval';
    try { S.pendingApproval = JSON.parse(content); } catch { S.pendingApproval = { action: content }; }
    chatShowApproval();
  } else {
    last.events.push({ type, content, ts: new Date() });
    chatUpdateAgentFromEvent(type, content);
    if (type === 'tool_call') S.toolCount++;
  }
  chatRenderMessages(); chatUpdateUI();
}

async function chatResolveApproval(decision) {
  chatHideApproval();
  const last = S.messages[S.messages.length - 1];
  if (last) last.events.push({ type: 'routing', content: `Operator: ${decision === 'approved' ? 'DISETUJUI' : 'DITOLAK'}`, ts: new Date() });
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
  const evHtml = m.events.length ? `<div class="bg-on-background rounded-lg p-3 font-data-mono text-data-mono space-y-1.5 mb-3">
    ${m.events.map(chatEventLine).join('')}</div>` : '';
  const typing = m.streaming && !m.content ? `<div class="flex items-center gap-1 mt-2">
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div></div>` : '';
  const txt = m.content ? `<div class="text-body-md text-on-surface whitespace-pre-wrap leading-relaxed">${esc(m.content)}</div>` : '';
  return `<div class="flex flex-col items-start max-w-[90%] self-start">
    <div class="flex items-center gap-2 mb-1">
      <span class="bg-secondary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">AGENT</span>
      <span class="text-[10px] text-outline tabular-nums">${fmtTime(m.ts)}</span>
    </div>
    <div class="bg-surface-container-lowest p-4 rounded-xl rounded-tl-none border border-outline-variant shadow-sm w-full">
      ${evHtml}${txt}${typing}
    </div>
  </div>`;
}

function chatEventLine(ev) {
  const c = {
    routing: { tag: '#fcd34d', l: 'ROUTING' },
    tool_call: { tag: '#60a5fa', l: 'TOOL_CALL' },
    tool_result: { tag: '#4ade80', l: 'RESULT' },
    error: { tag: '#f87171', l: 'ERROR' },
  }[ev.type] || { tag: '#94a3b8', l: ev.type.toUpperCase() };
  return `<div class="flex items-start gap-2"><span class="font-bold whitespace-nowrap" style="color:${c.tag}">[${c.l}]</span><span class="text-surface-variant break-all">${esc(ev.content)}</span></div>`;
}

function chatRenderThreads() {
  const el = $('thread-list'); if (!el) return;
  el.innerHTML = S.threads.map(t => {
    const a = t.id === S.threadId;
    const preview = t.lastMessage ? `<p class="text-[10px] ${a ? 'text-on-surface-variant' : 'text-outline'} mt-0.5 truncate">${esc(t.lastMessage)}</p>` : '';
    return `<div data-tid="${esc(t.id)}" class="${a ? 'bg-white border border-outline-variant shadow-sm' : 'hover:bg-surface-container'} p-3 rounded cursor-pointer transition-colors" onclick="chatSwitchThread('${esc(t.id)}')">
      <p class="${a ? 'font-bold text-primary' : 'font-medium text-on-surface-variant'} text-xs truncate">${esc(t.title)}</p>
      ${preview}
      <p class="text-[10px] ${a ? 'text-primary/60' : 'text-outline'} mt-0.5 tabular-nums">${fmtTime(t.ts)}</p>
    </div>`;
  }).join('');
}

async function chatSwitchThread(threadId) {
  if (threadId === S.threadId) return;
  S.threadId = threadId;
  S.activeQuery = '';
  S.chatState = 'idle';
  Object.keys(S.agents).forEach(k => { S.agents[k] = { state: 'standby', detail: '', toolCount: 0 }; });
  chatStopElapsed();
  chatRenderAgents();
  chatRenderThreads();
  chatUpdateUI();
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
