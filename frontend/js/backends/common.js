// Shared HTTP/SSE helpers for the backend adapters. Every backend is reached
// through the nginx proxy under /backend/<id>/ (see nginx.conf.template), so
// the browser never talks to the backends directly and never holds an API key.

export class HttpError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export async function http(base, path, { method = 'GET', body, signal } = {}) {
  const init = { method, signal, headers: {} };
  if (body !== undefined) {
    init.headers['Content-Type'] = 'application/json';
    init.body = JSON.stringify(body);
  }
  const r = await fetch(base + path, init);
  if (!r.ok) throw new HttpError(r.status, `HTTP ${r.status} ${path}: ${await errorDetail(r)}`);
  if (r.status === 204) return null;
  const text = await r.text();
  return text ? JSON.parse(text) : null;
}

async function errorDetail(r) {
  const text = await r.text().catch(() => '');
  try {
    const j = JSON.parse(text);
    // FastAPI validation errors: detail is a list of { loc, msg }.
    if (Array.isArray(j.detail)) return j.detail.map(d => `${(d.loc || []).slice(1).join('.')}: ${d.msg}`).join('; ');
    return j.detail || j.error?.message || j.error || j.message || text;
  } catch {
    return text || r.statusText;
  }
}

export async function ensureOk(r, path) {
  if (!r.ok) throw new HttpError(r.status, `HTTP ${r.status} ${path}: ${await errorDetail(r)}`);
  return r;
}

// Parses a text/event-stream body. Calls onFrame({ event, data }) per frame,
// where `data` is the parsed JSON payload (or the raw string when it is not
// JSON). Comment frames (": ping", ": keepalive") are skipped.
export async function readSSE(response, onFrame) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split(/\r?\n\r?\n/);
    buf = frames.pop();
    for (const frame of frames) dispatchFrame(frame, onFrame);
  }
  if (buf.trim()) dispatchFrame(buf, onFrame);
}

function dispatchFrame(frame, onFrame) {
  let event = null;
  const dataLines = [];
  for (const line of frame.split(/\r?\n/)) {
    if (!line || line.startsWith(':')) continue;
    if (line.startsWith('event:')) event = line.slice(6).trim();
    else if (line.startsWith('data:')) dataLines.push(line.slice(5).replace(/^ /, ''));
  }
  if (!dataLines.length) return;
  const raw = dataLines.join('\n');
  let data = raw;
  try { data = JSON.parse(raw); } catch { /* keep raw string */ }
  onFrame({ event, data });
}

// Unix seconds (float) / milliseconds / ISO string → Date (null when unusable).
export function toDate(v) {
  if (v == null || v === '') return null;
  if (typeof v === 'number') return new Date(v < 1e12 ? v * 1000 : v);
  const d = new Date(v);
  return isNaN(d) ? null : d;
}

// Message content may be a plain string or an OpenAI-style parts array.
export function contentText(content) {
  if (typeof content === 'string') return content;
  if (Array.isArray(content)) {
    return content.map(p => (typeof p === 'string' ? p : p?.text || '')).filter(Boolean).join('\n');
  }
  return '';
}

// crypto.randomUUID() only exists in secure contexts (HTTPS or localhost); the
// console is normally served over plain http://<host>:3000, where it is
// undefined. getRandomValues() is available everywhere.
export function uuid() {
  if (typeof crypto.randomUUID === 'function') return crypto.randomUUID();
  const b = crypto.getRandomValues(new Uint8Array(16));
  b[6] = (b[6] & 0x0f) | 0x40;
  b[8] = (b[8] & 0x3f) | 0x80;
  const h = [...b].map(x => x.toString(16).padStart(2, '0')).join('');
  return `${h.slice(0, 8)}-${h.slice(8, 12)}-${h.slice(12, 16)}-${h.slice(16, 20)}-${h.slice(20)}`;
}
