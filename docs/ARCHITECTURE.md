# Architecture Document — NetOps AI

**Versi:** 2.2  
**Tanggal:** 2026-05-16  
**Status:** Selesai

---

## 1. System Overview

NetOps AI adalah platform operasional jaringan kampus berbasis multi-agent LangGraph. Operator jaringan berinteraksi melalui TUI; query diproses oleh supervisor yang mendelegasikan ke specialist agent; agent mengeksekusi tools (SSH ke router) dengan panduan dari skill Markdown yang didefinisikan operator.

```
┌─────────────────────────────────────────────────────────────┐
│              TUI (tui_textual.py — aktif)                   │
│              TUI (tui.py — legacy ncurses)                  │
│   Input ──► agent.py public API ◄── Approval Modal         │
└─────────────────────────┬───────────────────────────────────┘
                           │ stream_agent_response()
┌─────────────────────────▼───────────────────────────────────┐
│                    agent.py (Orchestration)                  │
│                                                             │
│   SkillLibrary     AgentLoader       LangGraph StateGraph   │
│   (hot reload) ─┐  definitions/*.md  Supervisor ──► Spec.  │
│   skills/*.md   └──────────────────► Agent      Agents     │
└──────────────────────────────────────────┬──────────────────┘
                                           │ call tools
┌──────────────────────────────────────────▼──────────────────┐
│                       tools/*.py                            │
│   SSH Commands → MikroTik Routers (ROS v6 / v7)            │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. Component Architecture

### 2.1 Direktori Struktur

```
llmnetops/
├── agent.py                    ← Public API + NetworkOpsState + SkillLibrary singleton
├── tui_textual.py              ← UI aktif (Textual framework)
├── tui.py                      ← UI legacy (ncurses, zero LLM logic)
├── generate_reports.py         ← Standalone DHCP report generator
│
├── tools/                      ← 61 atomic SSH operations
│   ├── base.py                 ← SSH helper, config loader, _validate_router
│   ├── reachability.py         ← ICMP ping, SSH access check
│   ├── system.py               ← CPU, RAM, uptime
│   ├── routing.py              ← Route table, OSPF, BGP, router config
│   ├── interface.py            ← Interface stats, errors
│   ├── traffic.py              ← TX/RX rates, top talkers, queue stats, traffic_all
│   ├── dhcp.py                 ← DHCP lease queries, search device, audit_dhcp
│   ├── log.py                  ← Router log pull
│   ├── config_read.py          ← Run command (read-only), run_command_all
│   ├── config_write.py         ← run_command_write (butuh approval)
│   ├── config_backup.py        ← Export + save, diff, list backups
│   ├── config_yaml.py          ← Update config.yaml via agent
│   ├── security.py             ← User audit, firewall, NTP check
│   ├── diagnostic.py           ← Ping/traceroute dari router
│   ├── netbox.py               ← NetBox IPAM: drift check, sync
│   ├── report.py               ← List/read/section/toc laporan Markdown
│   ├── document.py             ← list/read/write template, write_document, write_skill
│   └── utility.py              ← list_routers, get_current_time
│
├── skills/                     ← Operator-defined Markdown knowledge files (32 skill)
│   ├── __init__.py             ← from skills.library import Skill, SkillLibrary
│   ├── library.py              ← SkillLibrary class + Skill dataclass + hot reload
│   ├── pedoman-agent.md        ← GLOBAL: conduct rules semua agent (dimuat otomatis)
│   ├── dhcp/                   ← 3 skill
│   ├── routing/                ← 4 skill
│   ├── monitoring/             ← 6 skill (termasuk morning-check)
│   ├── security/               ← 3 skill
│   ├── config/                 ← 6 skill (termasuk commissioning)
│   ├── interface/              ← 1 skill
│   ├── maintenance/            ← 1 skill
│   └── documents/              ← 5 file (skill + template)
│
├── agents/                     ← Multi-agent LangGraph
│   ├── __init__.py             ← from agents.graph import build_graph
│   ├── graph.py                ← StateGraph builder (START→supervisor→specialists→END)
│   ├── nodes.py                ← supervisor_node + 6 specialist nodes (loader-driven)
│   ├── tools.py                ← TOOL_MAP (flat, semua 61 tools)
│   ├── loader.py               ← AgentLoader + AgentDefinition dataclass
│   └── definitions/            ← Agent definition files (single source of truth)
│       ├── supervisor.md
│       ├── monitor_agent.md
│       ├── diagnose_agent.md
│       ├── config_agent.md
│       ├── security_agent.md
│       ├── document_agent.md
│       └── netbox_agent.md
│
├── docs/                       ← Project documentation
├── backups/                    ← Config backups (gitignored)
├── output/                     ← DHCP lease files (gitignored)
└── laporan/                    ← Generated reports (gitignored)
```

---

## 3. LangGraph Graph Topology

### 3.1 Nodes dan Edges

```
START
  │
  ▼
