import { AGENTS } from './config.js';

function makeAgentStates() {
  const s = {};
  AGENTS.forEach(a => { s[a.alias] = { state: 'standby', detail: '', toolCount: 0 }; });
  return s;
}

export const S = {
  screen: location.hash.slice(1) || 'dashboard',
  threadId: null,
  threads: [],
  messages: [],
  chatState: 'idle',
  pendingApproval: null,
  activeQuery: '',
  agents: makeAgentStates(),
  systemStatus: null,
  toolCount: 0,
  elapsed: 0,
  console: [],          // persistent process log — survives across turns/threads
  consoleOpen: true,
  consoleHeight: 240,
};
