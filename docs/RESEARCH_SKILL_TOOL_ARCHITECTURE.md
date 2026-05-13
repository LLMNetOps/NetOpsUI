# Research Report — Skill & Tool Architecture Review

**Versi:** 1.1
**Tanggal:** 2026-05-08
**Status:** Draft
**Konteks:** Branch `netops` — llmnetops Campus Network Operations Platform

---

## 1. Latar Belakang

Diskusi ini dimulai dari observasi bahwa sistem skill dan tool di proyek llmnetops mengalami **tumpang tindih dan mismatch** yang berpotensi menjadi bug saat runtime. Selain itu, ada pertanyaan strategis tentang apakah arsitektur multi-agent saat ini bisa dikembangkan ke model **agent swarm** yang lebih fleksibel.

### Kondisi Arsitektur Saat Ini

```
Supervisor (bambang) ← JSON-mode LLM routing
    ├── monitor_agent  (eko)    — 21 tools
    ├── diagnose_agent (agus)   — 12 tools
    ├── config_agent   (joko)   — 10 tools
    ├── security_agent (satria) —  6 tools
    └── document_agent (budi)   — 20 tools
```

Skills adalah file Markdown dengan frontmatter YAML yang di-inject sebagai context ke system prompt specialist agent. Total: **11 skills, 34 unique tools, 69 total tool slots** (ada duplikasi).

---

## 2. Temuan: Masalah Skill-Tool Mismatch

### 2.1 Delapan Mismatch yang Teridentifikasi

Skill mendokumentasikan tools yang tidak tersedia di agent yang kemungkinan menanganinya:

| Skill | Tool Bermasalah | Tersedia Di | Dibutuhkan Di |
|---|---|---|---|
| `router-unreachable` | `run_command` | diagnose, config, security | **monitor** |
| `dhcp-pool-audit` | `audit_dhcp` | monitor, document | **diagnose** |
| `utbk-client-monitor` | `audit_dhcp` | monitor, document | **diagnose** |
| `utbk-client-monitor` | `search_device` | diagnose | **monitor** |
| `diagnose-dhcp-client` | `search_device` | diagnose | **monitor** (bila di-route ke sana) |
| `diagnose-dhcp-client` | `run_diagnostic` | diagnose | **monitor** (bila di-route ke sana) |
| `bgp-diagnostics` | `get_router_config` | config saja | **diagnose** |
| `ospf-neighbor-down` | `get_router_config` | config saja | **diagnose** |

**Dampak:** LLM membaca prosedur dari skill context → mencoba memanggil tool → mendapat `"Error: tool not found"` → output tidak akurat atau LLM mengarang data.

### 2.2 Masalah Boundary Agent

**`security_agent` tidak punya unique tools.** Semua tools-nya (`audit_security`, `get_router_log`, `run_command`, `run_command_all`) juga dimiliki agent lain. Identitas security agent hanya ditentukan dari system prompt, bukan dari kapabilitas tools yang eksklusif.

**`document_agent` adalah superset.** Dengan 20 tools, ia bisa gather data dari hampir semua domain sekaligus menulis dokumen. Boundary-nya kabur.

**Tools yang terlalu banyak terduplikasi:**

| Tool | Jumlah Agent |
|---|---|
| `list_routers`, `get_current_time` | 5 (semua agent) |
| `get_router_log`, `run_command_all` | 4 |
| `check_reachability`, `get_system_info`, `get_router_log`, dll | 3 |

### 2.3 Akar Masalah

Field `tools` di skill frontmatter adalah **dokumentasi**, bukan enforcement. Runtime tidak pernah memvalidasi "apakah agent yang menangani skill ini memiliki semua tools yang dibutuhkan?" Akibatnya mismatch terjadi secara silent.

---

## 3. Studi Referensi

### 3.1 Evonic (github.com/anvie/evonic)

Framework agentic AI buatan Indonesia. Konsep yang relevan:
- **Skill sebagai installable package** — dikemas sebagai `.zip`, diaktifkan per-agent via CLI (`skill enable`)
- **Lifecycle skill:** `load → context → execute` — menjaga system prompt tetap lean
- **Agent-to-agent communication** sebagai first-class protocol
- Skill tidak hard-bound ke satu agent, tapi aktivasi dikontrol eksplisit per-agent