[supervisor]  ◄────────────────────────────────────────┐
  │                                                     │
  │ route berdasarkan intent + skill yang relevan       │
  │                                                     │
  ├──► [monitor_agent]   → tools: system, routing,     │
  │                        interface, traffic, dhcp,    │
  │                        log, report (23 tools)       │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [diagnose_agent]  → tools: reachability,        │
  │                        diagnostic, log, dhcp,       │
  │                        routing (13 tools)           │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [config_agent]    → tools: config_read,         │
  │                        config_write, config_backup  │
  │         │           ← interrupt() backup + write   │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [security_agent]  → tools: security, log,       │
  │                        config_read                  │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [netbox_agent]    → tools: netbox, list_routers │
  │                        check_reachability           │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  └──► [document_agent]  → tools: document, report,    │
                           template                     │
            │                                           │
            └───────────────────────────────────────── ┘
                                                        │
                                                       END
```

### 3.2 Routing Logic

Supervisor menggunakan LLM untuk menentukan:
1. Specialist agent mana yang paling tepat
2. Skill apa yang relevan untuk di-inject sebagai context
3. Apakah query butuh chain ke lebih dari satu specialist

```python
# Supervisor routing decision (JSON-mode LLM output)
{
    "next_agent": "monitor_agent | diagnose_agent | config_agent | security_agent | netbox_agent | document_agent | END",
    "relevant_skills": ["skill-name-1", "skill-name-2"],
    "reasoning": "<1 kalimat alasan>"
}
```

---

## 4. Shared State Design

```python
from typing import Annotated, TypedDict
from langgraph.graph.message import add_messages

class AgentLogEntry(TypedDict):
    timestamp: str
    source: str        # "supervisor" | "monitor_agent" | dll
    event_type: str    # "routing" | "tool_call" | "tool_result" | "approval"
    content: str

class ApprovalRequest(TypedDict):
    agent: str
    action: str
    risk_level: str    # "medium" | "high"
    details: dict

def _append(existing: list, new: list) -> list:
    return (existing or []) + (new or [])

class NetworkOpsState(TypedDict):
    messages:           Annotated[list, add_messages]           # LangGraph reducer
    next_agent:         str                                     # supervisor routing decision
    active_agent:       str                                     # currently executing agent
    injected_skills:    list[str]                               # skill names yang sedang aktif
    agent_log:          Annotated[list[AgentLogEntry], _append] # visible di TUI
    reasoning:          str                                     # debug reasoning supervisor
    pending_approval:   ApprovalRequest | None                  # blocked waiting for operator
    approval_decision:  str | None                              # "approved" | "rejected"
```

---

## 5. Skill System

### 5.1 Skill Naming Convention

Nama skill mengikuti pola **`[domain]-[capability-noun]`**:

```
monitoring/network-health-check.md     ← ✓ domain-capability
dhcp/dhcp-client-diagnostics.md        ← ✓ domain-capability
routing/ospf-diagnostics.md            ← ✓ domain-capability

monitoring/router-unreachable.md       ← ✗ terlalu spesifik (lama)
routing/ospf-neighbor-down.md          ← ✗ event bukan capability (lama)
```

Domain yang tersedia: `monitoring`, `dhcp`, `routing`, `security`, `config`, `documents`.

### 5.2 Skill File Format

Setiap skill adalah file `.md` dengan struktur:

```markdown
---
name: dhcp-client-diagnostics
domain: dhcp
triggers:
  - client tidak dapat IP
  - DHCP tidak berfungsi
  - no IP address
tools:
  - search_device
  - get_dhcp_leases
  - get_router_log
  - run_diagnostic
approval_required: false
enabled: true
---

# [Judul Skill]

## Konteks
[Kapan skill ini digunakan]

## Langkah Prosedur
[Workflow yang harus diikuti agent — natural language]

## Output yang Diharapkan
[Format dan isi output yang diinginkan operator]
```

**Frontmatter YAML** → dibaca runtime untuk routing dan tool-loading.  
**Body Markdown** → di-inject sebagai system context ke specialist agent.

### 5.3 Daftar Skill (32 skill aktif)

| Domain | Skill | Agent | Keterangan |
|--------|-------|-------|------------|
| monitoring | `network-health-check` | monitor | Health check menyeluruh semua router |
| monitoring | `network-reachability` | monitor | Investigasi router unreachable |
| monitoring | `network-traffic-analysis` | monitor | Analisis bandwidth & top talkers |
| monitoring | `network-status-report` | monitor | Ringkasan status jaringan |
| monitoring | `morning-check` | monitor | Morning check harian — reachability + BGP + traffic |
| monitoring | `capacity-planning` | monitor | Analisis utilisasi dan proyeksi kapasitas |
| monitoring | `mtu-mismatch-diagnostics` | diagnose | Diagnosa MTU mismatch antar segmen |
| monitoring | `netbox-read` | monitor/netbox | Query NetBox via agent |
| dhcp | `dhcp-pool-audit` | monitor | Audit utilisasi DHCP pool |
| dhcp | `dhcp-client-diagnostics` | diagnose | Diagnosa client gagal dapat IP |
| dhcp | `utbk-session-monitoring` | monitor | Monitoring peserta UTBK |
| dhcp | `static-lease-management` | config | Kelola static lease DHCP |
| routing | `bgp-diagnostics` | diagnose | Diagnosa BGP session/prefix |
| routing | `ospf-diagnostics` | diagnose | Diagnosa OSPF neighbor/state |
| routing | `bgp-prefix-leak` | diagnose | Deteksi dan respons BGP prefix leak |
| routing | `static-route-management` | config | Kelola static route |
| security | `security-audit` | security | Audit postur keamanan router |
| security | `brute-force-response` | security | Deteksi dan blokir brute force |
| security | `firewall-management` | security/config | Kelola aturan firewall |
| config | `config-backup` | config | Prosedur backup konfigurasi |
| config | `config-change` | config | Workflow perubahan konfigurasi dengan approval |
| config | `commissioning` | config | Komisioning router baru dari fresh |
| config | `vlan-provisioning` | config | Provisioning VLAN baru |
| config | `router-discovery` | config | Deteksi dan registrasi router baru |
| config | `netbox-sync` | config/netbox | Sync konfigurasi ke NetBox |
| interface | `link-diagnostics` | diagnose | Diagnosa masalah interface/link |
| maintenance | `router-maintenance` | config | Prosedur maintenance router |
| documents | `document-writing` | document | Penulisan laporan ke file |
| documents | `skill-authoring` | document | Membuat skill baru |

**File khusus (bukan skill biasa):**
- `skills/pedoman-agent.md` — Conduct rules global, dimuat otomatis ke semua agent system prompt. Tidak perlu dicantumkan di definisi agent manapun. Edit file ini untuk mengubah perilaku semua agent sekaligus.

### 5.4 SkillLibrary

File: `skills/library.py`. Singleton `_skill_lib` dibuat di `agent.py` saat modul di-import.

```python
@dataclass
class Skill:
    name: str; domain: str; triggers: list[str]; tools: list[str]
    approval_required: bool; enabled: bool; body: str; path: Path

