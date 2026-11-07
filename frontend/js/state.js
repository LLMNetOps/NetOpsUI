export const S = {
  user: null,           // logged-in operator's username
  screen: location.hash.slice(1) || 'dashboard',
  threadId: null,
  threads: [],
  threadsBackend: null, // backend id S.threads was loaded from; reload when it differs
  messages: [],
  chatState: 'idle',    // 'idle' | 'streaming' — approval is shown while still streaming
  stopRequested: false, // true after operator clicks Stop, until run actually ends
  pendingApproval: null,
  activeQuery: '',
  tools: [],            // tool activity of the thread's last turn: { name, detail, state, durationMs }
  toolsQuery: '',       // question that turn answered, shown above the list for review
  toolsPartial: false,  // the turn was left while running, so later calls are missing
  elapsed: 0,
  console: [],          // persistent process log — survives across turns/threads
  consoleOpen: true,
  consoleHeight: 240,
};