**Keterbatasan:** Tidak ada kode implementasi yang bisa dipelajari dari repository publik.

### 3.2 OpenAI Agents SDK

Framework produksi dengan dua konsep yang langsung relevan:

**Handoff sebagai Tool:**
```python
# Handoff diimplementasikan sebagai tool biasa yang bisa dipanggil LLM
billing_agent = Agent(
    name="Billing agent",
    handoff_description="Gunakan ini untuk masalah billing",  # hint ke LLM
    is_enabled=lambda ctx: ctx.some_condition,                # conditional runtime
)
triage_agent = Agent(
    handoffs=[billing_agent, refund_agent],
)
```

Agent yang memutuskan kapan handoff, bukan supervisor central. Ini menghilangkan satu round-trip di setiap routing.

**Skill sebagai Knowledge Package:**
- Skill = `SKILL.md` manifest + optional `scripts/`
- **Progressive disclosure**: hanya metadata dimuat awal, body penuh hanya saat skill diaktifkan
- Binding via `AGENTS.md` (file routing rules), bukan hard-coded

**Perbedaan filosofis dari implementasi kita:**
> Tools = kapabilitas terisolasi. Skills = workflow + judgment + interpretasi yang menggabungkan multiple tools.

### 3.3 GStack (github.com/garrytan/gstack)

Framework Claude Code untuk software development workflow oleh CEO YC. Pola yang relevan:

**Sprint Pipeline — Skill feeds output ke skill berikutnya:**
```
/office-hours → /plan-eng-review → /build → /review → /qa → /ship → /retro
```
Setiap skill mengonsumsi output dari predecessor-nya. Ini adalah konsep **sequential skill pipeline** yang bisa diadopsi untuk `network-report → write-report`.

**Skills sebagai Role, bukan Function:**
Setiap skill merepresentasikan perspektif berbeda (CEO, Engineering Manager, QA Lead). Lebih kaya dari sekedar kumpulan tools — membawa judgment dan sudut pandang yang berbeda.

**GBrain — Persistent Knowledge Base:**
Skills bisa menyimpan dan membaca knowledge antar sesi. Relevan untuk menyimpan history diagnosa, pattern masalah berulang, dan baseline performa jaringan.

### 3.4 Ultralight Orchestration — Burke Holland's Gist

Implementasi nyata multi-agent system menggunakan **VS Code Copilot native agent format**. Empat agent didefinisikan sebagai file `.agent.md` terpisah:

```yaml
# orchestrator.agent.md
---
name: Orchestrator
model: Claude Opus 4.6 (copilot)
tools: ['read/readFile', 'agent', 'memory']   # ← hanya 3 tools!
---
```

**Hal paling relevan:**

**A. Agent definition sebagai file per-agent**

Setiap agent adalah file mandiri dengan `name`, `model`, dan `tools` allowlist eksplisit. Orchestrator hanya punya 3 tools, Planner punya lebih banyak karena butuh riset. Ini adalah implementasi nyata dari "Jalur B — Agent Definitions" yang kita rancang.

**B. Phase-based parallel execution**

Orchestrator mem-parse output Planner jadi fase berdasarkan **file overlap**:

```
Phase 1 (PARALLEL — tidak ada overlap):
  Task 1.1: Design color palette → Designer
  Task 1.2: Create toggle UI    → Designer

Phase 2 (SEQUENTIAL — depends on Phase 1):
  Task 2.1: Implement theme context → Coder   ← file berbeda = bisa paralel
  Task 2.2: Create toggle component → Coder

Phase 3 (SEQUENTIAL — depends on Phase 2):
  Task 3.1: Apply theme globally → Coder
```

Diterjemahkan ke konteks jaringan kita:

```
Phase 1 (PARALLEL — router berbeda):
  Task 1.1: Check reachability router-A → monitor_agent
  Task 1.2: Check reachability router-B → monitor_agent
  Task 1.3: Check reachability router-C → monitor_agent

Phase 2 (SEQUENTIAL — depends on Phase 1):
  Task 2.1: Diagnose router-A (unreachable) → diagnose_agent
  Task 2.2: Audit security router-B         → security_agent  ← paralel karena beda scope

Phase 3:
  Task 3.1: Compile semua hasil → document_agent
```

Ini adalah **gap terbesar** di arsitektur kita — semua eksekusi saat ini sekuensial.