class SkillLibrary:
    def __init__(self, skills_dir: Path)
    def _load_all(self) -> None         # scan skills/**/*.md
    def list_enabled(self) -> list[Skill]
    def start_watcher(self) -> None     # watchfiles background daemon thread
    def stop_watcher(self) -> None
    def find_relevant(self, query: str, domain: str = None) -> list[Skill]
    def get_by_name(self, name: str) -> Skill | None
    def inject_context(self, skills: list[Skill]) -> str  # gabungkan body Markdown
```

### 5.5 Hot Reload Mechanism

```
Operator: edit/tambah/hapus skills/**/*.md
                │
     watchdog (watchfiles library)
                │
     SkillLibrary._reload(changed_file)
                │
     skill tersedia di request berikutnya
```

### 5.6 Skill Selection

```
Query: "kenapa Lab5 tidak dapat IP?"
            │
   [1] Supervisor LLM baca daftar skill triggers
            │
   [2] Match: "tidak dapat IP" → triggers di diagnose-dhcp-client.md
            │
   [3] Load skill body → inject ke diagnose_agent context
            │
   [4] diagnose_agent ikuti prosedur dalam skill Markdown

Query: "/skill bgp-diagnostics DTI"
            │
   [explicit] SkillLibrary.get_by_name("bgp-diagnostics")
            │
   load → inject ke agent yang sesuai domain
```

---

## 6. Agent Definition System

### 6.1 Konsep: Single Source of Truth

Setiap agent didefinisikan dalam satu file Markdown di `agents/definitions/`. File ini menjadi **single source of truth** untuk:
- Tools yang dimiliki agent
- Skills yang digunakan agent
- LLM parameters (model, context window, max tokens, timeout)
- System prompt (body Markdown)
- Agent mana yang boleh di-handoff

### 6.2 Format Definition File

```markdown
---
name: monitor_agent
alias: eko
description: >
  Status jaringan kampus, health check semua router, DHCP overview,
  interface stats, dan traffic monitoring.
model: gemma4:e4b
num_ctx: 16384        # token context window LLM
num_predict: 2048     # max output tokens
context_window: 10    # jumlah pesan history yang dimasukkan ke LLM
timeout: 300          # timeout LLM (detik)
tools:
  - list_routers
  - check_reachability
  - ...
skills:
  - network-health-check
  - network-traffic-analysis
  - ...
handoff_to:
  - document_agent
---
Kamu adalah Eko, agen monitoring jaringan kampus universitas.
[system prompt body...]
```

### 6.3 LLM Parameters per Agent

Model aktif: **qwen3.5:9b** (lihat Section 6.8 untuk alasan pemilihan model).

| Agent | num_ctx | num_predict | context_window | timeout | Alasan |
|-------|---------|-------------|----------------|---------|--------|
| supervisor | 8192 | 2048 | 6 | 60s | Output JSON routing; qwen tokenizer 2.2× lebih verbose |
| monitor_agent | 32768 | 16384 | 20 | 600s | Tool results 17+ router + morning check multi-step |
| diagnose_agent | 16384 | 2048 | 10 | 300s | Logs + routing table + analisis RCA |
| config_agent | 16384 | 2048 | 10 | 180s | Config export per router + commissioning |
| security_agent | 16384 | 2048 | 10 | 300s | Audit results + log parsing |
| netbox_agent | 16384 | 2048 | 10 | 300s | NetBox API results bisa verbose |
| document_agent | 24576 | 4096 | 20 | 600s | Seluruh history percakapan + template |

> **Catatan tokenizer:** qwen3.5:9b menghasilkan ~2.2× lebih banyak token dibanding gemma4:e4b
> untuk teks yang sama (diukur: 1791 vs 817 token untuk system prompt supervisor yang identik).
> Semua nilai `num_ctx` sudah disesuaikan dengan faktor ini.

### 6.4 AgentLoader

File: `agents/loader.py`. Instance `_agent_loader` dibuat di `agents/nodes.py` saat modul di-import.

```python
@dataclass
class AgentDefinition:
    name: str; alias: str; description: str; model: str
    tools: list[str]; skills: list[str]; handoff_to: list[str]
    approval_required_tools: list[str]; body: str; path: Path
    num_ctx: int; num_predict: int; context_window: int; timeout: int

