// NetOps Agent adapter (the palapa-agent REST API, palapa/gateway/api.py).
//
// NetOps Agent's POST /chat is stateless: the client sends the whole conversation
// every turn and nothing is persisted per thread on the server. Threads and
// their messages therefore live in this browser's localStorage. NetOps Agent has no
// approval flow (its network tools are read-only) and no stop endpoint — Stop
// aborts the SSE stream, but the agent loop on the server keeps running until
// it finishes on its own.
import { http, ensureOk, readSSE, uuid } from './common.js';

const BASE = '/backend/netops';
const STORAGE_KEY = 'llmnetops-netops-threads-v1';
const LEGACY_STORAGE_KEY = 'llmnetops-palapa-threads-v1'; // key used before the rename
const MAX_THREADS = 100;

let _threads = load();
const _controllers = {}; // threadId → AbortController of the in-flight /chat

function load() {
  try {
    return JSON.parse(localStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(LEGACY_STORAGE_KEY)) || {};
  } catch { return {}; }
}

function save() {
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(_threads)); } catch { /* storage full — in-memory only */ }
}

function summary(t) {
  return {
    id: t.id,
    title: t.title,
    createdAt: new Date(t.createdAt),
    updatedAt: new Date(t.updatedAt),
    lastMessage: t.lastMessage || '',
  };
}

function ensureThread(id) {
  if (!_threads[id]) {
    const now = Date.now();
    _threads[id] = { id, title: 'New Chat', createdAt: now, updatedAt: now, lastMessage: '', messages: [] };
  }
  return _threads[id];
}

export const netops = {
  id: 'netops',
  label: 'NetOps Agent',
  shortLabel: 'NetOps Agent',
  description: 'Agent lokal berbasis Ollama dengan network tools read-only (Netmiko), skills, dan delegasi ke child agent.',
  capabilities: {
    approval: false,
    stop: 'abort',        // only cuts the stream; the server-side run is not interrupted
    serverThreads: false, // threads are stored in the browser
    devices: true,        // POST /devices registers a node (no list/update/delete endpoint yet)
  },

  async health() {
    const h = await http(BASE, '/health');
    return { ok: h?.status === 'ok', model: h?.model || '—', detail: h?.base_url || '' };
  },

  async listThreads() {
    return Object.values(_threads).map(summary).sort((a, b) => b.updatedAt - a.updatedAt);
  },

  async createThread() {
    const ids = Object.keys(_threads);
    if (ids.length >= MAX_THREADS) {
      const oldest = ids.sort((a, b) => _threads[a].updatedAt - _threads[b].updatedAt)[0];
      delete _threads[oldest];
    }
    const t = ensureThread(uuid());
    save();
    return summary(t);
  },

  async loadMessages(id) {
    return (_threads[id]?.messages || []).map(m => ({ ...m }));
  },

  async renameThread(id, title) {
    ensureThread(id).title = title;
    save();
  },

  async deleteThread(id) {
    delete _threads[id];
    save();
  },

  async send(threadId, text, emit) {
    const t = ensureThread(threadId);
    const messages = [
      ...t.messages
        .filter(m => m.content)
        .map(m => ({ role: m.role === 'agent' ? 'assistant' : 'user', content: m.content })),
      { role: 'user', content: text },
    ];

    const controller = new AbortController();
    _controllers[threadId] = controller;
    let answer = '';
    try {
      const r = await fetch(BASE + '/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages }),
        signal: controller.signal,
      });
      await ensureOk(r, '/chat');
      await readSSE(r, ({ data }) => {
        if (!data || typeof data !== 'object') return;
        if (data.type === 'delta') {
          answer += data.content || '';
          emit({ type: 'delta', text: data.content || '' });
        } else if (data.type === 'tool_call') {
          // NetOps Agent reports a tool call once, after it has finished.
          emit({
            type: 'tool_end',
            name: data.name,
            detail: data.arguments || '',
            durationMs: (data.duration || 0) * 1000,
          });
        }
      });
    } catch (e) {
      if (e.name !== 'AbortError') throw e;
      emit({ type: 'stopped', text: 'Stream dihentikan operator. Proses di server NetOps Agent tetap berjalan sampai selesai, tetapi hasilnya tidak diterima.' });
    } finally {
      delete _controllers[threadId];
      t.messages.push({ role: 'user', content: text });
      t.messages.push({ role: 'agent', content: answer });
      if (t.title === 'New Chat') t.title = text.slice(0, 60);
      t.lastMessage = text.slice(0, 120);
      t.updatedAt = Date.now();
      save();
    }
  },

  async stop(threadId) {
    const c = _controllers[threadId];
    if (!c) return { ok: false };
    c.abort();
    return { ok: true };
  },

  // Registers a device/node. Credentials in `device` go straight to the agent;
  // the response never echoes username/password back.
  async addDevice(device) {
    return http(BASE, '/devices', { method: 'POST', body: device });
  },

  async listSkills() {
    const rows = await http(BASE, '/skills');
    return (rows || []).map(s => ({ name: s.name, description: s.description || '', tags: s.tags || [] }));
  },
};
