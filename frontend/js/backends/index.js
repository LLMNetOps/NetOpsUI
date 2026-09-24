// Backend registry. Exactly one backend is active at a time for the whole UI;
// the choice is made on the Settings screen and remembered per browser.
//
// Adapter contract (see netops.js / hermes.js):
//   id, label, shortLabel, description, capabilities { approval, stop, serverThreads, credential }
//   health()                      → { ok, model, detail }
//   listThreads()                 → [{ id, title, createdAt, updatedAt, lastMessage }]
//   createThread()                → thread summary
//   loadMessages(id)              → [{ role: 'user' | 'agent', content }]
//   renameThread(id, title), deleteThread(id)
//   send(threadId, text, emit)    → resolves when the turn ends; emit(event) with
//       { type: 'delta', text } | { type: 'tool_start', name, detail }
//       { type: 'tool_end', name, detail, durationMs, error }
//       { type: 'note' | 'thinking' | 'error' | 'stopped', text }
//       { type: 'approval', data: { action, description, choices, requestId } }
//   stop(threadId)                → { ok }
//   respondApproval(threadId, choice, requestId)   (only when capabilities.approval)
//   listSkills()                  → [{ name, description, tags }]
//   listJobs() / runJob(id) / pauseJob(id) / resumeJob(id)  (only when capabilities.jobs)
//   listActivity(limit)           → [{ at, message, toolCalls, errors, timeouts, durationS }] (only when capabilities.activity)
//   listDevices()                 → [{name, mgmt_ip, …}] (only when capabilities.devices)
//   addDevice(device)             → registered device (only when capabilities.devices)
//   updateDevice(name, device)    → updated device (only when capabilities.devices)
//   deleteDevice(name)            → void (only when capabilities.devices)
import { netops } from './netops.js';
import { hermes } from './hermes.js';

export const BACKENDS = { netops, hermes };

const STORAGE_KEY = 'llmnetops-backend';
const DEFAULT_BACKEND = 'netops';

function readChoice() {
  try {
    let v = localStorage.getItem(STORAGE_KEY);
    if (v === 'palapa') v = 'netops'; // id used before the rename
    return BACKENDS[v] ? v : DEFAULT_BACKEND;
  } catch {
    return DEFAULT_BACKEND;
  }
}

let _activeId = readChoice();

export function activeBackend() {
  return BACKENDS[_activeId];
}

export function setActiveBackend(id) {
  if (!BACKENDS[id]) throw new Error(`Backend tidak dikenal: ${id}`);
  _activeId = id;
  try { localStorage.setItem(STORAGE_KEY, id); } catch { /* per-session only */ }
  window.dispatchEvent(new CustomEvent('backend-changed', { detail: { id } }));
}