class AgentLoader:
    def __init__(self, definitions_dir: Path)
    def _load_all(self) -> None          # scan agents/definitions/*.md
    def reload(self) -> None             # re-read dari disk
    def validate(tool_map, skill_library) -> list[str]  # validasi bindings
    def get(name: str) -> AgentDefinition | None
    def all() -> list[AgentDefinition]
    def tool_list(agent_name: str) -> list[str]
    def skill_list(agent_name: str) -> list[str]
    def system_prompt(agent_name: str) -> str
```

### 6.5 Validasi Binding

`AgentLoader.validate()` dijalankan saat startup dan memeriksa tiga hal:
1. `agent.tools` → semua ada di `TOOL_MAP`
2. `agent.skills` → semua ada di `SkillLibrary`
3. `skill.tools ⊆ agent.tools` → agent punya semua tool yang dibutuhkan skill-nya

### 6.6 Menambah Agent Baru

Cukup buat file `agents/definitions/nama_agent.md` dengan frontmatter yang benar — tidak perlu menyentuh `nodes.py` atau `tools.py`.

### 6.7 Metodologi Penentuan LLM Parameters

#### Konsep: Token

Token adalah satuan terkecil yang diproses LLM. Estimasi kasar:

| Tipe Konten | Estimasi Token |
|-------------|---------------|
| 1 karakter Latin/Indonesia | ~0.25 token |
| 1 kata rata-rata | ~1.3 token |
| 1 KB teks biasa | ~250 token |
| 1 KB JSON/structured | ~200 token |

#### Formula num_ctx

```
num_ctx ≥ T_system + T_history + T_tools + num_predict

T_system  = agent_body + tool_list + rules + skill_context
T_history = context_window × avg_message_tokens
T_tools   = max_iterations × avg_tool_result_tokens
```

> `num_ctx` harus mencakup **seluruh input** sekaligus **ruang output** (`num_predict`).
> Gunakan kelipatan 2048 untuk efisiensi KV-cache. Tambah safety margin ~30%.

#### Estimasi Ukuran Komponen Sistem

| Komponen | Token |
|----------|-------|
| Agent body (300-500 kata) | 200–500 |
| Tool list per tool (nama saja) | ~5 |
| Aturan wajib tool calling (5 baris) | ~150 |
| Skill context (1 skill body) | 300–800 |
| Human message rata-rata | 30–100 |
| AI message rata-rata | 100–500 |

#### Estimasi Ukuran Tool Result

| Tool | Kondisi | Token |
|------|---------|-------|
| `check_reachability` | 1 router | ~50 |
| `check_ssh_access` | 1 router | ~30 |
| `get_system_info` | 1 router | ~200 |
| `get_interface_stats` | semua interface | ~500 |
| `get_interface_traffic` | 1 interface | ~100 |
| `get_traffic_summary` | semua interface | ~400 |
| `get_top_talkers` | top 10 IP | ~300 |
| `get_queue_stats` | semua queue | ~400 |
| `get_traffic_all` | 5 router | ~1000 |
| `get_dhcp_leases` | 500 client | ~2500 |
| `get_router_leases` | 200 client | ~1000 |
| `audit_dhcp` | 5 router | ~2000 |
| `search_device` | 1 device | ~100 |
| `get_routing_full` | 20 route + OSPF | ~1500 |
| `get_router_config` | full export | 2000–5000 |
| `get_router_log` | 100 baris | ~800 |
| `run_command` | output singkat | 100–500 |
| `audit_security` | 1 router | ~600 |
| `run_diagnostic` | ping/traceroute | ~300 |
| `read_template` | template MD | ~1500 |
| `get_report` | laporan penuh | 2000–4000 |

#### Contoh: monitor_agent (worst case — health check 5 router)

```
T_system:
  agent body               =  400 token
  tool list (23 × 5)       =  115 token
  aturan wajib             =  150 token
  skill context (1 skill)  =  400 token
                           ─────────────
  Subtotal                 = 1065 token

T_history:
  10 pesan × 150 token/msg = 1500 token

T_tools (worst-case sequence):
  check_reachability × 5   =  250 token
  get_system_info × 5      = 1000 token
  audit_dhcp × 1           = 2000 token
  get_traffic_all × 1      = 1000 token
                           ─────────────
  Subtotal                 = 4250 token

num_predict (output)       = 2048 token
                           ═════════════
Total                      = 8863 token
→ Pilih 16384  (kelipatan 2048 ke atas, safety margin ~85%)
```

#### Contoh: supervisor (single call, no tools)

```
T_system:
  supervisor body          =  300 token
  agent descriptions (5)   =  250 token
  skill list (12 skill)    =  200 token
  JSON format instructions =  150 token
                           ─────────────
  Subtotal                 =  900 token

T_history:
  6 pesan × 100 token/msg  =  600 token

T_tools                    =    0 token  (supervisor tidak panggil tool)

num_predict (JSON output)  =  256 token
                           ═════════════
