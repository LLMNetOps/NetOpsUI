// NetOps Agent adapter (the palapa-agent REST API, palapa/gateway/api.py).
//
// NetOps Agent's POST /chat is stateless: the client sends the whole conversation
// every turn and nothing is persisted per thread by the agent. Threads and their
// messages are therefore stored by the NetOpsUI manager (/api/threads), so every
// operator sees the same list. The manager also makes the /chat call itself
// (server/runs.py), so a run and its saved answer survive a page refresh.
// NetOps Agent has no approval flow (its network tools are read-only) and no stop
// endpoint — Stop only cuts the manager's stream; the agent loop on the server
// keeps running until it finishes on its own.
import { http, ensureOk, readSSE, uuid, toDate } from './common.js';
import { mgr } from '../manager.js';

const BASE = '/backend/netops';
const LEGACY_KEYS = ['llmnetops-netops-threads-v1', 'llmnetops-palapa-threads-v1']; // browser-only storage used before
const IMPORTED_KEY = 'llmnetops-netops-threads-imported';
const CLIENT_KEY = 'llmnetops-client-name';

const _controllers = {}; // threadId → AbortController of the in-flight /chat

// Label shown next to a thread so operators can tell whose chat it is.
function clientName() {
  try {
    let n = localStorage.getItem(CLIENT_KEY);
    if (!n) { n = 'user-' + uuid().slice(0, 4); localStorage.setItem(CLIENT_KEY, n); }
    return n;
  } catch { return ''; }
}

function summary(t) {
  return {
    id: t.id,
    title: t.title,
    createdAt: new Date(t.created_at),
    updatedAt: new Date(t.updated_at),
    lastMessage: t.last_message || '',
    owner: t.owner || '',
    running: !!t.running,
  };
}

// One-time move of this browser's old localStorage threads to the server.
async function importLegacy() {
  try {
    if (localStorage.getItem(IMPORTED_KEY)) return;
    const raw = LEGACY_KEYS.map(k => localStorage.getItem(k)).find(Boolean);
    const threads = raw ? Object.values(JSON.parse(raw) || {}) : [];
    if (threads.length) await mgr('/threads/import', { method: 'POST', body: { backend: 'netops', client: clientName(), threads } });
    localStorage.setItem(IMPORTED_KEY, '1');
  } catch { /* retried on the next list */ }
}

export const netops = {
  id: 'netops',
  label: 'NetOps Agent',
  shortLabel: 'NetOps Agent',
  description: 'Agent lokal berbasis Ollama dengan network tools read-only (Netmiko), skills, dan delegasi ke child agent.',
  capabilities: {
    approval: false,
    stop: 'abort',        // only cuts the stream; the server-side run is not interrupted
    resume: true,         // a running thread can be re-attached (refresh, other operator)
    serverThreads: true,  // threads are stored by the manager, shared by all operators
    devices: true,        // GET/POST /devices list and register nodes update and delete them
    activity: true,       // GET /turns: per-turn tool calls, errors, timeouts
  },

  // Recent agent turns from the trace store, newest first.
  async listActivity(limit = 100) {
    const rows = (await http(BASE, `/turns?limit=${limit}`)) || [];
    return rows.map(t => ({
      sessionId: t.session_id,
      at: toDate(t.timestamp),
      message: t.user_message || '',
      toolCalls: t.tool_call_count || 0,
      errors: t.error_count || 0,
      timeouts: t.timeout_count || 0,
      durationS: t.tool_duration_s || 0,
    })).sort((a, b) => (b.at || 0) - (a.at || 0));
  },

  async health() {
    const h = await http(BASE, '/health');
    return { ok: h?.status === 'ok', model: h?.model || '—', detail: h?.base_url || '' };
  },

  async listThreads() {
    await importLegacy();
    return (await mgr('/threads?backend=netops')).threads.map(summary);
  },

  async createThread() {
    return summary(await mgr('/threads', { method: 'POST', body: { id: uuid(), backend: 'netops', client: clientName() } }));
  },

  async loadMessages(id) {
    return (await mgr(`/threads/${encodeURIComponent(id)}/messages`)).messages.map(m => ({ role: m.role, content: m.content, ts: new Date(m.created_at) }));
  },

  async renameThread(id, title) {
    await mgr(`/threads/${encodeURIComponent(id)}`, { method: 'PATCH', body: { title } });
  },

  async deleteThread(id) {
    await mgr(`/threads/${encodeURIComponent(id)}`, { method: 'DELETE' });
  },

  // The manager makes the /chat call and stores the answer, so a page refresh
  // cannot lose it; the browser only watches the run's event stream.
  async send(threadId, text, emit) {
    await mgr(`/threads/${encodeURIComponent(threadId)}/run`, { method: 'POST', body: { text } });
    await this.resume(threadId, emit);
  },

  // Follows the thread's run from its first event (also used to re-attach after a refresh).
  async resume(threadId, emit) {
    const controller = new AbortController();
    _controllers[threadId] = controller;
    try {
      const r = await fetch(`/api/threads/${encodeURIComponent(threadId)}/events`, { signal: controller.signal });
      await ensureOk(r, '/events');
      await readSSE(r, ({ data }) => {
        if (!data || typeof data !== 'object' || data.type === 'done') return;
        emit(data);
      });
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
    } finally {
      delete _controllers[threadId];
    }
  },

  async stop(threadId) {
    try { return await mgr(`/threads/${encodeURIComponent(threadId)}/stop`, { method: 'POST' }); }
    catch { return { ok: false }; }
  },

  // Registers a device/node. Credentials in `device` go straight to the agent;
  // the response never echoes username/password back.
  async addDevice(device) {
    return http(BASE, '/devices', { method: 'POST', body: device });
  },

  async listDevices() {
    return (await http(BASE, '/devices')) || [];
  },

  // PUT /devices/{name} (assumed contract, not in the agent yet): replaces the
  // node's fields, with username/password optional (omitted = unchanged).
  async updateDevice(name, device) {
    return http(BASE, '/devices/' + encodeURIComponent(name), { method: 'PUT', body: device });
  },

  // DELETE /devices/{name}: removes the node from inventory.yaml (404 unknown name,
  // 400 duplicate names). Credentials in ~/.palapa/.env are left untouched.
  async deleteDevice(name) {
    return http(BASE, '/devices/' + encodeURIComponent(name), { method: 'DELETE' });
  },

  async listSkills() {
    const rows = await http(BASE, '/skills');
    return (rows || []).map(s => ({ name: s.name, description: s.description || '', tags: s.tags || [] }));
  },
};
