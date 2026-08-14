export const AGENTS = [
  { name:'supervisor',     alias:'bambang', role:'supervisor',  icon:'account_tree' },
  { name:'monitor_agent',  alias:'eko',     role:'monitor',     icon:'monitoring' },
  { name:'diagnose_agent', alias:'agus',    role:'diagnosa',    icon:'troubleshoot' },
  { name:'config_agent',   alias:'joko',    role:'config',      icon:'settings_suggest' },
  { name:'security_agent', alias:'satria',  role:'security',    icon:'shield' },
  { name:'document_agent', alias:'budi',    role:'dokumen',     icon:'description' },
  { name:'netbox_agent',   alias:'yanto',   role:'netbox',      icon:'storage' },
  { name:'validasi_agent', alias:'wati',    role:'validasi',    icon:'verified' },
];

// Consecutive items sharing the same `group` are rendered together under a
// section header in the sidebar (see shell.js renderNav()); items without a
// `group` render at the root with no header. Order here is display order.
export const NAV_ITEMS = [
  { id:'dashboard', label:'Dashboard',  icon:'dashboard' },
  { id:'chat',      label:'AI Chat',    icon:'chat_bubble' },
  { id:'nodes',     label:'Nodes',      icon:'dns',        group:'Infrastructure' },
  { id:'network',   label:'Network',    icon:'hub',        group:'Infrastructure' },
  { id:'dhcp',      label:'DHCP',       icon:'router',     group:'Infrastructure' },
  { id:'netbox',    label:'NetBox',     icon:'storage',    group:'Infrastructure' },
  { id:'skills',    label:'Skills',     icon:'psychology', group:'Agent Platform' },
  { id:'agents',    label:'Agents',     icon:'smart_toy',  group:'Agent Platform' },
  { id:'reports',   label:'Reports',    icon:'assessment', group:'Insights' },
  { id:'backups',   label:'Backups',    icon:'backup',     group:'Insights' },
  { id:'metrics',   label:'Metrics',    icon:'insights',   group:'Insights' },
  { id:'settings',  label:'Settings',   icon:'settings' },
];

export const ROLE_TO_ALIAS = {};
AGENTS.forEach(a => { ROLE_TO_ALIAS[a.name] = a.alias; });
