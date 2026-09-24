export const S = {
  screen: location.hash.slice(1) || 'dashboard',
  threadId: null,
  threads: [],
  threadsBackend: null, // backend id S.threads was loaded from; reload when it differs
  messages: [],
  chatState: 'idle',    // 'idle' | 'streaming' — approval is shown while still streaming
  stopRequested: false, // true after operator clicks Stop, until run actually ends
  pendingApproval: null,
  activeQuery: '',
  tools: [],            // tool activity of the current turn: { name, detail, state, durationMs }
  toolCount: 0,
  elapsed: 0,
  console: [],          // persistent process log — survives across turns/threads
  consoleOpen: true,
  consoleHeight: 240,
};
