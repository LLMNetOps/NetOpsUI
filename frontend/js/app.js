import { S } from './state.js';
import { renderShell, renderNav } from './shell.js';
import { $ } from './utils.js';
import { NAV_ITEMS } from './config.js';

import { screenDashboard } from './screens/dashboard.js';
import { screenChat, chatUnmount } from './screens/chat.js';
import { screenNodes } from './screens/nodes.js';
import { screenSkills } from './screens/skills.js';
import { screenAgents } from './screens/agents.js';
import { screenSettings } from './screens/settings.js';
import { screenUnavailable } from './screens/unavailable.js';

let _currentUnmount = null;

async function navigate(screenId, param) {
  if (_currentUnmount) { _currentUnmount(); _currentUnmount = null; }

  S.screen = screenId;
  renderNav();

  const item = NAV_ITEMS.find(n => n.id === screenId);
  const breadcrumb = document.getElementById('breadcrumb-page');
  if (breadcrumb) breadcrumb.textContent = item ? item.label : screenId;

  const c = $('screen-container');
  if (!c) return;

  c.innerHTML = '';

  if (!item) { location.hash = 'dashboard'; return; } // unknown/removed route
  if (item.unavailable) {
    screenUnavailable(c, screenId);
    return;
  }

  switch (screenId) {
    case 'dashboard': await screenDashboard(c); break;
    case 'chat':
      await screenChat(c, param);
      _currentUnmount = chatUnmount;
      break;
    case 'nodes':     await screenNodes(c); break;
    case 'skills':    await screenSkills(c); break;
    case 'agents':    await screenAgents(c); break;
    case 'settings':  await screenSettings(c); break;
    default:          screenUnavailable(c, screenId); break;
  }
}

function onHash() {
  const raw = location.hash.slice(1) || 'dashboard';
  const [id, ...rest] = raw.split('/');
  navigate(id, rest.length ? decodeURIComponent(rest.join('/')) : undefined);
}

renderShell();
onHash();
window.addEventListener('hashchange', onHash);