Total                      = 1756 token
→ Pilih 4096  (kelipatan 2048, safety margin ~133%)
```

#### Contoh: document_agent (worst case — kompilasi laporan panjang)

```
T_system:
  agent body               =  500 token
  tool list (20 × 5)       =  100 token
  aturan wajib             =  150 token
  skill context (1 skill)  =  600 token
                           ─────────────
  Subtotal                 = 1350 token

T_history:
  20 pesan × 500 token/msg = 10000 token
  (termasuk output semua agent sebelumnya)

T_tools:
  read_template × 1        = 1500 token
  get_report × 1           = 3000 token
                           ─────────────
  Subtotal                 = 4500 token

num_predict (dokumen penuh)= 4096 token
                           ═════════════
Total                      = 19946 token
→ Pilih 24576  (kelipatan 2048, safety margin ~23%)
```

#### Metodologi num_predict

Estimasi panjang output yang diharapkan, lalu beri margin 2–3×:

| Output | Estimasi Aktual | num_predict |
|--------|----------------|-------------|
| JSON routing supervisor | ~50 token | 256 |
| Health check report (5 router) | 500–1000 token | 2048 |
| RCA analysis + evidence | 500–2000 token | 2048 |
| Config summary + diff | 500–1500 token | 2048 |
| Audit report (4 area) | 800–2000 token | 2048 |
| Laporan operasional lengkap | 2000–4000 token | 4096 |

#### Metodologi timeout

```
timeout ≥ max_iterations × (t_inference + t_tool_call)

