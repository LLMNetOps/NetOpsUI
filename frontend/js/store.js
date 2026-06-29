const AGENTS = [
  { name: 'supervisor',     alias: 'bambang', role: 'supervisor',  icon: 'account_tree' },
  { name: 'monitor_agent',  alias: 'eko',     role: 'monitor',     icon: 'monitoring' },
  { name: 'diagnose_agent', alias: 'agus',    role: 'diagnosa',    icon: 'troubleshoot' },
  { name: 'config_agent',   alias: 'joko',    role: 'config',      icon: 'settings_suggest' },
  { name: 'security_agent', alias: 'satria',  role: 'security',    icon: 'shield' },
  { name: 'document_agent', alias: 'budi',    role: 'dokumen',     icon: 'description' },
  { name: 'netbox_agent',   alias: 'yanto',   role: 'netbox',      icon: 'storage' },
  { name: 'validasi_agent', alias: 'wati',    role: 'validasi',    icon: 'verified' },
]

const ROLE_TO_ALIAS = {}
AGENTS.forEach(a => { ROLE_TO_ALIAS[a.name] = a.alias })

function makeAgentStates() {
  const s = {}
  AGENTS.forEach(a => { s[a.alias] = { state: 'standby', detail: '', toolCount: 0 } })
  return s
}

export const store = {
  currentScreen: location.hash.slice(1) || 'dashboard',

  // Chat
  threadId: null,
  threads: [],
  messages: [],
  chatState: 'idle',
  pendingApproval: null,
  activeQuery: '',

  // Agents
  agents: makeAgentStates(),

  // System
  systemStatus: null,

  // Metrics
  toolCount: 0,
  elapsed: 0,
  elapsedTimer: null,
}

export { AGENTS, ROLE_TO_ALIAS, makeAgentStates }