**C. "WHAT not HOW" — Prinsip Delegasi**

```
✅ BENAR: "Cek apakah router-A masih reachable dan identifikasi penyebabnya"
❌ SALAH: "Panggil check_reachability lalu get_router_log lalu run_diagnostic"
```

Supervisor mendelegasikan *outcome*, bukan prosedur. Specialist yang menentukan bagaimana.

**D. Orchestrator tidak pernah implementasi sendiri**

> *"You coordinate work but NEVER implement anything yourself."*

Supervisor kita sudah mengikuti prinsip ini, tapi belum ada enforcement lewat tools allowlist.

**Perbedaan vs proyek kita:**

| Aspek | Gist (Copilot) | llmnetops (LangGraph) |
|---|---|---|
| Agent definition | File `.agent.md` per agent | Registry terpusat `agents/tools.py` |
| Parallelism | Phase-based, file conflict prevention | Tidak ada, semua sekuensial |
| Task framing | Supervisor rumuskan WHAT eksplisit | Specialist menerima raw user message |
| Model per agent | Berbeda (Opus/Codex/Gemini) | Semua sama (Ollama gemma4) |

### 3.5 Anthropic — Multi-Agent Research System & Claude Code Agent Teams

**Dari Multi-Agent Research System:**

Orchestrator (Opus) + Subagents (Sonnet) → **+90.2%** dibanding single-agent Opus.

Key findings:
- **Tool descriptions kritis** — tim membuat "tool-testing agent" yang menguji dan menulis ulang deskripsi tools → penurunan 40% waktu penyelesaian tugas
- **Task delegation harus eksplisit** — setiap subagent butuh: objektif spesifik + format output + tool guidance + batas tugas
- **Token usage** menjelaskan 80% variance performa — multi-agent ~15× lebih banyak token tapi bernilai untuk task kompleks

**Dari Claude Code Agent Teams:**

```
Team Lead (koordinator)
├── Teammate A ──── Shared Task List ──── Teammate B
│         └───────── Mailbox ────────────┘
└── Teammate C  (peer-to-peer messaging)
```

Berbeda dari arsitektur hub-and-spoke kita: teammates bisa berkomunikasi **peer-to-peer** tanpa lewat lead.

**Subagent Definitions — Paling Relevan:**
```markdown
---
tools: [check_reachability, get_system_info, audit_dhcp]
model: claude-sonnet-4-6
skills: [network-health-check, router-unreachable]
---
Kamu adalah agen monitoring jaringan kampus...
```
File definisi per-agent yang mendeklarasikan tools allowlist dan skills yang aktif. Ini adalah bentuk native dari apa yang perlu kita implementasikan di LangGraph.

---

## 4. Pola yang Konsisten Antar Referensi

| Aspek | Evonic | OpenAI SDK | GStack | Anthropic | Gist (Copilot) |
|---|---|---|---|---|---|
| Skill binding | Per-agent via CLI | Via AGENTS.md routing | Sequential pipeline | Subagent definition | Tools allowlist per file |
| Handoff | Agent-to-agent native | Tool (`transfer_to_X`) | Sequential skill | Peer-to-peer mailbox | Phase-based delegation |
| Skill content | load → context → exec | SKILL.md + scripts | SKILL.md + role | Dimuat dari project settings | System prompt per file |
| Persistent memory | Per-agent enable/disable | Tidak eksplisit | GBrain | Tidak eksplisit | `memory` tool |
| Tool enforcement | Eksplisit per-agent | Via agent definition | Via skill definition | Tools allowlist | Tools allowlist per agent |
| Parallelism | Tidak eksplisit | Tidak eksplisit | Tidak eksplisit | Shared task list | Phase-based file conflict detection |
| Task framing | Tidak eksplisit | Tidak eksplisit | Tidak eksplisit | Eksplisit per subagent | WHAT not HOW dari orchestrator |

**Kesimpulan:** Semua referensi mengarah ke dua prinsip konsisten:
1. **Skill harus deklaratif** — tahu milik siapa, divalidasi terhadap tools yang tersedia
2. **Orchestrator mendelegasikan WHAT, specialist menentukan HOW** — termasuk kemampuan eksekusi paralel berdasarkan scope

---

## 5. Rekomendasi

### 5.1 Jalur A — Inkremental (Pendek)

