# Architecture Document — NetOps AI

**Versi:** 2.0  
**Tanggal:** 2026-05-08  
**Status:** Selesai

---

## 1. System Overview

NetOps AI adalah platform operasional jaringan kampus berbasis multi-agent LangGraph. Operator jaringan berinteraksi melalui TUI; query diproses oleh supervisor yang mendelegasikan ke specialist agent; agent mengeksekusi tools (SSH ke router) dengan panduan dari skill Markdown yang didefinisikan operator.

```
┌─────────────────────────────────────────────────────────────┐
│                         TUI (tui.py)                        │
│   Input ──► agent.py public API ◄── Agent Activity Panel   │
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
├── tui.py                      ← UI only (zero LLM logic)
├── generate_reports.py         ← Standalone DHCP report generator
│
├── tools/                      ← 34 atomic SSH operations
│   ├── base.py                 ← SSH helper, config loader, _validate_router
│   ├── reachability.py         ← ICMP ping, SSH access check
│   ├── system.py               ← CPU, RAM, uptime
│   ├── routing.py              ← Route table, OSPF, BGP, router config
│   ├── interface.py            ← Interface stats, errors
│   ├── traffic.py              ← TX/RX rates, top talkers, queue stats, traffic_all
│   ├── dhcp.py                 ← DHCP lease queries, search device, audit_dhcp
│   ├── log.py                  ← Router log pull
│   ├── config_read.py          ← Run command (read-only), run_command_all
│   ├── config_backup.py        ← Export + save, diff, list backups
│   ├── security.py             ← User audit, firewall, NTP check
│   ├── diagnostic.py           ← Ping/traceroute dari router
│   ├── report.py               ← List/read/section/toc laporan Markdown
│   ├── document.py             ← list/read/write template, write_document, write_skill
│   └── utility.py              ← list_routers, get_current_time
│
├── skills/                     ← Operator-defined Markdown knowledge files
│   ├── __init__.py             ← from skills.library import Skill, SkillLibrary
│   ├── library.py              ← SkillLibrary class + Skill dataclass + hot reload
│   ├── dhcp/
│   │   ├── dhcp-client-diagnostics.md   ← diagnosa client gagal dapat IP
│   │   ├── dhcp-pool-audit.md           ← audit utilisasi pool DHCP
│   │   └── utbk-session-monitoring.md   ← monitoring peserta UTBK
│   ├── routing/
│   │   ├── ospf-diagnostics.md          ← diagnosa OSPF neighbor/state
│   │   └── bgp-diagnostics.md           ← diagnosa BGP session/prefix
│   ├── monitoring/
│   │   ├── network-health-check.md      ← health check menyeluruh
│   │   ├── network-reachability.md      ← investigasi router unreachable
│   │   ├── network-traffic-analysis.md  ← analisis bandwidth & top talkers
│   │   └── network-status-report.md     ← ringkasan status jaringan
│   ├── security/
│   │   └── security-audit.md            ← audit postur keamanan router
│   ├── config/
│   │   └── config-backup.md             ← prosedur backup konfigurasi
│   └── documents/
│       └── document-writing.md          ← penulisan laporan ke file
│
├── agents/                     ← Multi-agent LangGraph
│   ├── __init__.py             ← from agents.graph import build_graph
│   ├── graph.py                ← StateGraph builder (START→supervisor→specialists→END)
│   ├── nodes.py                ← supervisor_node + 5 specialist nodes (loader-driven)
│   ├── tools.py                ← TOOL_MAP (flat, semua 34 tools)
│   ├── loader.py               ← AgentLoader + AgentDefinition dataclass
│   └── definitions/            ← Agent definition files (single source of truth)
│       ├── supervisor.md
│       ├── monitor_agent.md
│       ├── diagnose_agent.md
│       ├── config_agent.md
│       ├── security_agent.md
│       └── document_agent.md
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
  │                        config_backup (10 tools)     │
  │         │           ← interrupt() jika backup      │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [security_agent]  → tools: security, log,       │
  │                        config_read (6 tools)        │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  └──► [document_agent]  → tools: document, report,    │
                           template (20 tools)          │
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
    "next_agent": "monitor_agent | diagnose_agent | config_agent | security_agent | END",
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
    agent_log:          Annotated[list[AgentLogEntry], _append] # visible di TUI Agent Activity
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

### 5.3 Daftar Skill (12 skill aktif)

| Skill | Domain | Agent | Keterangan |
|-------|--------|-------|------------|
| `network-health-check` | monitoring | monitor | Health check menyeluruh semua router |
| `network-reachability` | monitoring | monitor | Investigasi router unreachable |
| `network-traffic-analysis` | monitoring | monitor | Analisis bandwidth & top talkers |
| `network-status-report` | monitoring | monitor | Ringkasan status jaringan |
| `dhcp-pool-audit` | dhcp | monitor | Audit utilisasi DHCP pool |
| `dhcp-client-diagnostics` | dhcp | diagnose | Diagnosa client gagal dapat IP |
| `utbk-session-monitoring` | dhcp | monitor | Monitoring peserta UTBK |
| `bgp-diagnostics` | routing | diagnose | Diagnosa BGP session/prefix |
| `ospf-diagnostics` | routing | diagnose | Diagnosa OSPF neighbor/state |
| `security-audit` | security | security | Audit postur keamanan router |
| `config-backup` | config | config | Prosedur backup konfigurasi |
| `document-writing` | documents | document | Penulisan laporan ke file |

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

| Agent | num_ctx | num_predict | context_window | timeout | Alasan |
|-------|---------|-------------|----------------|---------|--------|
| supervisor | 4096 | 256 | 6 | 60s | Output hanya JSON routing pendek |
| monitor_agent | 16384 | 2048 | 10 | 300s | Tool results dari 5+ router menumpuk |
| diagnose_agent | 8192 | 2048 | 10 | 300s | Logs + routing table + analisis RCA |
| config_agent | 8192 | 2048 | 10 | 180s | Config export per router |
| security_agent | 8192 | 2048 | 10 | 300s | Audit results + log parsing |
| document_agent | 24576 | 4096 | 20 | 600s | Seluruh history percakapan + template |

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

---

## 7. Human-in-the-Loop (Approval)

### 6.1 Flow

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

### 6.2 Risk Levels

| Level | Contoh Aksi | Default |
|---|---|---|
| `medium` | Config backup, export config | Require approval |
| `high` | (future) write operations | Require approval |
| `low` | Read-only queries | Auto-proceed |

---

## 8. Public API (agent.py → tui.py)

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

# Approval
def submit_approval(
    graph: CompiledStateGraph,
    config: RunnableConfig,
    decision: str           # "approved" | "rejected"
) -> None

# Info
def get_available_skills() -> list[dict]    # untuk TUI display
def get_agent_status() -> dict
```