t_inference  ≈ 5–25 detik  (tergantung num_predict dan hardware)
t_tool_call  ≈ 1–3 detik   (SSH ke MikroTik + parsing)
```

| Agent | max_iter | t_per_iter | Estimasi | timeout |
|-------|----------|------------|----------|---------|
| supervisor | 1 | ~10s | ~10s | 60s |
| monitor_agent | 12 | ~15s | ~180s | 300s |
| diagnose_agent | 12 | ~15s | ~180s | 300s |
| config_agent | 12 | ~12s | ~144s | 180s |
| security_agent | 12 | ~15s | ~180s | 300s |
| document_agent | 12 | ~30s | ~360s | 600s |

> `document_agent` lebih lama karena `num_predict=4096` — inferensi teks panjang lebih berat.

#### Metodologi context_window

Pilih jumlah pesan history yang cukup untuk memahami task saat ini tanpa membawa noise dari percakapan jauh sebelumnya:

| Pola Kerja | context_window |
|------------|----------------|
| Single-shot routing (supervisor) | 6 |
| Task dalam satu giliran (specialist) | 10 |
| Sintesis lintas agent (document_agent) | 20 |
| Investigasi panjang / troubleshooting | 15–20 |

#### Tanda Perlu Penyesuaian

| Gejala | Penyebab | Solusi |
|--------|----------|--------|
| Output terpotong di tengah kalimat | `num_predict` terlalu kecil | Naikkan `num_predict` |
| Error "context length exceeded" | `num_ctx` kurang | Naikkan `num_ctx` atau turunkan `context_window` |
| Agent "lupa" instruksi awal saat tools banyak | `num_ctx` hampir penuh | Naikkan `num_ctx` |
| Timeout error di saat beban ringan | `timeout` terlalu pendek | Naikkan `timeout` |
| Respons sangat lambat walau output pendek | `num_predict` terlalu besar | Turunkan `num_predict` |

### 6.8 Model Selection & VRAM Constraint

#### Constraint Hardware

Server Ollama (`rogbox.local.id`) menggunakan GPU dengan **12GB VRAM**. Dengan constraint ini,
hanya **satu model lokal** yang dapat dimuat sekaligus — tidak ada ruang untuk dua model
secara bersamaan. Jika agent berbeda menggunakan model berbeda, Ollama harus unload lalu
load model baru → overhead **~5 detik per swap**.

Arsitektur yang optimal: **semua agent menggunakan model yang sama** agar model selalu hot
di VRAM tanpa swap overhead.

#### Model yang Tersedia

| Model | VRAM | Parameters | Quantization | Status |
|-------|------|------------|--------------|--------|
| `gemma4:e4b` | 8.9 GB | 8.0B | Q4_K_M | tidak dipakai |
| `gemma4:e2b` | 6.7 GB | 5.1B | Q4_K_M | tidak dipakai |
| `qwen3.5:9b` | 6.1 GB | 9.7B | Q4_K_M | **aktif** |
| `kimi-k2.5:cloud` | 0 GB | — | cloud | tersedia |

#### Alasan Memilih qwen3.5:9b

| Kriteria | gemma4:e4b | qwen3.5:9b | Keunggulan |
|----------|-----------|-----------|------------|
| VRAM | 8.9 GB | **6.1 GB** | 2.8 GB lebih hemat |
| VRAM headroom | 3.1 GB | **5.9 GB** | KV cache lebih lega |
| Parameters | 8.0B | **9.7B** | Model lebih capable |
| JSON output | ❌ sering kosong | ✅ reliabel | Routing supervisor benar |
| Token per output (JSON) | 57–72 | **36** | Lebih efisien |
| Tool calling (17 router) | perlu 2–3 pass | **1 pass** | Tidak loop |
| Forced summary | perlu | tidak perlu | Lebih bersih |

#### Perbandingan Karakteristik Model: Gemma 4 vs Qwen 3.5

##### Arsitektur & Keluarga Model

| Aspek | Gemma 4 (Google DeepMind) | Qwen 3.5 (Alibaba) |
|-------|--------------------------|---------------------|
| Arsitektur | Transformer + thinking mode | Transformer + thinking mode |
| Varian tersedia | e2b (5.1B), e4b (8.0B) | 9b (9.7B) |
| Quantization (lokal) | Q4_K_M | Q4_K_M |
| Bahasa utama | English-first, multilingual | Multilingual kuat (termasuk ID) |
| Lisensi | Gemma Terms of Use | Apache 2.0 |

##### Thinking Mode

Kedua model adalah **thinking model** — menghasilkan token reasoning internal sebelum output.
Perbedaan penting dalam konteks sistem ini:

| Perilaku | Gemma 4 | Qwen 3.5 |
|----------|---------|----------|
| Thinking tokens masuk `content` | ❌ tidak (tersembunyi) | ✅ sebagian (dalam `<think>` tags) |
| Token thinking habiskan `num_predict` | ✅ ya | ✅ ya |
| Token output setelah thinking | Sering 0 jika `num_predict` kecil | Konsisten ada output |
| Minimum `num_predict` untuk JSON | ~2048 (thinking 90%+ token) | ~256 (thinking lebih efisien) |

**Gemma 4 problem:** Dengan `num_predict=256`, model menghabiskan semua token untuk berpikir
internal tanpa pernah menulis output. Terdeteksi via: `done_reason: 'length'`, `content: ''`,
`eval_count == num_predict`.

**Qwen 3.5 behavior:** Thinking lebih efisien, output JSON supervisor hanya butuh 36 token,
jauh di bawah limit `num_predict=2048`.

##### Tokenizer

| Metrik | Gemma 4 e4b | Qwen 3.5 9b |
|--------|-------------|-------------|
| Prompt supervisor (token) | 817 | 1791 |
| Rasio verbositas | 1.0× (baseline) | **2.2×** |
| Dampak ke `num_ctx` | baseline | perlu ~2× lebih besar |

Tokenizer Qwen lebih verbose karena perbedaan vocabulary size dan subword splitting.
Teks bahasa Indonesia cenderung ter-tokenize lebih detail di Qwen vs Gemma.

##### Kemampuan Tool Calling

| Skenario | Gemma 4 e4b | Qwen 3.5 9b |
|----------|-------------|-------------|
| Panggil 1 tool | ✅ | ✅ |
| Panggil tool berurutan (17 router) | ✅ tapi sering loop | ✅ 1 pass selesai |
| Batch tool calls (1 LLM call, N tools) | Jarang | Lebih sering |
| Response setelah banyak tool results | Sering kosong | Konsisten ada isi |
| Kebutuhan forced summary fallback | Ya | Tidak |

##### Kapan Mempertimbangkan Kembali ke Gemma

- Jika `qwen3.5:9b` ditarik dari Ollama registry atau tidak tersedia
- Jika ada Gemma 4 versi yang lebih besar (misal 27B) dengan VRAM yang cukup
- Jika task membutuhkan karakteristik khusus Gemma (vision, dll)

#### VRAM Budget dengan qwen3.5:9b

```
Model weights:          6.1 GB
KV cache (num_ctx max): ~2.0 GB  (estimate untuk 24576 token document_agent)
Overhead sistem:        ~0.5 GB
─────────────────────────────────
Total estimate:         ~8.6 GB  (dari 12 GB tersedia)
Headroom:               ~3.4 GB
```

---

## 7. Human-in-the-Loop (Approval)

### 7.1 Flow

```
config_agent memutuskan perlu backup
          │
    interrupt(ApprovalRequest)     ← LangGraph pause
          │
    agent_log ← {"event_type": "approval_required", ...}
          │
    TUI: Agent Activity tampilkan modal
          │
    Operator: Y (approved) / N (rejected)
          │
    graph.invoke(Command(resume="approved"))
          │
    config_agent lanjut / batalkan
```

### 7.2 Risk Levels

| Level | Contoh Aksi | Default |
|---|---|---|
| `medium` | Config backup, export config | Require approval |
| `high` | Write operations (`run_command_write`) | Require approval |
| `low` | Read-only queries | Auto-proceed |

**Auto-backup enforcement:** `config_node` menjamin backup selalu dilakukan sebelum `run_command_write` pertama ke setiap router, terlepas dari urutan tool yang dipilih LLM. Ini enforced di code level (`_backed_up_routers` set per invocation), bukan di instruksi LLM.

---

## 8. Public API (agent.py → tui.py / tui_textual.py)

```python
# Inisialisasi
def create_agent(thread_id: str) -> tuple[CompiledStateGraph, RunnableConfig]
def reset_agent(thread_id: str) -> tuple[CompiledStateGraph, RunnableConfig]

# Eksekusi
def stream_agent_response(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    message: str
) -> Iterator[tuple[str, str]]
# Yields: (event_type, content)
# event_type: "routing" | "tool_call" | "tool_result" | "ai" | "approval_required" | "error"

# Approval — dua varian:
def submit_approval(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    decision: str           # "approved" | "rejected"
) -> None
# Headless/non-streaming. Pakai ini untuk testing atau CLI satu-shot.