Perubahan minimal, dampak langsung:

**Step 1: Tambah `agent` field ke skill frontmatter**
```yaml
---
name: router-unreachable
domain: monitoring
agent: monitor_agent          # ← tambah ini
triggers: [...]
tools: [check_reachability, check_ssh_access, get_system_info, run_command, get_router_log]
---
```

**Step 2: Validasi di SkillLibrary saat startup**
```python
def _validate_skill(skill: Skill, agent_tool_registry: dict[str, set]) -> list[str]:
    """Return list of missing tools for skill's declared agent."""
    agent_tools = agent_tool_registry.get(skill.agent, set())
    return [t for t in skill.tools if t not in agent_tools]
```

**Step 3: Fix 8 mismatch** — pilihan per-kasus:
- `bgp-diagnostics`, `ospf-neighbor-down` → tambah `get_router_config` ke `diagnose_agent`
- `router-unreachable` → tambah `run_command` ke `monitor_agent`
- `dhcp-pool-audit`, `utbk-client-monitor` → bind ke `monitor_agent`, tambah `search_device` ke `monitor_agent`

**Step 4: Supervisor inject hanya skill yang cocok dengan target agent**
```python
# Di supervisor_node — filter skills by target agent
skill_list = "\n".join(
    f"  {s.name}: {', '.join(s.triggers[:3])}"
    for s in _skill_lib.list_enabled()
    if s.agent == next_agent  # ← filter ini
)
```

**Step 5: Supervisor kirim task description eksplisit ke specialist**

Tambah field `task` di JSON response supervisor (terinspirasi dari prinsip "WHAT not HOW" gist):

```python
# Sebelum — specialist hanya dapat raw user message
{"next_agent": "monitor_agent", "relevant_skills": [...]}

# Sesudah — supervisor rumuskan task scope yang jelas
{
  "next_agent": "monitor_agent",
  "task": "Cek reachability semua router dan identifikasi yang tidak merespons",
  "scope": ["router-a", "router-b", "router-c"],   # opsional
  "relevant_skills": [...],
  "reasoning": "..."
}
```

**Step 6: Optimasi tool descriptions** — tulis ulang docstrings tool berdasarkan temuan mismatch dan pola penggunaan aktual. Anthropic melaporkan penurunan 40% waktu penyelesaian tugas dari langkah ini.

### 5.2 Jalur B — Agent Definitions (Menengah)

Buat file definisi per-agent yang mendeklarasikan tools dan skills secara eksplisit. Terinspirasi dari format `.agent.md` gist dan Claude Code subagent definitions. Lebih bersih jangka panjang, tapi memerlukan restructure `agents/tools.py` dan `agents/nodes.py`.

```
agents/definitions/
  monitor_agent.md
  diagnose_agent.md
  config_agent.md
  security_agent.md
  document_agent.md
```

Contoh format:

```yaml
# agents/definitions/monitor_agent.md
---
name: monitor_agent
alias: eko
model: gemma4:e4b
tools:
  - list_routers
  - check_reachability
  - check_ssh_access
  - get_system_info
  - get_interface_stats
  - get_interface_traffic
  - get_traffic_summary
  - get_top_talkers
  - get_queue_stats
  - get_traffic_all
  - get_dhcp_leases
  - get_router_leases
  - audit_dhcp
  - search_device        # ← ditambah dari fix mismatch
  - run_command          # ← ditambah dari fix mismatch
  - get_router_log
  - run_command_all
  - list_reports
  - get_report
  - get_report_section
  - get_report_toc
  - get_current_time
skills:
  - network-health-check
  - router-unreachable
  - dhcp-pool-audit
  - utbk-client-monitor
  - network-report
handoffs:
  - document_agent       # ← setelah data terkumpul
---
Kamu adalah agen monitoring jaringan kampus universitas (eko).
Infrastruktur menggunakan MikroTik RouterOS v6/v7.
```

Setiap file menjadi single source of truth untuk: role, tools, skills aktif, dan handoff destinations.

### 5.3 Jalur C — Handoff Pattern (Swarm, Jangka Panjang)

