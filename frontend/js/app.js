import { S } from './state.js';
import { renderShell, renderNav } from './shell.js';
import { $ } from './utils.js';
import { NAV_ITEMS } from './config.js';

import { screenDashboard } from './screens/dashboard.js';
import { screenChat, chatUnmount } from './screens/chat.js';
import { screenNetwork } from './screens/network.js';
import { screenDHCP } from './screens/dhcp.js';
import { screenNetBox } from './screens/netbox.js';
import { screenSkills } from './screens/skills.js';
import { screenReports } from './screens/reports.js';
import { screenReports as screenBackups } from './screens/reports.js';
import { screenMetrics } from './screens/metrics.js';
import { screenSettings } from './screens/settings.js';

let _currentUnmount = null;

async function navigate(screenId, param) {
  if (_currentUnmount) { _currentUnmount(); _currentUnmount = null; }

  S.screen = screenId;
  renderNav();

  const breadcrumb = document.getElementById('breadcrumb-page');
  if (breadcrumb) {
    const item = NAV_ITEMS.find(n => n.id === screenId);
    breadcrumb.textContent = item ? item.label : screenId;
  }

  const c = $('screen-container');
  if (!c) return;

  c.innerHTML = '';

  switch (screenId) {
    case 'dashboard': await screenDashboard(c); break;
    case 'chat':
      await screenChat(c, param);
      _currentUnmount = chatUnmount;
      break;
    case 'network':   await screenNetwork(c); break;
    case 'dhcp':      await screenDHCP(c); break;
    case 'netbox':    await screenNetBox(c); break;
    case 'skills':    await screenSkills(c); break;
    case 'reports':   await screenReports(c); break;
    case 'backups':   await screenBackups(c); break;
    case 'metrics':   await screenMetrics(c); break;
    case 'settings':  await screenSettings(c); break;
    default:          placeholderScreen(c, screenId); break;
  }
}

function placeholderScreen(c, id) {
  const item = NAV_ITEMS.find(n => n.id === id) || { label: id, icon: 'widgets' };
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    <div class="mb-6">
      <h2 class="text-headline-md font-headline-md text-primary">${item.label}</h2>
      <p class="text-body-md text-on-surface-variant">This screen is under development.</p>
    </div>
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-center">
      <span class="material-symbols-outlined text-5xl text-outline-variant mb-4">${item.icon}</span>
      <h3 class="text-title-sm font-title-sm text-primary mb-2">${item.label}</h3>
      <p class="text-body-sm text-on-surface-variant max-w-md">Use AI Chat to interact with the system.</p>
      <button onclick="location.hash='chat'" class="mt-4 px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity">Open AI Chat</button>
    </div>
  </div>`;
}

function onHash() {
  const raw = location.hash.slice(1) || 'dashboard';
  const [id, ...rest] = raw.split('/');
  navigate(id, rest.length ? decodeURIComponent(rest.join('/')) : undefined);
}

renderShell();
onHash();
window.addEventListener('hashchange', onHash);
