import { store, AGENTS, ROLE_TO_ALIAS, makeAgentStates } from '../store.js'
import { createSession, streamChat, submitApproval } from '../api.js'
import { agentCard, escapeHtml, formatTime } from '../components.js'

let chatContainer = null
let elapsedInterval = null

export async function mount(container) {
  if (!store.threadId) {
    try {
      const { thread_id } = await createSession()
      store.threadId = thread_id
      store.threads.push({ id: thread_id, title: 'New Chat', ts: new Date() })
    } catch {
      store.threadId = crypto.randomUUID()
      store.threads.push({ id: store.threadId, title: 'Offline', ts: new Date() })
    }
  }
  render(container)
  chatContainer = container.querySelector('#chat-messages')
  scrollToBottom()
}

export function unmount() {
  stopElapsed()
}

function render(container) {
  container.innerHTML = `
    <div class="flex h-[calc(100vh-56px)] overflow-hidden">
      <!-- Thread Sidebar -->
      <aside class="w-64 border-r border-outline-variant bg-surface-container-low flex flex-col shrink-0">
        <div class="p-4 border-b border-outline-variant flex justify-between items-center">
          <span class="text-label-caps font-label-caps text-on-surface-variant">Active Threads</span>
          <button id="btn-new-thread" class="material-symbols-outlined text-sm text-primary hover:bg-surface-container rounded p-1 transition-colors">add_box</button>
        </div>
        <div class="flex-1 overflow-y-auto chat-scroll p-3 space-y-1" id="thread-list"></div>
      </aside>

      <!-- Chat Area -->
      <section class="flex-1 flex flex-col min-w-0">
        <div id="chat-messages" class="flex-1 overflow-y-auto chat-scroll p-6 space-y-6 flex flex-col"></div>

        <!-- Input Bar -->
        <div class="border-t border-outline-variant bg-surface-container-lowest p-4 shrink-0">
          <div class="flex items-center gap-3 max-w-[900px] mx-auto">
            <input id="chat-input" type="text"
              class="flex-1 bg-surface-container-low border border-outline-variant rounded-lg px-4 py-2.5 text-body-md text-on-surface focus:ring-1 focus:ring-primary focus:border-primary outline-none transition-all"
              placeholder="Type a command or ask a question..." autocomplete="off" spellcheck="false">
            <button id="btn-send"
              class="px-5 py-2.5 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity disabled:opacity-40 disabled:cursor-not-allowed">
              Send
            </button>
          </div>
          <p class="text-[10px] text-on-surface-variant mt-2 text-center">[Enter] Kirim &middot; [Ctrl+L] Clear chat</p>
        </div>
      </section>

      <!-- Agent Panel -->
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

    <!-- Approval Modal -->
    <div id="approval-overlay" class="hidden fixed inset-0 bg-black/30 backdrop-blur-sm z-[200] flex items-center justify-center">
      <div class="bg-surface-container-lowest rounded-xl shadow-xl max-w-[500px] w-full mx-4 overflow-hidden">
        <div class="bg-amber-50 px-6 py-3 flex items-center gap-2 border-b border-amber-200">
          <span class="material-symbols-outlined text-amber-700">warning</span>
          <span class="text-label-caps font-label-caps text-amber-800">APPROVAL REQUIRED</span>
        </div>
        <div class="p-6">
          <h3 class="text-title-sm font-title-sm font-bold text-on-surface mb-2">Confirm System Operation</h3>
          <p class="text-body-sm text-on-surface-variant mb-4">An automated agent has requested permission to perform a high-impact network task.</p>
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
    </div>`

  renderThreadList()
  renderAgentPanel()
  renderMessages()
  bindEvents(container)
}

function bindEvents(container) {
  const input = container.querySelector('#chat-input')
  const btnSend = container.querySelector('#btn-send')
  const btnNewThread = container.querySelector('#btn-new-thread')
  const btnApprove = container.querySelector('#btn-approve')
  const btnReject = container.querySelector('#btn-reject')

  async function send() {
    const text = input.value.trim()
    if (!text || store.chatState !== 'idle') return
    input.value = ''

    store.activeQuery = text
    store.messages.push({ role: 'user', content: text, ts: new Date(), events: [] })
    store.messages.push({ role: 'agent', content: '', ts: new Date(), events: [], streaming: true })
    resetAgentsForQuery()
    startElapsed()
    store.chatState = 'streaming'
    renderMessages()
    updateUI()

    try {
      await streamChat(store.threadId, text, handleEvent)
    } catch (err) {
      handleEvent('error', err.message || 'Connection failed')
    }
    finishStreaming()
  }

  btnSend.addEventListener('click', send)
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
    if (e.key === 'l' && e.ctrlKey) { e.preventDefault(); clearChat() }
  })

  btnNewThread.addEventListener('click', async () => {
    try {
      const { thread_id } = await createSession()
      store.threadId = thread_id
      store.threads.push({ id: thread_id, title: 'New Chat', ts: new Date() })
    } catch {
      store.threadId = crypto.randomUUID()
    }
    clearChat()
  })

  btnApprove.addEventListener('click', () => resolveApproval('approved'))
  btnReject.addEventListener('click', () => resolveApproval('rejected'))

  document.addEventListener('keydown', function _approvalKeys(e) {
    if (store.chatState !== 'approval') return
    if (e.key === 'y' || e.key === 'Y') resolveApproval('approved')
    if (e.key === 'n' || e.key === 'N') resolveApproval('rejected')
  })
}

