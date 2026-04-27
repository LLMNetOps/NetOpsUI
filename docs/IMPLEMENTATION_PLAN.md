# Implementation Plan — NetOps AI

**Versi:** 1.0  
**Tanggal:** 2026-04-27  
**Branch Target:** `netops`  
**Base Branch:** `main`

---

## Ringkasan Phases

| Phase | Nama | Deskripsi | Status |
|---|---|---|---|
| 1 | Foundation | Branch setup + struktur direktori + base layer | ⬜ Belum |
| 2 | Tool Extraction | Pecah tools dari agent.py ke tools/*.py | ⬜ Belum |
| 3 | Skill System | SkillLibrary + format + skill contoh | ⬜ Belum |
| 4 | Multi-Agent Graph | Supervisor + 4 specialist agents | ⬜ Belum |
| 5 | New Tools | traffic.py + config_backup.py + skill-nya | ⬜ Belum |
| 6 | TUI Refactor | Pisahkan LLM logic + Agent Activity screen | ⬜ Belum |
| 7 | Human-in-the-Loop | Approval mechanism via interrupt() | ⬜ Belum |

**Legend:** ⬜ Belum · 🔄 In Progress · ✅ Selesai · 🔁 Review

---

## Phase 1: Foundation

**Goal:** Branch siap, struktur direktori ada, shared infrastructure terbentuk.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P1-01 | Buat branch `netops` dari `main` | — | `git checkout -b netops` berhasil |
| P1-02 | Buat struktur direktori | `tools/`, `skills/`, `agents/`, `backups/` | Semua direktori ada + `__init__.py` |
| P1-03 | Update `.gitignore` | `.gitignore` | `backups/` dikecualikan |
| P1-04 | Ekstrak `tools/base.py` | `tools/base.py` | `ssh_run_command`, `_load_config`, `_validate_router`, `_ssh_creds` ada + tested importable |
| P1-05 | Buat `requirements.txt` | `requirements.txt` | Semua dependency terdokumentasi dengan versi minimum |

### Definition of Done Phase 1
- `from tools.base import ssh_run_command, _load_config` berhasil
- `git status` di branch `netops`
- `requirements.txt` ada dan akurat

---

## Phase 2: Tool Extraction

**Goal:** Semua tools dari `agent.py` dipindah ke `tools/*.py` tanpa perubahan logic. `agent.py` lama masih tetap ada (belum dihapus) sebagai referensi.

### Tasks

| ID | Task | File Target | Source di agent.py |
|---|---|---|---|
| P2-01 | Ekstrak reachability tools | `tools/reachability.py` | `check_reachability` |
| P2-02 | Ekstrak system tools | `tools/system.py` | `get_system_info` |
| P2-03 | Ekstrak routing tools | `tools/routing.py` | `get_routing_full`, `get_router_config(routing-*)` |
| P2-04 | Ekstrak interface tools | `tools/interface.py` | bagian interface dari `collect_network_data` |
| P2-05 | Ekstrak DHCP tools | `tools/dhcp.py` | `get_dhcp_leases`, `get_all_leases_for_router`, `search_device`, `audit_all_routers` |
| P2-06 | Ekstrak log tools | `tools/log.py` | `get_router_log` |
| P2-07 | Ekstrak config_read tools | `tools/config_read.py` | `get_router_config`, `run_command`, `run_command_all_routers` |
| P2-08 | Ekstrak security tools | `tools/security.py` | bagian security dari `collect_network_data` |
| P2-09 | Ekstrak diagnostic tools | `tools/diagnostic.py` | `run_diagnostic`, `check_reachability` (ping dari router) |
| P2-10 | Ekstrak report tools | `tools/report.py` | `list_reports`, `read_report`, `read_report_section`, `get_report_toc` |
| P2-11 | Ekstrak utility tools | `tools/utility.py` | `list_routers`, `get_current_time` |
| P2-12 | Verifikasi semua tools importable | — | `from tools.dhcp import get_dhcp_leases` OK untuk semua tools |

### Catatan P2
- Jangan hapus `agent.py` lama dulu — pakai sebagai referensi sampai Phase 4 selesai
- Logic SSH tidak berubah — hanya reorganisasi file
- Setiap file `tools/*.py` mengimport dari `tools.base`

### Definition of Done Phase 2
- `tools/` berisi 10+ file
- Semua `@tool` decorator masih ada di masing-masing file
- Import dari `tools.*` berfungsi tanpa error
- `agent.py` lama masih ada (belum dihapus)

---

## Phase 3: Skill System

**Goal:** SkillLibrary berfungsi, format skill terdefinisi, minimal 8 skill contoh tersedia.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P3-01 | Implementasi `SkillLibrary` class | `agent.py` (bagian atas) | Load, search, hot reload berfungsi |
| P3-02 | Implementasi file watcher | `agent.py` | Perubahan file `.md` ter-detect dalam 2 detik |
| P3-03 | Buat skill: `dhcp-server-health` | `skills/dhcp/dhcp-server-health.md` | Format valid, triggers match |
| P3-04 | Buat skill: `diagnose-dhcp-client` | `skills/dhcp/diagnose-dhcp-client.md` | Format valid |
| P3-05 | Buat skill: `dhcp-pool-audit` | `skills/dhcp/dhcp-pool-audit.md` | Format valid |
| P3-06 | Buat skill: `bgp-diagnostics` | `skills/routing/bgp-diagnostics.md` | Format valid |
| P3-07 | Buat skill: `ospf-troubleshoot` | `skills/routing/ospf-troubleshoot.md` | Format valid |
| P3-08 | Buat skill: `network-health-check` | `skills/monitoring/network-health-check.md` | Format valid |
| P3-09 | Buat skill: `security-audit` | `skills/security/security-audit.md` | Format valid |
| P3-10 | Buat skill: `config-review-checklist` | `skills/config/config-review-checklist.md` | Format valid |

### Definition of Done Phase 3
- `SkillLibrary().find_relevant("client tidak dapat IP")` return skill DHCP
- Hot reload: edit `.md` → perubahan aktif tanpa restart
- `/skill <nama>` explicit invoke berfungsi (di-test manual)
- Minimal 8 skill tersedia

---

## Phase 4: Multi-Agent Graph

**Goal:** LangGraph Supervisor + 4 specialist agents berfungsi, routing akurat, streaming ke TUI berjalan.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P4-01 | Definisi `NetworkOpsState` | `agent.py` | TypedDict valid, semua field ada |
| P4-02 | Implementasi `agents/supervisor.py` | `agents/supervisor.py` | Routing ke 4 specialist + END berfungsi |
| P4-03 | Implementasi `agents/monitor_agent.py` | `agents/monitor_agent.py` | Akses 7 tool, skill injection berfungsi |
| P4-04 | Implementasi `agents/diagnose_agent.py` | `agents/diagnose_agent.py` | Akses 5 tool, multi-step diagnosis berfungsi |
| P4-05 | Implementasi `agents/config_agent.py` | `agents/config_agent.py` | Akses 2 tool, interrupt() placeholder |
| P4-06 | Implementasi `agents/security_agent.py` | `agents/security_agent.py` | Akses 3 tool |
| P4-07 | Bangun StateGraph di `agent.py` | `agent.py` | Graph compile tanpa error |
| P4-08 | Implementasi `create_agent()` public API | `agent.py` | Return (graph, config) yang valid |
| P4-09 | Implementasi `stream_agent_response()` | `agent.py` | Yield event tuples sesuai spec |
| P4-10 | Hapus / archive `agent.py` lama | `agent_legacy.py` | Rename jadi `agent_legacy.py` untuk referensi |
| P4-11 | Update `tui.py` import | `tui.py` | Import dari `agent.py` baru, tidak ada import error |

### Definition of Done Phase 4
- Query "cek status jaringan" → monitor_agent teraktivasi
- Query "diagnosa koneksi DTI" → diagnose_agent teraktivasi
- Streaming event sampai ke TUI
- Semua test manual 4 specialist berjalan
- `agent_legacy.py` ada sebagai backup

---

## Phase 5: New Tools

**Goal:** Tools traffic stats dan config backup tersedia dan terhubung ke agent.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P5-01 | Implementasi `get_interface_traffic` | `tools/traffic.py` | Return TX/RX rate realtime |
| P5-02 | Implementasi `get_traffic_summary` | `tools/traffic.py` | Semua interface satu router |
| P5-03 | Implementasi `get_top_talkers` | `tools/traffic.py` | Menggunakan MikroTik `/tool/torch` |
| P5-04 | Implementasi `get_queue_stats` | `tools/traffic.py` | Queue usage dan drop stats |
| P5-05 | Implementasi `backup_router_config` | `tools/config_backup.py` | Export + simpan ke `backups/` dengan timestamp |
| P5-06 | Implementasi `list_backups` | `tools/config_backup.py` | Daftar backup per router |
| P5-07 | Implementasi `diff_config` | `tools/config_backup.py` | Diff dua file backup |
| P5-08 | Implementasi `get_latest_backup` | `tools/config_backup.py` | Baca backup terbaru |
| P5-09 | Tambah traffic tools ke `monitor_agent` | `agents/monitor_agent.py` | Tools terdaftar, bisa dipanggil |
| P5-10 | Tambah config_backup tools ke `config_agent` | `agents/config_agent.py` | Tools terdaftar |
| P5-11 | Buat skill: `traffic-analysis` | `skills/monitoring/traffic-analysis.md` | Format valid |
| P5-12 | Buat skill: `config-backup-procedure` | `skills/config/config-backup-procedure.md` | approval_required: true |

### Definition of Done Phase 5
- `backup_router_config("DTI")` menyimpan file ke `backups/DTI_YYYYMMDD_HHMMSS.rsc`
- `diff_config("DTI", file1, file2)` output readable diff
- `get_interface_traffic("DTI", "ether1")` return TX/RX rates

---

## Phase 6: TUI Refactor

**Goal:** Zero LLM logic di `tui.py`. Agent Activity screen berfungsi.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P6-01 | Hapus `_call_ollama()` dari `AIScreen` | `tui.py` | Tidak ada Ollama import di tui.py |
| P6-02 | Hapus `_call_agent()` dari `AIScreen` | `tui.py` | Tidak ada LangGraph import di tui.py |
| P6-03 | Refactor `AIScreen._send_message()` | `tui.py` | Hanya panggil `agent.stream_agent_response()` |
| P6-04 | Handle semua event types di `AIScreen.draw()` | `tui.py` | routing, tool_call, tool_result, ai render dengan benar |
| P6-05 | Implementasi `AgentActivityScreen` | `tui.py` | Screen baru menu item 7 |
| P6-06 | Agent Activity: render agent_log | `tui.py` | Log events tampil real-time |
| P6-07 | Update MENU constant | `tui.py` | Menu item 7 "Activity" muncul |
| P6-08 | Backward compatibility: fallback jika LangGraph tidak ada | `tui.py` | Pesan informatif, tidak crash |

### Definition of Done Phase 6
- `grep -n "import langchain\|import langgraph\|ChatOllama\|requests.post" tui.py` → 0 results
- Agent Activity screen tampil dan update real-time
- TUI berfungsi normal untuk semua 7 menu items

---

## Phase 7: Human-in-the-Loop

**Goal:** Config backup memerlukan approval operator, flow berjalan end-to-end.

### Tasks

| ID | Task | File Target | DoD |
|---|---|---|---|
| P7-01 | Tambah `interrupt()` di `config_agent` sebelum backup | `agents/config_agent.py` | Graph pause saat backup |
| P7-02 | Implementasi `submit_approval()` public API | `agent.py` | `Command(resume=decision)` dikirim ke graph |
| P7-03 | TUI: handle event `approval_required` | `tui.py` | Modal approval muncul di AIScreen atau Activity screen |
| P7-04 | TUI: kirim keputusan operator ke agent | `tui.py` | `agent.submit_approval(graph, config, "approved")` |
| P7-05 | Log approval decisions ke `agent_log` | `agent.py` | Semua keputusan tercatat dengan timestamp |
| P7-06 | Test end-to-end: request backup → approval → eksekusi | — | Flow lengkap berfungsi |

### Definition of Done Phase 7
- Request backup → TUI modal muncul → Y → backup file tersimpan
- Request backup → TUI modal muncul → N → agent respond "dibatalkan"
- Log approval decision muncul di Agent Activity screen

---

## Tracking Status

### Progress Overview

```
Phase 1: Foundation          [░░░░░░░░░░] 0%
Phase 2: Tool Extraction     [░░░░░░░░░░] 0%
Phase 3: Skill System        [░░░░░░░░░░] 0%
Phase 4: Multi-Agent Graph   [░░░░░░░░░░] 0%
Phase 5: New Tools           [░░░░░░░░░░] 0%
Phase 6: TUI Refactor        [░░░░░░░░░░] 0%
Phase 7: Human-in-the-Loop   [░░░░░░░░░░] 0%
```

### Blockers & Notes

*(Isi saat ada blocker atau keputusan penting yang perlu dicatat)*

---

## Dependency Graph antar Phase

```
P1 (Foundation)
  └── P2 (Tool Extraction)
        ├── P3 (Skill System) ─────────┐
        └── P4 (Multi-Agent Graph) ◄───┘
              ├── P5 (New Tools)
              ├── P6 (TUI Refactor)
              └── P7 (Human-in-the-Loop)
```

P5, P6, P7 dapat dikerjakan paralel setelah P4 selesai.
