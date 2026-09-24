import { $, esc } from '../utils.js';
import { mgr } from '../manager.js';

// Faint "connected network" tile: nodes joined by thin lines. Lines that leave the
// tile are repeated at the opposite edge so the pattern tiles without seams.
const NODES = [[30, 40], [120, 20], [200, 90], [90, 130], [190, 200], [40, 210], [130, 240]];
const LINKS = [[0, 1], [1, 2], [0, 3], [3, 2], [3, 5], [3, 4], [2, 4], [5, 6], [4, 6], [1, 3]];
function networkTile() {
  const T = 240;
  const at = (i, dx, dy) => `${NODES[i][0] + dx},${NODES[i][1] + dy}`;
  const seg = (p, q) => {
    const [x1, y1] = p.split(','), [x2, y2] = q.split(',');
    return `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`;
  };
  const line = ([a, b]) => seg(at(a, 0, 0), at(b, 0, 0));
  // Each wrapping link is drawn twice: leaving this tile, and entering it from the previous one.
  const wrap = [[4, 5, T, 0], [2, 0, T, 0], [6, 1, 0, T]]
    .map(([a, b, dx, dy]) => seg(at(a, 0, 0), at(b, dx, dy)) + seg(at(a, -dx, -dy), at(b, 0, 0))).join('');
  const dots = NODES.map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3"/>`).join('');
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="${T}" height="${T}">
    <g stroke="#1b3a5c" stroke-opacity="0.09" stroke-width="1">${LINKS.map(l => line(l)).join('')}${wrap}</g>
    <g fill="#1b3a5c" fill-opacity="0.14">${dots}</g></svg>`;
  return `url('data:image/svg+xml,${encodeURIComponent(svg)}')`;
}

// Full-page login shown instead of the app shell until a session exists.
// Calls onSuccess({ username }) after a successful login.
export function renderLogin(onSuccess, notice = '') {
  $('app').innerHTML = `
  <div class="min-h-screen flex flex-col items-center justify-center bg-background px-4 py-8" style="background-image:radial-gradient(ellipse 45% 55% at 50% 50%, #f7f9fc 30%, rgba(247,249,252,0) 100%), ${networkTile()}">
    <img src="/assets/llmnetops-logo-formal.png" alt="LLMNetOps" class="h-14 mb-8">
    <form id="login-form" class="w-full max-w-[380px] bg-surface-container-lowest border border-outline-variant rounded-xl shadow-sm p-8" autocomplete="on">
      <h1 class="font-headline-md text-headline-md text-primary mb-6">Masuk</h1>
      <div id="login-error" class="${notice ? '' : 'hidden'} mb-4 px-3 py-2 rounded-lg bg-error-container text-error text-body-sm" role="alert">${esc(notice)}</div>
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1" for="login-username">USERNAME</label>
      <input id="login-username" name="username" type="text" autocomplete="username" autocapitalize="none" spellcheck="false" required maxlength="64"
        class="w-full mb-4 px-3 py-2 border border-outline-variant rounded-lg text-body-md focus:border-primary focus:ring-1 focus:ring-primary">
      <label class="block text-label-caps font-label-caps text-on-surface-variant mb-1" for="login-password">PASSWORD</label>
      <input id="login-password" name="password" type="password" autocomplete="current-password" required maxlength="256"
        class="w-full mb-6 px-3 py-2 border border-outline-variant rounded-lg text-body-md focus:border-primary focus:ring-1 focus:ring-primary">
      <button id="login-submit" type="submit" class="w-full py-2.5 bg-primary text-on-primary rounded-lg text-body-md font-medium hover:bg-primary-container transition-colors disabled:opacity-60">Masuk</button>
    </form>
    <footer class="mt-8 text-center text-[11px] text-on-surface-variant leading-relaxed">
      <p>LLMNetOps © 2026 · v1.0.0</p>
      <p>Universitas Brawijaya · Malang, Indonesia</p>
      <p class="mt-1">
        <a href="https://llmnetops.github.io/" target="_blank" rel="noopener noreferrer" class="text-primary hover:underline">llmnetops.github.io</a>
        · Kontak: <a href="mailto:llmnetops@ub.ac.id" class="text-primary hover:underline">llmnetops@ub.ac.id</a>
      </p>
    </footer>
  </div>`;

  const err = $('login-error');
  $('login-username').focus();
  $('login-form').onsubmit = async e => {
    e.preventDefault();
    const btn = $('login-submit');
    btn.disabled = true;
    btn.textContent = 'Memeriksa...';
    err.classList.add('hidden');
    try {
      const u = await mgr('/auth/login', { method: 'POST', body: { username: $('login-username').value.trim(), password: $('login-password').value } });
      onSuccess(u);
    } catch (ex) {
      err.textContent = ex.message;
      err.classList.remove('hidden');
      $('login-password').value = '';
      $('login-password').focus();
      btn.disabled = false;
      btn.textContent = 'Masuk';
    }
  };
}
