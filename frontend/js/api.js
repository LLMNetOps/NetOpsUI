export async function consumeSSE(response, onEvent) {
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buf = '';
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buf += decoder.decode(value, { stream: true });
    const frames = buf.split('\n\n');
    buf = frames.pop();
    for (const frame of frames) {
      const line = frame.trim();
      if (!line || line.startsWith(':')) continue;
      if (line.startsWith('data: ')) {
        try { const p = JSON.parse(line.slice(6)); onEvent(p.type, p.content); } catch {}
      }
    }
  }
}

export async function apiCreateSession() {
  const r = await fetch('/session/new', { method: 'POST' });
  return r.json();
}

export async function apiStreamChat(threadId, message, onEvent) {
  const r = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, message }),
  });
  await consumeSSE(r, onEvent);
}

export async function apiApprove(threadId, decision, onEvent) {
  const r = await fetch('/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, decision }),
  });
  await consumeSSE(r, onEvent);
}

export async function apiInfo() { return (await fetch('/info')).json(); }
export async function apiStatus() {
  try { return (await fetch('/api/status')).json(); } catch { return null; }
}

export async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
}

export async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
}

export async function apiPut(path, body) {
  const r = await fetch(path, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body || {}),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
}

export async function apiDelete(path) {
  const r = await fetch(path, { method: 'DELETE' });
  if (!r.ok) throw new Error(`HTTP ${r.status} ${path}`);
  return r.json();
}
