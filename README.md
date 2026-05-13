# NetOps AI — Campus Network Operations Platform

Platform operasional jaringan kampus berbasis multi-agent AI. Dibangun di atas project monitoring DHCP UTBK 2026 (`main`), branch ini (`netops`) memperluas cakupan ke operasional jaringan kampus secara menyeluruh dengan arsitektur LangGraph multi-agent, skill system berbasis Markdown, dan human-in-the-loop approval.

## Fitur Utama

- **Multi-agent LangGraph**: Supervisor + 5 specialist agents (monitor/eko, diagnose/agus, config/joko, security/satria, document/budi)
- **Skill System**: Operator mendefinisikan prosedur kerja dalam Markdown — tanpa coding Python; template sistem untuk panduan format laporan
- **32 tools atomic**: SSH ke MikroTik RouterOS v6/v7, mencakup traffic stats, config backup, diagnostik, security audit, document writing
- **Hot reload**: Tambah atau edit skill dan template langsung aktif tanpa restart sistem
- **Human-in-the-loop**: Operasi berisiko (config backup) memerlukan persetujuan operator Y/N
- **TUI 7 layar**: Termasuk layar Agent Activity untuk monitoring komunikasi antar agent secara real-time
- **Zero LLM logic di tui.py**: Semua orchestration di `agent.py`, TUI hanya consume public API

## Arsitektur

```
┌─────────────────────────────────────────────────────────────┐
│                    TUI (tui.py, 7 layar)                    │
│   AI Chat  ──►  agent.py public API  ◄──  Agent Activity   │
└─────────────────────────┬───────────────────────────────────┘
                           │ stream_agent_response()
┌─────────────────────────▼───────────────────────────────────┐
│                  agent.py (Orchestration)                   │
│                                                             │
│   SkillLibrary (hot reload)    LangGraph StateGraph         │
│   skills/**/*.md          ───► supervisor → specialists     │
└──────────────────────────────────────────┬──────────────────┘
                                           │ tools SSH
┌──────────────────────────────────────────▼──────────────────┐
│                     tools/*.py (28 tools)                   │
│         SSH Commands → MikroTik Routers (ROS v6/v7)        │
└─────────────────────────────────────────────────────────────┘
```

### Struktur File

```
llmnetops/
├── agent.py              ← Public API + NetworkOpsState + SkillLibrary singleton
├── tui.py                ← UI only (zero LLM logic)
├── generate_reports.py   ← Standalone DHCP report generator
│
├── agents/
│   ├── graph.py          ← StateGraph builder
│   ├── nodes.py          ← supervisor_node + 5 specialist nodes + config_node; AGENT_ALIAS
│   └── tools.py          ← Tool registries per agent domain
│
├── skills/
│   ├── library.py        ← SkillLibrary class + hot reload
│   ├── dhcp/             ← diagnose-dhcp-client, dhcp-pool-audit, utbk-client-monitor
│   ├── routing/          ← ospf-neighbor-down, bgp-diagnostics
│   ├── monitoring/       ← network-health-check, router-unreachable
│   ├── security/         ← security-audit
│   ├── config/           ← config-backup-procedure
│   └── documents/        ← write-report; templates/security-assessment.md
│
├── tools/                ← 32 atomic SSH tools
│   ├── base.py           ← SSH helper, config loader
│   ├── traffic.py        ← TX/RX rates, top talkers, queue stats
│   ├── config_backup.py  ← Export, diff, list backups
│   ├── document.py       ← list_templates, read_template, write_document, create_template
│   └── ...               ← reachability, system, routing, dhcp, log, dll
│
├── legacy/               ← Script main-branch (DHCP collector, report generator, scheduler)
│   ├── mikrotik_agent.py ← SSH DHCP collector (dipakai CollectScreen via subprocess)
│   ├── generate_reports.py ← DHCP report generator (dipakai LaporanScreen via subprocess)
│   ├── schedule_utbk.sh  ← Scheduler UTBK 2026
│   └── test_regex.py     ← One-off test script
│
├── backups/              ← Config backups (gitignored)
├── docs/                 ← PRD, Architecture, Implementation Plan, Skill Authoring Guide
└── laporan/              ← Generated reports (gitignored)
```

## Prerequisites