def resume_after_approval(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    decision: str
) -> Iterator[tuple[str, str]]
# Streaming variant — WAJIB dipakai TUI agar interrupt berikutnya
# (multi-step write chain) tetap sampai ke UI.

# Info
def get_available_skills() -> list[dict]    # untuk TUI display
def get_agent_status() -> dict
def get_token_metrics(n: int = 100) -> list[dict]  # ctx/pred usage per message
```

---

## 9. TUI Interface

### 9.1 tui_textual.py (aktif — Phase 8)

Textual framework. Layout: single-panel chat mendominasi layar penuh.

```
┌─ [eko — idle] ───────────────────────────────────────────────┐
│ [14:32:01] → routing ke monitor_agent (skill: morning-check)  │
│ [14:32:01] ⚙ check_reachability(DTI) ✓ 1.2ms                 │
│ [14:32:02] ⚙ get_system_info(DTI) ✓ CPU 12%, up 14d          │
│ ...                                                           │
│ ┌ AI ──────────────────────────────────────────────────────┐  │
│ │ ✅ 15 normal · ⚠️ 1 perhatian · 🚨 0 kritis             │  │
│ │ ...                                                      │  │
│ └──────────────────────────────────────────────────────────┘  │
├───────────────────────────────────────────────────────────────┤
│ ctx ████░░ 19% · pred ████░░ 26% · 8 tools · 00:02:14        │
└───────────────────────────────────────────────────────────────┘
```

**Approval modal** — Textual `ModalScreen`, muncul saat `approval_required`:
```
╔══════════════════════════════════════╗
║  ⚠  KONFIRMASI TINDAKAN             ║
║  Agent  : joko (config_agent)       ║
║  Aksi   : Backup FILKOM-CORE        ║
║  Risk   : MEDIUM                    ║
║  [Setuju, jalankan]  [Tolak]        ║
╚══════════════════════════════════════╝
```

**Keyboard shortcuts:** `ctrl+y` copy, `ctrl+b` copy raw, `ctrl+e` suspend + view log di `less`

### 9.2 tui.py (legacy ncurses)

Tetap berfungsi. Dipertahankan sampai `tui_textual.py` verified stable di produksi.

---

## 10. Tools per Agent (Tool Access Matrix)

| Tool | monitor | diagnose | config | security | document |
|---|:---:|:---:|:---:|:---:|:---:|
| `list_routers` | ✓ | ✓ | ✓ | ✓ | ✓ |
| `check_reachability` | ✓ | ✓ | | | ✓ |
| `check_ssh_access` | ✓ | ✓ | | | |
| `get_system_info` | ✓ | ✓ | | | ✓ |
| `get_routing_full` | ✓ | ✓ | | | |
| `get_router_config` | | ✓ | ✓ | | |
| `get_interface_stats` | ✓ | | | | ✓ |
| `get_interface_traffic` | ✓ | | | | |
| `get_traffic_summary` | ✓ | | | | ✓ |
| `get_top_talkers` | ✓ | | | | |
| `get_queue_stats` | ✓ | | | | |
| `get_traffic_all` | ✓ | | | | |
| `get_dhcp_leases` | ✓ | ✓ | | | ✓ |
| `get_router_leases` | ✓ | ✓ | | | |
| `audit_dhcp` | ✓ | | | | ✓ |
| `search_device` | ✓ | ✓ | | | |
| `get_router_log` | ✓ | ✓ | | ✓ | ✓ |
| `run_command` | ✓ | ✓ | ✓ | ✓ | |
| `run_command_all` | ✓ | | ✓ | ✓ | ✓ |
| `backup_router_config` | | | ✓ ⚠ | | |
| `list_backups` | | | ✓ | | |
| `diff_config` | | | ✓ | | |
| `audit_security` | | | | ✓ | ✓ |
| `run_diagnostic` | | ✓ | | | |
| `list_reports` | ✓ | | ✓ | | ✓ |
| `get_report` | ✓ | | ✓ | | ✓ |
| `get_report_section` | ✓ | | | | ✓ |
| `get_report_toc` | ✓ | | | | ✓ |
| `list_templates` | | | | | ✓ |
| `read_template` | | | | | ✓ |
| `write_document` | | | | | ✓ |
| `create_template` | | | | | ✓ |
| `write_skill` | | | | | ✓ |
| `get_current_time` | ✓ | ✓ | ✓ | ✓ | ✓ |

⚠ `backup_router_config` dan `run_command_write` memerlukan persetujuan operator (interrupt gate).

**Total: 61 tool atomic** | Source of truth: `agents/definitions/*.md` + `AgentLoader.validate()`

> Tabel di atas merepresentasikan tool utama. Tool tambahan (netbox, config_write, config_yaml, dll) terdaftar di `agents/tools.py:TOOL_MAP`. Kolom `netbox_agent` belum ditampilkan — lihat `agents/definitions/netbox_agent.md`.

---

## 11. Dependencies Baru

```
# Tambahan dari branch main
watchfiles          ← hot reload skill files
```

Semua dependency lain inherited dari branch `main`:
```
langchain-ollama
langgraph >= 0.2
langchain-core
pyyaml
requests
paramiko            ← via mikrotik_agent.py
```

---

## 12. Learning Loop — Sistem Pembelajaran Berkelanjutan

### 12.1 Konsep: Two-Tier Intelligence

Sistem menggunakan dua model dengan peran berbeda:

| | qwen3.5:9b (lokal) | Claude (Claude Code) |
|---|---|---|
| **Peran** | Runtime operasional | Quality gatekeeper |
| **Kecepatan** | Cepat (~2-5s/call) | Lambat (interaktif) |
| **Privasi** | Fully local | Session lokal, tidak kirim ke API |
| **Kualitas** | Terbatas (9.7B params) | Tinggi |
| **Kapan aktif** | Setiap request harian | Saat development / review |

Data jaringan sensitif (log, IP, credential) tidak pernah dikirim ke luar — qwen3.5:9b menangani semua operasional. Claude hanya membaca file lokal dalam session Claude Code.

### 12.2 Loop Pembelajaran

```
┌─────────────────────────────────────────────────────────┐
│  1. OPERASIONAL  (qwen3.5:9b)                           │
│                                                         │
│  Operator request → Supervisor route → Specialist       │
│  → Tool calls (SSH ke router) → Response ke operator   │
└───────────────────────────┬─────────────────────────────┘
                            │ jika output salah / kurang baik
                            ▼
┌─────────────────────────────────────────────────────────┐
│  2. KNOWLEDGE GROWTH  (qwen3.5:9b draft, Claude review) │
│                                                         │
│  Operator: "buat skill untuk X"                         │
│  qwen3.5 → write_skill() → skills/.pending/X.md        │
│                          ↓                              │
│  python tests/review.py show X   ← buka di Claude Code │
│  Claude: cek checklist, syntax RouterOS, logika         │
│                          ↓                              │
│  python tests/review.py approve X  → skill live        │
│  python tests/eval.py              → verifikasi regresi │
└───────────────────────────┬─────────────────────────────┘
                            │ catat temuan
                            ▼
┌─────────────────────────────────────────────────────────┐
│  3. INSTITUTIONAL MEMORY  (docs/teaching-log.md)        │
│                                                         │
│  Format per entri:                                      │
│    Apa yang gagal → Root cause → Perubahan → Hasil      │
│                                                         │
│  Tujuan: agar keputusan desain tidak hilang dan         │
│  kesalahan yang sama tidak terulang di sesi berikutnya  │
└─────────────────────────────────────────────────────────┘
```

### 12.3 Komponen Sistem Pembelajaran

#### Scenario Library (`tests/scenarios/*.yaml`)

File YAML yang mendefinisikan skenario evaluasi. Setiap skenario punya:
- `input` — pesan user yang akan dikirim ke agent
- `expected_agents` — agent yang harus dipilih supervisor
- `expected_tools` — tools yang harus dipanggil specialist
- `acceptance_criteria` — daftar checks yang harus pass

Skenario tersedia (per v1.3.0):

| ID | Domain | Agent Target |
|----|--------|-------------|
| `bgp-ospf-report` | Routing | diagnose_agent + document_agent |
| `health-check` | Monitoring | monitor_agent |
| `brute-force-detect` | Security | security_agent |
| `dhcp-exhaustion` | DHCP | monitor_agent |
| `interface-flapping` | Diagnosa | diagnose_agent |
| `skill-authoring` | Meta | document_agent |

#### Evaluator (`tests/eval.py`)

```bash
python tests/eval.py                  # semua scenarios, mock mode
python tests/eval.py health-check     # satu scenario
python tests/eval.py --lab            # tool asli (butuh containerlab)
python tests/eval.py -v               # verbose events
```

**Mock mode** (default): TOOL_MAP di-patch dengan fixture data dari `tests/mocks/fixtures.py`.
LLM tetap jalan sungguhan — yang di-mock hanya koneksi SSH ke router.
Cocok untuk regresi cepat tanpa infrastruktur nyata.

**Lab mode** (`--lab`): menggunakan koneksi nyata ke containerlab. Untuk validasi akhir
sebelum deploy ke produksi.

#### Pending Review Queue (`skills/.pending/`)

Skill yang digenerate agent via `write_skill` masuk ke `skills/.pending/` — tidak langsung live.

```bash
python tests/review.py                      # list pending
python tests/review.py show <name>          # tampilkan + checklist 9 item
python tests/review.py approve <name>       # pindah ke production, hot-reload
python tests/review.py reject <name>        # hapus dari pending
```

Checklist review (`tests/review.py show`) memverifikasi:
- Naming convention `[domain]-[capability-noun]`
- Field frontmatter wajib lengkap
- Tool disebutkan eksplisit di body
- Ada contoh output (code block)
- Tidak ada instruksi ambigu
- Panjang < 150 baris

#### Teaching Log (`docs/teaching-log.md`)

Log per sesi dengan format:
```
## [YYYY-MM-DD] — [topik]
Apa yang gagal → root cause → perubahan → hasil
```

Berbeda dengan git log (yang mencatat *apa* yang berubah), teaching log mencatat
*mengapa* keputusan diambil — konteks yang hilang setelah kode ditulis.

### 12.4 Prinsip Skill untuk Model Kecil

Lihat `skills/documents/skill-authoring.md` — Section "Prinsip untuk Model Kecil (qwen3.5:9b)".

Ringkasan: qwen3.5:9b bekerja jauh lebih baik dengan instruksi prosedural eksplisit
(sebutkan tool secara eksplisit, berikan contoh output) daripada instruksi deskriptif
("analisis dengan bijak", "pertimbangkan faktor yang relevan").