function handleEvent(type, content) {
  const msgs = store.messages
  const last = msgs[msgs.length - 1]
  if (!last || last.role !== 'agent') return

  if (type === 'ai') {
    last.content += (last.content ? '\n' : '') + content
  } else if (type === 'approval_required') {
    store.chatState = 'approval'
    try { store.pendingApproval = JSON.parse(content) } catch { store.pendingApproval = { action: content } }
    showApprovalModal()
  } else {
    last.events.push({ type, content, ts: new Date() })
    updateAgentFromEvent(type, content)
    store.toolCount += (type === 'tool_call' ? 1 : 0)
  }
  renderMessages()
  updateUI()
}

async function resolveApproval(decision) {
  hideApprovalModal()
  const last = store.messages[store.messages.length - 1]
  if (last) last.events.push({ type: 'routing', content: `Operator: ${decision === 'approved' ? 'DISETUJUI' : 'DITOLAK'}`, ts: new Date() })
  store.chatState = 'streaming'
  renderMessages()

  try {
    await submitApproval(store.threadId, decision, handleEvent)
  } catch (err) {
    handleEvent('error', err.message)
  }
  finishStreaming()
}

function finishStreaming() {
  const last = store.messages[store.messages.length - 1]
  if (last) last.streaming = false
  store.chatState = 'idle'
  stopElapsed()
  AGENTS.forEach(a => {
    const s = store.agents[a.alias]
    if (s.state === 'running') s.state = 'done'
  })
  renderMessages()
  renderAgentPanel()
  updateUI()
}

function clearChat() {
  store.messages = []
  store.activeQuery = ''
  store.toolCount = 0
  store.chatState = 'idle'
  Object.keys(store.agents).forEach(k => { store.agents[k] = { state: 'standby', detail: '', toolCount: 0 } })
  stopElapsed()
  renderMessages()
  renderAgentPanel()
  renderThreadList()
  updateUI()
}

// ── Agent state tracking ──────────────────────────────────────────────────

function resetAgentsForQuery() {
  Object.keys(store.agents).forEach(k => { store.agents[k] = { state: 'standby', detail: '', toolCount: 0 } })
  store.agents.bambang.state = 'running'
  store.agents.bambang.detail = 'routing...'
  store.toolCount = 0
}

function updateAgentFromEvent(type, content) {
  const m = content.match(/^\[(\w+)\]\s*(.*)/)
  if (!m) return
  const [, source, msg] = m

  const alias = ROLE_TO_ALIAS[source] || source

  if (type === 'routing' && msg.startsWith('→')) {
    if (store.agents[alias]) store.agents[alias].state = 'done'
    const target = msg.match(/→\s*(\w+)/)?.[1]
    const tAlias = ROLE_TO_ALIAS[target]
    if (tAlias && store.agents[tAlias]) {
      store.agents[tAlias].state = 'running'
      store.agents[tAlias].detail = ''
    }
  } else if (type === 'tool_call') {
    if (store.agents[alias]) {
      store.agents[alias].state = 'running'
      store.agents[alias].detail = msg.split('(')[0]
      store.agents[alias].toolCount++
    }
  } else if (type === 'error') {
    if (store.agents[alias]) store.agents[alias].state = 'failed'
  }
  renderAgentPanel()
}

// ── Rendering ─────────────────────────────────────────────────────────────

function renderMessages() {
  const el = document.getElementById('chat-messages')
  if (!el) return

  if (store.messages.length === 0) {
    el.innerHTML = `
      <div class="flex-1 flex flex-col items-center justify-center text-center">
        <span class="material-symbols-outlined text-5xl text-outline-variant mb-3">hub</span>
        <h3 class="text-title-sm font-title-sm text-primary mb-1">LLMNetOps</h3>
        <p class="text-body-sm text-on-surface-variant max-w-xs">Type a command to start an operational session with the AI agent network.</p>
      </div>`
    return
  }

  el.innerHTML = store.messages.map(msg => {
    if (msg.role === 'user') return renderUserMsg(msg)
    return renderAgentMsg(msg)
  }).join('')
  scrollToBottom()
}

function renderUserMsg(msg) {
  return `
    <div class="flex flex-col items-end max-w-[85%] self-end">
      <div class="flex items-center gap-2 mb-1">
        <span class="text-[10px] text-outline tabular-nums">${formatTime(msg.ts)}</span>
        <span class="bg-primary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">ANDA</span>
      </div>
      <div class="bg-primary-container text-white p-4 rounded-xl rounded-tr-none shadow-sm">
        <p class="text-body-md">${escapeHtml(msg.content)}</p>
      </div>
    </div>`
}

