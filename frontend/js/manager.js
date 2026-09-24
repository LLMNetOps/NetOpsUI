// Client for the NetOpsUI management service (server/), reached at /api/ via
// nginx. It owns skills, agent profiles and the read-only views of each
// backend's config files — things NetOps Agent and Hermes have no API for.
import { HttpError } from './backends/common.js';

export async function mgr(path, { method = 'GET', body } = {}) {
  const init = { method, headers: {} };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const r = await fetch('/api' + path, init);
  const text = await r.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* non-JSON error page from the proxy */ }
  if (!r.ok) {
    const detail = data?.detail;
    const msg = typeof detail === 'string' ? detail : Array.isArray(detail) ? detail.map(d => d.msg).join('; ')
      : r.status === 502 || r.status === 504 ? 'Manager service tidak terjangkau' : text || r.statusText;
    throw new HttpError(r.status, msg);
  }
  return data;
}

// Agent profile chosen for Hermes chats (NetOps Agent takes its persona from SOUL.md).
const PROFILE_KEY = 'llmnetops-hermes-profile';

export function getActiveProfile() {
  try { return localStorage.getItem(PROFILE_KEY) || null; } catch { return null; }
}

export function setActiveProfile(slug) {
  try {
    if (slug) localStorage.setItem(PROFILE_KEY, slug); else localStorage.removeItem(PROFILE_KEY);
  } catch { /* per-session only */ }
}
