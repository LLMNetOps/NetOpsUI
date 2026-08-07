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

export const NAV_ITEMS = [
  { id:'dashboard', label:'Dashboard',  icon:'dashboard' },
  { id:'chat',      label:'AI Chat',    icon:'chat_bubble' },
  { id:'network',   label:'Network',    icon:'hub' },
  { id:'dhcp',      label:'DHCP',       icon:'router' },
  { id:'netbox',    label:'NetBox',     icon:'storage' },
  { id:'skills',    label:'Skills',     icon:'psychology' },
  { id:'reports',   label:'Reports',    icon:'assessment' },
  { id:'backups',   label:'Backups',    icon:'backup' },
  { id:'metrics',   label:'Metrics',    icon:'insights' },
  { id:'settings',  label:'Settings',   icon:'settings' },
];

export const ROLE_TO_ALIAS = {};
AGENTS.forEach(a => { ROLE_TO_ALIAS[a.name] = a.alias; });
