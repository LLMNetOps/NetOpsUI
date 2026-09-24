import { NAV_ITEMS } from '../config.js';
import { esc, pageHeader } from '../utils.js';
import { activeBackend } from '../backends/index.js';

// Placeholder for screens whose data came from the old monolithic backend and
// has no counterpart in NetOps Agent or Hermes yet (NAV_ITEMS[].unavailable).
export function screenUnavailable(c, id) {
  const item = NAV_ITEMS.find(n => n.id === id) || { label: id, icon: 'widgets' };
  c.innerHTML = `<div class="p-6 max-w-[1600px] mx-auto">
    ${pageHeader(esc(item.label), 'Belum tersedia pada backend saat ini.')}
    <div class="bg-surface-container-lowest border border-outline-variant rounded-lg p-12 shadow-sm flex flex-col items-center justify-center text-center">
      <span class="material-symbols-outlined text-5xl text-outline-variant mb-4">${item.icon}</span>
      <h3 class="text-title-sm font-title-sm text-primary mb-2">${esc(item.label)} &middot; Belum Tersedia</h3>
      <p class="text-body-sm text-on-surface-variant max-w-md">
        Backend aktif (<b>${esc(activeBackend().label)}</b>) belum menyediakan API untuk halaman ini.
        Halaman akan diaktifkan kembali setelah endpoint-nya tersedia di NetOps Agent atau Hermes.
      </p>
      <button onclick="location.hash='chat'" class="mt-4 px-4 py-2 bg-secondary text-white rounded-lg text-body-sm font-medium hover:opacity-90 transition-opacity">Buka AI Chat</button>
    </div>
  </div>`;
}
