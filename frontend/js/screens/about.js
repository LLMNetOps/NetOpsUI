import { cardHtml, pageHeader } from '../utils.js';

const CONTACT_EMAIL = 'llmnetops@ub.ac.id';

const LINKS = [
  { href: 'https://llmnetops.github.io/', label: 'llmnetops.github.io', note: 'Situs proyek LLMNetOps', icon: 'language' },
  { href: 'https://apnic.foundation/projects/llmnetops/', label: 'apnic.foundation/projects/llmnetops', note: 'Halaman proyek di APNIC Foundation', icon: 'open_in_new' },
];

function fact(label, value) {
  return `<div>
    <dt class="text-label-caps font-label-caps text-on-surface-variant mb-0.5">${label}</dt>
    <dd class="text-body-md text-on-surface">${value}</dd>
  </div>`;
}

function linkRow(l) {
  return `<a href="${l.href}" target="_blank" rel="noopener noreferrer" class="flex items-center gap-3 p-3 border border-outline-variant rounded-lg hover:bg-surface-container-low transition-colors">
    <span class="material-symbols-outlined text-secondary">${l.icon}</span>
    <span class="min-w-0">
      <span class="block text-body-sm font-medium text-primary truncate">${l.label}</span>
      <span class="block text-[11px] text-on-surface-variant">${l.note}</span>
    </span>
  </a>`;
}

export function screenAbout(c) {
  c.innerHTML = `<div class="p-6 max-w-[1100px] mx-auto">
    ${pageHeader('About', 'Tentang proyek LLMNetOps dan pendanaannya.')}
    <div class="space-y-6">
      ${cardHtml('LLMNetOps', `
        <p class="text-body-md text-on-surface leading-relaxed">
          <b>LLMNetOps</b> — <i>Strengthening network operations knowledge through locally-hosted generative AI</i>.
          Proyek ini membantu institusi anggota IDREN mengadopsi Large Language Model (LLM) open-source yang dijalankan
          secara lokal dan mengutamakan privasi, untuk pengelolaan jaringan dan dokumentasinya.
          Konsol ini adalah antarmuka operator untuk agent jaringan yang dikembangkan dalam proyek tersebut.
        </p>
        <ul class="mt-4 space-y-2 text-body-sm text-on-surface-variant list-disc pl-5">
          <li>Memperkenalkan AI kontekstual untuk operasi infrastruktur jaringan.</li>
          <li>Mendorong adopsi AI yang mengutamakan privasi lewat model open-source yang di-host sendiri.</li>
          <li>Menjembatani kesenjangan literasi AI bagi staf jaringan.</li>
          <li>Membangun komunitas berbagi pengetahuan lewat workshop dan kolaborasi antar-peer.</li>
        </ul>`)}
      ${cardHtml('Pendanaan', `
        <p class="text-body-md text-on-surface leading-relaxed mb-5">
          Proyek ini merupakan <b>hibah ISIF Asia</b> dan mendapat dukungan dari APNIC Foundation.
        </p>
        <dl class="grid grid-cols-1 sm:grid-cols-2 gap-4">
          ${fact('Program hibah', 'ISIF Asia Grants')}
          ${fact('Tahun', '2025')}
          ${fact('Pelaksana', 'Universitas Brawijaya, Indonesia')}
          ${fact('Mitra', 'IDREN')}
        </dl>`)}
      ${cardHtml('Informasi lebih lanjut', `<div class="grid grid-cols-1 md:grid-cols-2 gap-3">${LINKS.map(linkRow).join('')}</div>
        <p class="mt-5 text-body-md text-on-surface">
          <span class="text-label-caps font-label-caps text-on-surface-variant mr-2">Kontak:</span>
          <a href="mailto:${CONTACT_EMAIL}" class="text-primary font-medium hover:underline">${CONTACT_EMAIL}</a>
        </p>`)}
    </div>
  </div>`;
}
