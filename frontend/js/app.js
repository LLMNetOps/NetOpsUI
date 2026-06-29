import { store } from './store.js'
import { mount as mountDashboard } from './screens/dashboard.js'
import { mount as mountChat, unmount as unmountChat } from './screens/chat.js'

const NAV_ITEMS = [
  { id: 'dashboard', label: 'Dashboard',  icon: 'dashboard' },
  { id: 'chat',      label: 'AI Chat',    icon: 'chat_bubble' },
  { id: 'network',   label: 'Network',    icon: 'hub' },
  { id: 'dhcp',      label: 'DHCP',       icon: 'router' },
  { id: 'netbox',    label: 'NetBox',     icon: 'storage' },
  { id: 'skills',    label: 'Skills',     icon: 'psychology' },
  { id: 'reports',   label: 'Reports',    icon: 'assessment' },
  { id: 'backups',   label: 'Backups',    icon: 'backup' },
  { id: 'metrics',   label: 'Metrics',    icon: 'insights' },
  { id: 'settings',  label: 'Settings',   icon: 'settings' },
]

let currentUnmount = null

function renderShell() {
  const app = document.getElementById('app')
  app.innerHTML = `
    <!-- Sidebar -->
    <aside class="fixed left-0 top-0 h-full w-[240px] bg-primary-container flex flex-col py-6 z-40">
      <div class="px-6 mb-8 mt-1">
        <h1 class="text-headline-md font-headline-md font-bold tracking-tight">
          <span class="text-white">LLM</span><span class="text-secondary-container">NetOps</span>
        </h1>
        <p class="text-[10px] font-label-caps text-white/50 tracking-widest mt-1 uppercase">Enterprise Console</p>
      </div>
      <nav id="sidebar-nav" class="flex-1 px-3 space-y-1 sidebar-scroll overflow-y-auto"></nav>
      <div class="px-6 pt-4 border-t border-white/10 mt-4">
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 rounded-full bg-secondary-container flex items-center justify-center text-on-secondary-container font-bold text-xs">OP</div>
          <div class="overflow-hidden">
            <p class="text-white text-xs font-bold truncate">Operator</p>
            <p class="text-white/50 text-[10px] truncate">Network Admin</p>
          </div>
        </div>
      </div>
    </aside>

    <!-- Header -->
    <header class="fixed top-0 left-[240px] right-0 h-[56px] bg-surface-container-lowest flex justify-between items-center px-6 z-50 border-b border-outline-variant">
      <nav class="flex items-center text-on-surface-variant text-body-sm">
        <span class="font-bold text-primary mr-2">Console</span>
        <span class="material-symbols-outlined text-[16px] mr-2">chevron_right</span>
        <span id="breadcrumb-page">Dashboard</span>
      </nav>
      <div class="flex items-center gap-4">
        <div id="system-badge" class="flex items-center gap-2 px-3 py-1 bg-green-50 border border-green-100 rounded-full">
          <span class="relative flex h-2 w-2">
            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
            <span class="relative inline-flex rounded-full h-2 w-2 bg-green-500"></span>
          </span>
          <span class="font-label-caps text-label-caps text-green-700">SYSTEM ONLINE</span>
        </div>
        <button class="text-on-surface-variant hover:bg-surface-container p-1.5 rounded-full transition-colors">
          <span class="material-symbols-outlined">notifications</span>
        </button>
        <div class="h-8 w-8 rounded-full bg-surface-container flex items-center justify-center border border-outline-variant">
          <span class="material-symbols-outlined text-on-surface-variant text-lg">account_circle</span>
        </div>
      </div>
    </header>

    <!-- Main Content -->
    <main class="ml-[240px] pt-[56px] min-h-screen bg-background">
      <div id="screen-container"></div>
    </main>`

  renderNav()
}

function renderNav() {
  const nav = document.getElementById('sidebar-nav')
  nav.innerHTML = NAV_ITEMS.map(item => {
    const active = store.currentScreen === item.id
    const base = 'flex items-center gap-3 px-3 py-2.5 transition-all duration-150 ease-in-out font-label-caps text-label-caps cursor-pointer'
    const activeClass = active
      ? 'text-surface-container-lowest bg-white/10 border-l-[3px] border-secondary-container'
      : 'text-surface-container-lowest/60 hover:bg-white/5 hover:text-surface-container-lowest border-l-[3px] border-transparent'
    const fillStyle = active ? "font-variation-settings: 'FILL' 1;" : ''
    return `<a class="${base} ${activeClass}" data-screen="${item.id}">
      <span class="material-symbols-outlined" style="${fillStyle}">${item.icon}</span>
      <span>${item.label}</span>
    </a>`
  }).join('')

  nav.addEventListener('click', e => {
    const link = e.target.closest('[data-screen]')
    if (link) {
      location.hash = link.dataset.screen
    }
  })
}

function navigate(screenId) {
  if (currentUnmount) { currentUnmount(); currentUnmount = null }

  store.currentScreen = screenId
  renderNav()

  const breadcrumb = document.getElementById('breadcrumb-page')
  if (breadcrumb) {
    const item = NAV_ITEMS.find(n => n.id === screenId)
    breadcrumb.textContent = item ? item.label : screenId
  }

  const container = document.getElementById('screen-container')

  switch (screenId) {
    case 'dashboard':
      mountDashboard(container)
      break
    case 'chat':
      mountChat(container)
      currentUnmount = unmountChat
      break
    default:
      container.innerHTML = placeholderScreen(screenId)
      break
  }
}

function placeholderScreen(id) {
  const item = NAV_ITEMS.find(n => n.id === id) || { label: id, icon: 'widgets' }
  return `
    <div class="p-6 max-w-[1600px] mx-auto">
      <div class="mb-6">
        <h2 class="text-headline-md font-headline-md text-primary">${item.label}</h2>
        <p class="text-body-md text-on-surface-variant">This screen is under development.</p>
      </div>
      <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-center">
        <span class="material-symbols-outlined text-5xl text-outline-variant mb-4">${item.icon}</span>
        <h3 class="text-title-sm font-title-sm text-primary mb-2">${item.label}</h3>
        <p class="text-body-sm text-on-surface-variant max-w-md">
          The ${item.label} screen will be implemented in a future update. Use AI Chat to interact with the system.
        </p>
        <button onclick="location.hash='chat'" class="mt-4 px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity">
          Open AI Chat
        </button>
      </div>
    </div>`
}

// ── Router ──────────────────────────────────────────────────────────────────

function onHashChange() {
  const hash = location.hash.slice(1) || 'dashboard'
  navigate(hash)
}

// ── Init ────────────────────────────────────────────────────────────────────

renderShell()
onHashChange()
window.addEventListener('hashchange', onHashChange)
