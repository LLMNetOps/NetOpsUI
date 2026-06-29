export async function createSession() {
  const res = await fetch('/session/new', { method: 'POST' })
  return res.json()
}

export async function streamChat(threadId, message, onEvent) {
  const res = await fetch('/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, message }),
  })
  await _consumeSSE(res, onEvent)
}

export async function submitApproval(threadId, decision, onEvent) {
  const res = await fetch('/approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId, decision }),
  })
  await _consumeSSE(res, onEvent)
}

export async function fetchInfo() {
  const res = await fetch('/info')
  return res.json()
}

export async function fetchMetrics(n = 100) {
  const res = await fetch(`/metrics?n=${n}`)
  return res.json()
}

export async function fetchStatus() {
  try {
    const res = await fetch('/api/status')
    return res.json()
  } catch {
    return null
  }
}

export async function resetSession(threadId) {
  await fetch('/api/reset', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ thread_id: threadId }),
  })
}

async function _consumeSSE(response, onEvent) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    const frames = buffer.split('\n\n')
    buffer = frames.pop()

    for (const frame of frames) {
      const line = frame.trim()
      if (!line || line.startsWith(':')) continue
      if (line.startsWith('data: ')) {
        try {
          const payload = JSON.parse(line.slice(6))
          onEvent(payload.type, payload.content)
        } catch { /* ignore malformed */ }
      }
    }
  }
}
