import { esc } from './utils.js';

// Mounts a chip/tag input with autocomplete into `container` (an existing
// DOM element). Replaces plain comma-separated text inputs for editing a
// list of values drawn from a known, finite option set (tool names, skill
// names). Returns { getValues(): string[] } to read the selection on save.
//
// The <input> element is built once at mount and never recreated — only the
// chips and suggestion-list sub-sections get their innerHTML rebuilt on
// change. Replacing the input itself on every keystroke would fire a native
// blur (removing a focused node from the DOM does that), which raced with
// the dropdown-close timeout below and made the field unusable while typing.
export function mountTagInput(container, { initial = [], options = [], placeholder = 'Cari...' } = {}) {
  let selected = [...initial];
  let query = '';
  let activeIndex = -1;

  container.innerHTML = `
    <div class="tag-input-box flex flex-wrap gap-1.5 items-center px-2 py-1.5 border border-outline-variant rounded text-body-sm bg-surface-container-lowest focus-within:ring-1 focus-within:ring-primary">
      <div data-chips class="contents"></div>
      <input type="text" data-tag-query class="flex-1 min-w-[100px] outline-none bg-transparent text-body-sm py-0.5">
    </div>
    <div class="relative">
      <div data-tag-suggestions class="absolute left-0 right-0 mt-1 max-h-48 overflow-y-auto bg-white border border-outline-variant rounded shadow-lg z-20 hidden"></div>
    </div>`;

  const chipsEl = container.querySelector('[data-chips]');
  const input = container.querySelector('[data-tag-query]');
  const suggEl = container.querySelector('[data-tag-suggestions]');

  function suggestions() {
    const q = query.trim().toLowerCase();
    return options
      .filter(o => !selected.includes(o))
      .filter(o => !q || o.toLowerCase().includes(q))
      .slice(0, 30);
  }

  function renderChips() {
    input.placeholder = selected.length ? '' : placeholder;
    chipsEl.innerHTML = selected.map((v, i) => `<span class="inline-flex items-center gap-1 pl-2 pr-1 py-0.5 bg-primary/10 text-primary rounded text-[12px] font-medium">
      ${esc(v)}
      <button type="button" data-remove-tag="${i}" class="hover:bg-primary/20 rounded-full w-4 h-4 flex items-center justify-center leading-none">
        <span class="material-symbols-outlined text-[13px]">close</span>
      </button>
    </span>`).join('');

    chipsEl.querySelectorAll('[data-remove-tag]').forEach(btn => {
      // mousedown+preventDefault so removing a chip never blurs the query input
      btn.onmousedown = e => {
        e.preventDefault();
        selected.splice(parseInt(btn.dataset.removeTag), 1);
        renderChips();
        renderSuggestions();
      };
    });
  }

  function renderSuggestions() {
    const sugg = suggestions();
    const show = document.activeElement === input && sugg.length > 0;
    if (!show) {
      suggEl.classList.add('hidden');
      suggEl.innerHTML = '';
      return;
    }
    suggEl.classList.remove('hidden');
    suggEl.innerHTML = sugg.map((o, i) => `<button type="button" data-pick-tag="${esc(o)}" class="w-full text-left px-3 py-1.5 text-body-sm hover:bg-surface-container-low transition-colors ${i === activeIndex ? 'bg-surface-container-low' : ''}">${esc(o)}</button>`).join('');

    suggEl.querySelectorAll('[data-pick-tag]').forEach(btn => {
      // mousedown+preventDefault so picking a suggestion never blurs the query input
      btn.onmousedown = e => { e.preventDefault(); addValue(btn.dataset.pickTag); };
    });
  }

  function addValue(v) {
    v = (v || '').trim();
    if (v && !selected.includes(v)) selected.push(v);
    query = '';
    input.value = '';
    activeIndex = -1;
    renderChips();
    renderSuggestions();
    input.focus();
  }

  input.oninput = () => { query = input.value; activeIndex = -1; renderSuggestions(); };
  input.onfocus = () => renderSuggestions();
  input.onblur = () => {
    // Never fires from an internal pick/remove click (those preventDefault the
    // mousedown) — only from genuinely leaving the field. Hide unconditionally
    // rather than re-checking document.activeElement, whose value during the
    // blur event itself is inconsistent across browsers.
    suggEl.classList.add('hidden');
    suggEl.innerHTML = '';
  };
  input.onkeydown = e => {
    const sugg = suggestions();
    if (e.key === 'ArrowDown') { e.preventDefault(); activeIndex = Math.min(activeIndex + 1, sugg.length - 1); renderSuggestions(); }
    else if (e.key === 'ArrowUp') { e.preventDefault(); activeIndex = Math.max(activeIndex - 1, -1); renderSuggestions(); }
    else if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault();
      if (activeIndex >= 0 && sugg[activeIndex]) addValue(sugg[activeIndex]);
      else if (query.trim()) addValue(query);
    } else if (e.key === 'Backspace' && !query && selected.length) {
      selected = selected.slice(0, -1);
      renderChips();
      renderSuggestions();
    } else if (e.key === 'Escape') {
      input.blur();
    }
  };

  renderChips();
  renderSuggestions();

  return { getValues: () => [...selected] };
}