---

## 9. TUI Interface Changes

### 8.1 Perubahan AIScreen

**Sebelum:**
- `AIScreen` berisi `_call_agent()`, `_call_ollama()`, LangGraph imports
- Import `agent` module langsung

**Sesudah:**
- `AIScreen` hanya memanggil `agent.stream_agent_response()`
- Handle event types yang di-yield
- Zero LLM logic di `tui.py`

### 8.2 Screen Baru: AgentActivityScreen (Menu item 7)

```
┌─ Agent Activity ──────────────────────────────────────────┐
│ [14:32:01] supervisor   → routing ke monitor_agent        │
│ [14:32:01] monitor      ⚙ tool_call: check_reachability   │
│                           └─ DTI (10.39.0.1): ✓ 1.2ms    │
│ [14:32:02] monitor      ⚙ tool_call: get_system_info      │
│                           └─ CPU 12%, RAM 45%, up 14d     │
│ [14:32:03] monitor      ← kembali ke supervisor           │
│ [14:32:04] supervisor   ✓ synthesis selesai               │
├───────────────────────────────────────────────────────────┤
│  ⚠ APPROVAL REQUIRED                                      │
│  Agent  : config_agent                                    │
│  Aksi   : Backup config FILKOM-CORE                       │
│  Risk   : MEDIUM                                          │
│  [Y] Approve    [N] Reject                                │
└───────────────────────────────────────────────────────────┘
```

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

⚠ `backup_router_config` memerlukan persetujuan operator (interrupt gate).

**Total: 34 tool atomic** | Source of truth: `agents/definitions/*.md` + `AgentLoader.validate()`

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