function renderAgentMsg(msg) {
  const eventsHtml = msg.events.length > 0 ? `
    <div class="bg-on-background rounded-lg p-3 font-data-mono text-data-mono space-y-1.5 mb-3">
      ${msg.events.map(renderEvent).join('')}
    </div>` : ''

  const typingHtml = msg.streaming && !msg.content ? `
    <div class="flex items-center gap-1 mt-2">
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
      <div class="w-2 h-2 bg-secondary rounded-full bouncing-dot"></div>
    </div>` : ''

  const textHtml = msg.content ? `<div class="text-body-md text-on-surface whitespace-pre-wrap leading-relaxed">${escapeHtml(msg.content)}</div>` : ''

  return `
    <div class="flex flex-col items-start max-w-[90%] self-start">
      <div class="flex items-center gap-2 mb-1">
        <span class="bg-secondary text-white px-2 py-0.5 rounded text-[10px] font-bold tracking-wider">AGENT</span>
        <span class="text-[10px] text-outline tabular-nums">${formatTime(msg.ts)}</span>
      </div>
      <div class="bg-surface-container-lowest p-4 rounded-xl rounded-tl-none border border-outline-variant shadow-sm w-full">
        ${eventsHtml}${textHtml}${typingHtml}
      </div>
    </div>`
}

function renderEvent(ev) {
  const colors = {
    routing:     { tag: '#fcd34d', icon: 'ROUTING' },
    tool_call:   { tag: '#60a5fa', icon: 'TOOL_CALL' },
    tool_result: { tag: '#4ade80', icon: 'RESULT' },
    error:       { tag: '#f87171', icon: 'ERROR' },
  }
  const c = colors[ev.type] || { tag: '#94a3b8', icon: ev.type.toUpperCase() }
  return `
    <div class="flex items-start gap-2">
      <span class="font-bold whitespace-nowrap" style="color:${c.tag}">[${c.icon}]</span>
      <span class="text-surface-variant break-all">${escapeHtml(ev.content)}</span>
    </div>`
}

function renderThreadList() {
  const el = document.getElementById('thread-list')
  if (!el) return
  el.innerHTML = store.threads.map(t => {
    const active = t.id === store.threadId
    return `
      <div class="${active ? 'bg-white border border-outline-variant shadow-sm' : 'hover:bg-surface-container'} p-3 rounded cursor-pointer transition-colors" data-thread="${t.id}">
        <p class="${active ? 'font-bold text-primary' : 'font-medium text-on-surface-variant'} text-xs truncate">${escapeHtml(t.title)}</p>
        <p class="text-[10px] ${active ? 'text-on-surface-variant' : 'text-outline'} mt-1">${formatTime(t.ts)}</p>
      </div>`
  }).join('')
}

function renderAgentPanel() {
  const el = document.getElementById('agent-panel')
  if (!el) return
  el.innerHTML = AGENTS.map(a => {
    const s = store.agents[a.alias] || { state: 'standby', detail: '' }
    return agentCard(a.alias, a.role, s.state, s.detail)
  }).join('')
}

function scrollToBottom() {
  if (chatContainer) chatContainer.scrollTop = chatContainer.scrollHeight
}

function showApprovalModal() {
  const overlay = document.getElementById('approval-overlay')
  if (!overlay) return
  overlay.classList.remove('hidden')
  const p = store.pendingApproval || {}
  const agentEl = document.getElementById('m-agent')
  const actionEl = document.getElementById('m-action')
  const riskEl = document.getElementById('m-risk')
  if (agentEl) agentEl.textContent = p.agent || 'config_agent'
  if (actionEl) actionEl.textContent = p.action || '—'
  if (riskEl) {
    const level = (p.risk_level || 'medium').toUpperCase()
    const cls = level === 'HIGH' ? 'bg-red-50 text-red-700 border-red-200' : 'bg-amber-50 text-amber-700 border-amber-200'
    riskEl.innerHTML = `<span class="px-2 py-0.5 text-[10px] font-bold border rounded-full ${cls}">${level}</span>`
  }
}

function hideApprovalModal() {
  const overlay = document.getElementById('approval-overlay')
  if (overlay) overlay.classList.add('hidden')
  store.pendingApproval = null
}

// ── Elapsed timer ─────────────────────────────────────────────────────────

function startElapsed() {
  store.elapsed = 0
  stopElapsed()
  const start = Date.now()
  elapsedInterval = setInterval(() => {
    store.elapsed = Math.floor((Date.now() - start) / 1000)
    const el = document.getElementById('elapsed-display')
    if (el) {
      const m = String(Math.floor(store.elapsed / 60)).padStart(2, '0')
      const s = String(store.elapsed % 60).padStart(2, '0')
      el.textContent = `⏱ ${m}:${s}`
    }
  }, 1000)
}

function stopElapsed() {
  if (elapsedInterval) { clearInterval(elapsedInterval); elapsedInterval = null }
}

function updateUI() {
  const q = document.getElementById('active-query')
  if (q) q.textContent = store.activeQuery || '—'
}