Setelah skill binding solid, tambahkan handoff sebagai tool:
```python
# monitor_agent mendapat tool untuk handoff ke document_agent
transfer_to_document = create_handoff_tool(
    agent_name="document_agent",
    description="Gunakan setelah data jaringan terkumpul dan perlu disusun jadi laporan"
)
```
Skill yang memiliki `handoff_to` field akan otomatis inject handoff tool ke agent-nya. Ini mengubah hub-and-spoke menjadi partial swarm tanpa full redesign.

---

## 6. Prioritas Implementasi

| Prioritas | Item | Impact | Effort |
|---|---|---|---|
| P1 | Fix 8 mismatch (Jalur A, Step 3) | Tinggi — mencegah silent failure | Rendah |
| P2 | Tambah `agent` field + validasi (Step 1-2) | Tinggi — enforcement | Rendah-Menengah |
| P3 | Supervisor filter skills by agent (Step 4) | Menengah — routing akurasi | Rendah |
| P4 | Supervisor kirim task description eksplisit (Step 5) | Menengah-Tinggi — kualitas output | Rendah |
| P5 | Optimasi tool descriptions (Step 6) | Menengah — performa LLM | Menengah |
| P6 | Agent definitions (Jalur B) | Tinggi jangka panjang | Tinggi |
| P7 | Phase-based parallel execution | Tinggi — performa jaringan besar | Sangat Tinggi |
| P8 | Handoff pattern (Jalur C) | Enabler swarm | Tinggi |

---

## 7. Catatan Desain

**Tentang `security_agent`:** Perlu evaluasi apakah ia layak sebagai agent terpisah atau lebih tepat sebagai "mode" dari diagnose_agent. Tidak ada unique tools = tidak ada kapabilitas yang eksklusif. Identitas hanya dari system prompt.

**Tentang `document_agent`:** Pertimbangkan memisahkan tanggung jawab — `report_agent` hanya untuk gathering + formatting, sementara `document_agent` murni untuk write ke file. Saat ini ia melakukan keduanya dengan 20 tools.

**Tentang progressive disclosure:** Saat ini semua skill body yang relevan di-inject ke system prompt sekaligus. Jika jumlah skill bertambah, ini bisa menghabiskan konteks. Pertimbangkan inject hanya nama + description awal, load body penuh hanya saat skill dipilih (seperti OpenAI SDK approach).

**Tentang persistent memory (GBrain pattern):** Nilai tertinggi untuk jaringan kampus adalah menyimpan baseline performa router (CPU, memory, traffic normal) sehingga agent bisa membandingkan kondisi saat ini vs baseline. Ini bisa diimplementasikan sebagai extension dari SkillLibrary atau sebagai tool terpisah.

**Tentang phase-based parallel execution:** Untuk jaringan kampus dengan 10+ router, eksekusi paralel per-router bisa mempersingkat waktu health check dari O(n) menjadi O(1). Prasyaratnya: supervisor harus mampu parse rencana kerja menjadi fase-fase dengan scope yang tidak overlap — mirip dengan file conflict prevention di gist. Ini adalah investasi engineering yang signifikan tapi memberi nilai besar untuk use case monitoring berkala.

**Tentang task description eksplisit:** Quick win yang underrated. Saat ini specialist menerima raw user message ("cek router-a") tanpa context tambahan dari supervisor. Jika supervisor merumuskan ulang task dengan scope dan format output yang jelas sebelum mendelegasikan, specialist bisa langsung fokus tanpa perlu "menebak" apa yang diminta.

---

## 8. Referensi

- [Evonic — Agentic AI Framework](https://github.com/anvie/evonic)
- [OpenAI Agents SDK — Handoffs](https://openai.github.io/openai-agents-python/handoffs/)
- [OpenAI — Skills for Agents SDK](https://developers.openai.com/blog/skills-agents-sdk)
- [GStack — Virtual Engineering Team](https://github.com/garrytan/gstack)
- [Anthropic — How We Built Our Multi-Agent Research System](https://www.anthropic.com/engineering/multi-agent-research-system)
- [Anthropic — Orchestrate teams of Claude Code sessions](https://code.claude.com/docs/en/agent-teams)
- [LangGraph Swarm](https://github.com/langchain-ai/langgraph-swarm-py)
- [LangGraph Supervisor](https://github.com/langchain-ai/langgraph-supervisor-py)
- [Ultralight Orchestration — Burke Holland's Gist](https://gist.github.com/burkeholland/0e68481f96e94bbb98134fa6efd00436)
