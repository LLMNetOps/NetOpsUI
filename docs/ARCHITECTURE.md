# Architecture Document — NetOps AI

**Versi:** 1.0  
**Tanggal:** 2026-04-27  
**Status:** Draft

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
│   SkillLibrary          LangGraph StateGraph                │
│   (hot reload)    ───►  Supervisor ──► Specialist           │
│   skills/*.md           Agent          Agents               │
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
├── agent.py                    ← Supervisor graph + SkillLibrary + public API
├── tui.py                      ← UI only (zero LLM logic)
├── generate_reports.py         ← Standalone DHCP report generator (tidak diubah)
│
├── tools/                      ← Atomic SSH operations
│   ├── base.py                 ← SSH helper, config loader, _validate_router
│   ├── reachability.py         ← ICMP ping check
│   ├── system.py               ← CPU, RAM, uptime
│   ├── routing.py              ← Route table, OSPF, BGP
│   ├── interface.py            ← Interface stats, errors
│   ├── traffic.py              ← TX/RX rates, top talkers, queue stats [NEW]
│   ├── dhcp.py                 ← DHCP lease queries, search device
│   ├── log.py                  ← Router log pull
│   ├── config_read.py          ← Config sections (read-only)
│   ├── config_backup.py        ← Export + save, diff, list backups [NEW]
│   ├── security.py             ← User audit, firewall, NTP check
│   ├── diagnostic.py           ← Ping/traceroute dari router
│   └── report.py               ← List/read laporan Markdown
│
├── skills/                     ← Operator-defined Markdown knowledge files
│   ├── dhcp/
│   ├── routing/
│   ├── monitoring/
│   ├── security/
│   └── config/
│
├── agents/                     ← Specialist agent definitions
│   ├── __init__.py
│   ├── supervisor.py
│   ├── monitor_agent.py
│   ├── diagnose_agent.py
│   ├── config_agent.py
│   └── security_agent.py
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
  │                        log, report                  │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [diagnose_agent]  → tools: reachability,        │
  │                        diagnostic, log, dhcp,       │
  │                        routing                      │
  │         │                                           │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  ├──► [config_agent]    → tools: config_read,         │
  │                        config_backup                │
  │         │           ← interrupt() jika backup      │
  │         └─────────────────────────────────────────►┤
  │                                                     │
  └──► [security_agent]  → tools: security, log,       │
                           config_read                  │
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
# Supervisor routing decision
{
    "next_agent": "monitor_agent | diagnose_agent | config_agent | security_agent | END",
    "relevant_skills": ["skill-name-1", "skill-name-2"],
    "requires_chain": bool
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

class NetworkOpsState(TypedDict):
    messages:           Annotated[list, add_messages]
    next_agent:         str                    # supervisor routing decision
    active_agent:       str                    # currently executing agent
    injected_skills:    list[str]              # skill names yang sedang aktif
    agent_log:          list[AgentLogEntry]    # visible di TUI Agent Activity
    pending_approval:   ApprovalRequest | None # blocked waiting for operator
    approval_decision:  str | None             # "approved" | "rejected"
```

---

## 5. Skill System

### 5.1 Skill File Format

Setiap skill adalah file `.md` dengan struktur:

```markdown
---
name: diagnose-dhcp-client
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

### 5.2 SkillLibrary

```python
class SkillLibrary:
    skills: dict[str, Skill]          # name → Skill object
    
    def load_all() -> None            # scan skills/**/*.md
    def start_watcher() -> None       # watchdog untuk hot reload
    def find_relevant(
        query: str,
        domain: str = None
    ) -> list[Skill]                  # keyword matching dari triggers
    def get_by_name(name: str) -> Skill | None
    def inject_context(
        skills: list[Skill]
    ) -> str                          # gabungkan body Markdown untuk injection
```

### 5.3 Hot Reload Mechanism

```
Operator: edit/tambah/hapus skills/**/*.md
                │
     watchdog (watchfiles library)
                │
     SkillLibrary._reload(changed_file)
                │
     skill tersedia di request berikutnya
```

### 5.4 Skill Selection

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

## 6. Human-in-the-Loop (Approval)

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

## 7. Public API (agent.py → tui.py)

```python
# Inisialisasi
def create_agent(thread_id: str) -> tuple[StateGraph, RunnableConfig]
def reset_agent(thread_id: str) -> tuple[StateGraph, RunnableConfig]

# Eksekusi
def stream_agent_response(
    graph: StateGraph,
    config: RunnableConfig,
    message: str
) -> Iterator[tuple[str, str]]
# Yields: (event_type, content)
# event_type: "routing" | "tool_call" | "tool_result" |
#             "agent_thinking" | "approval_required" | "ai" | "error"

# Approval
def submit_approval(
    graph: StateGraph,
    config: RunnableConfig,
    decision: str           # "approved" | "rejected"
) -> None

# Info
def get_available_skills() -> list[dict]    # untuk TUI display
def get_agent_status() -> dict
```

---

## 8. TUI Interface Changes

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

## 9. Tools per Agent (Tool Access Matrix)

| Tool | monitor | diagnose | config | security |
|---|:---:|:---:|:---:|:---:|
| reachability | ✓ | ✓ | | |
| system | ✓ | | | |
| routing | ✓ | ✓ | | |
| interface | ✓ | | | |
| traffic | ✓ | | | |
| dhcp | ✓ | ✓ | | |
| log | ✓ | ✓ | | ✓ |
| config_read | ✓ | | ✓ | ✓ |
| config_backup | | | ✓ | |
| security | | | | ✓ |
| diagnostic | | ✓ | | |
| report | ✓ | | | |

---

## 10. Dependencies Baru

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