- Python 3.11+
- Linux terminal (curses TUI)
- Akses SSH ke router MikroTik
- [Ollama](https://ollama.ai) dengan model `gemma4:e4b` (atau model lain via `OLLAMA_MODEL`)

## Setup

```bash
git checkout netops
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit OLLAMA_BASE_URL dan OLLAMA_MODEL di .env
# Buat config.yaml (lihat seksi Konfigurasi)
```

## Konfigurasi

### `.env`

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=gemma4:e4b
```

### `config.yaml` (tidak di-commit)

```yaml
ssh:
  username: netadmin
  password: "REDACTED"
  timeout: 15
  port: 22

routers:
  - name: DTI
    host: 10.39.0.1
    ros_version: 7
    dhcp_servers:
      - dhcp-lab-tik
```

## Cara Penggunaan

```bash
source .venv/bin/activate
python tui.py
```

### Layar TUI

| Nomor | Layar | Fungsi |
|---|---|---|
| 1 | Dashboard | Status ringkas lease DHCP lintas router |
| 2 | Jadwal | Informasi jadwal pengumpulan data |
| 3 | Collect | Trigger koleksi data via `mikrotik_agent.py` |
| 4 | Laporan | Baca file markdown di `laporan/` |
| 5 | Log | Catatan aktivitas/eksekusi |
| 6 | AI Chat | Interaksi multi-agent dengan approval modal |
| 7 | Activity | Log routing, tool calls, tool results real-time |

### AI Chat — Contoh Query

```
cek status jaringan kampus
kenapa Lab5 tidak dapat IP?
audit keamanan router FILKOM-CORE
backup konfigurasi DTI
cek traffic ether1 di GKB
simpan laporan health check ke file
tulis laporan keamanan jaringan DTI
```

### Invoke Skill Eksplisit

```
/skill diagnose-dhcp-client
/skill ospf-neighbor-down
/skill security-audit
```

## Tools AI Agent (28 tool)

### Monitoring & Status

| Tool | Fungsi |
|---|---|
| `list_routers` | Daftar router dan DHCP server |
| `check_reachability` | Ping ke router |
| `get_system_info` | CPU, RAM, uptime |
| `get_interface_stats` | Error dan drop per interface |
| `get_interface_traffic` | TX/RX rate realtime |
| `get_traffic_summary` | Ringkasan traffic semua interface |
| `get_top_talkers` | IP dengan traffic tertinggi |
| `get_queue_stats` | Statistik queue dan drop |
| `get_traffic_all` | Traffic stats semua router paralel |
| `get_current_time` | Waktu lokal WIB (UTC+7) |

### DHCP

| Tool | Fungsi |
|---|---|
| `get_dhcp_leases` | Lease dari satu DHCP server |
| `get_router_leases` | Semua lease di satu router |
| `audit_dhcp` | Audit DHCP semua router |
| `search_device` | Cari perangkat by IP atau MAC |

### Routing & Config

| Tool | Fungsi |
|---|---|
| `get_routing_full` | Route table + OSPF + BGP |
| `get_router_config` | Konfigurasi router (berbagai section) |
| `run_command` | Command read-only di satu router |
| `run_command_all` | Command yang sama di semua router paralel |

### Config Backup

| Tool | Fungsi |
|---|---|
| `backup_router_config` | `/export` → `backups/<router>/<ts>.rsc` (**butuh approval**) |
| `list_backups` | Daftar backup tersimpan |
| `diff_config` | Diff dua versi config |

### Log, Diagnostik, Security, Report

| Tool | Fungsi |
|---|---|
| `get_router_log` | Log router (bisa filter per topic) |
| `run_diagnostic` | Ping atau traceroute dari router |
| `audit_security` | Audit user accounts, NTP, firewall |
| `list_reports` | Daftar file laporan |
| `get_report` | Baca laporan Markdown |
| `get_report_section` | Baca section tertentu dari laporan |
| `get_report_toc` | Daftar isi laporan |

### Document

| Tool | Fungsi |
|---|---|
| `list_templates` | Daftar template laporan di `skills/documents/templates/` |
| `read_template` | Baca isi file template |
| `write_document` | Tulis dokumen laporan ke `laporan/` (konvensi nama otomatis) |
| `create_template` | Buat atau perbarui template — langsung aktif tanpa restart |

## Skill System

Skill adalah file Markdown di `skills/` yang mendefinisikan prosedur kerja untuk agent. Operator jaringan bisa menulis skill baru tanpa menyentuh kode Python.

```bash
# Buat skill baru
vim skills/routing/bgp-flap.md
# Langsung aktif — tidak perlu restart
```

Format minimal:

```markdown
---
name: nama-skill
domain: routing
triggers:
  - kata kunci yang memicu skill ini
tools:
  - get_routing_full
  - get_router_log
approval_required: false
enabled: true
---

## Konteks
Kapan skill ini digunakan.

## Prosedur
Langkah-langkah yang harus diikuti agent.
```

Lihat [docs/SKILL_AUTHORING_GUIDE.md](docs/SKILL_AUTHORING_GUIDE.md) untuk panduan lengkap.

## Human-in-the-Loop

Operasi `backup_router_config` memerlukan persetujuan operator sebelum dieksekusi:

```
┌─ APPROVAL REQUIRED ─────────────────────────┐
│ Agent  : config_agent                       │
│ Aksi   : Backup config router 'DTI'        │
│ Risk   : MEDIUM                             │
│ [Y] Approve    [N] Reject                   │
└─────────────────────────────────────────────┘
```

## Requirements

```
langchain-ollama>=0.3.0
langchain-core>=0.3.0
langgraph>=1.1.0
pyyaml>=6.0
paramiko>=3.0
watchfiles>=0.21
tabulate>=0.9
```

## Security Notes

- Jangan commit `config.yaml`, `.env`, isi `output/`, `laporan/`, dan `backups/`.
- Gunakan kredensial SSH minimum privilege khusus monitoring (read-only).
- `run_command` dibatasi blocklist kata destruktif.
- File backup di `backups/` dikecualikan dari git via `.gitignore`.
- Credentials (SSH password) tidak pernah muncul di log atau output agent.

## Dokumentasi

| Dokumen | Isi |
|---|---|
| [docs/PRD.md](docs/PRD.md) | Requirements dan success metrics |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Desain sistem, state, API |
| [docs/IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Rencana implementasi 8 phase |
| [docs/SKILL_AUTHORING_GUIDE.md](docs/SKILL_AUTHORING_GUIDE.md) | Panduan menulis skill baru |
| [docs/LANGGRAPH_FUNDAMENTALS.md](docs/LANGGRAPH_FUNDAMENTALS.md) | Node, edge, dan state di LangGraph |
| [docs/AGENT_COMMUNICATION_PATTERNS.md](docs/AGENT_COMMUNICATION_PATTERNS.md) | Pola komunikasi antar agent |
| [docs/PERSISTENCE_AND_MEMORY.md](docs/PERSISTENCE_AND_MEMORY.md) | Checkpointing dan memory di LangGraph |

## Branch

| Branch | Deskripsi |
|---|---|
| `main` | DHCP lease monitoring UTBK 2026 (original) |
| `netops` | Campus network operations platform (branch ini) |
