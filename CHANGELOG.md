# Changelog

Semua perubahan penting pada proyek ini akan didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan proyek ini menggunakan [Semantic Versioning](https://semver.org/lang/id/).

## [v1.3.0] - 2026-05-09 (branch: refactor_agent_skill_tool)

### Added
- **Write operations** (`tools/config_write.py`): tool `run_command_write` untuk eksekusi perintah
  destruktif di router — selalu memerlukan approval operator via interrupt gate; hard-blocked untuk
  `format`, `factory-reset`, `reset-configuration`
- **`agents/metrics.py`**: `TokenMetricsCallback` — catat stats Ollama (prompt/eval tokens,
  duration) ke `data/metrics.jsonl` sebagai JSONL append-only; `get_token_metrics()` di public API
- **6 skill baru**:
  - `skills/config/config-change.md` — prosedur ubah konfigurasi spesifik dengan backup-first
  - `skills/dhcp/static-lease-management.md` — kelola DHCP static lease
  - `skills/interface/link-diagnostics.md` — diagnosa interface error dan flapping
  - `skills/maintenance/router-maintenance.md` — upgrade dan reboot terjadwal
  - `skills/routing/static-route-management.md` — tambah/hapus static route
  - `skills/security/brute-force-response.md` — blokir IP penyerang (response dari deteksi)
  - `skills/security/firewall-management.md` — kelola firewall rules MikroTik
- **2 template laporan baru**:
  - `skills/documents/templates/network-status.md`
  - `skills/documents/templates/routing-bgp-ospf.md`
- **Routing tools baru** (`tools/routing.py`): `get_bgp_sessions`, `get_ospf_neighbors`,
  `get_interface_stats` — SSH ke router, parse output, format sebagai tabel ringkas
- **Sistem evaluasi** (`tests/`):
  - `tests/eval.py` — evaluator script: patch TOOL_MAP dengan mock, jalankan agent, verifikasi
    expected_agents/expected_tools/acceptance_criteria; support `--lab` untuk koneksi nyata
  - `tests/mocks/fixtures.py` — mock data realistis kampus UB per tool (17 router)
  - `tests/scenarios/*.yaml` — 5 skenario evaluasi: `bgp-ospf-report`, `health-check`,
    `brute-force-detect`, `dhcp-exhaustion`, `interface-flapping`
- **`docs/teaching-log.md`** — log institutional memory: apa yang gagal, root cause, perubahan,
  hasil; 7 entri dari sesi pengembangan (gemma4 num_predict bug, max_iters, forced summary, dll)
- **`tui.py`** headless + debug mode: `--headless "pesan"` untuk non-interactive, `--debug`
  untuk tampilkan raw supervisor response dan token metadata

### Changed
- **`supervisor.md`**: `chat_prompt` dibaca dari definition file (bukan hardcode di nodes.py);
  tabel routing diperbarui untuk mencakup skill write operations
- **`config_agent.md`**: ditambah 7 skill write-capable + tabel quick-reference skill → tools
- **`document_agent.md`**: skill `skill-authoring` diperbarui dengan `fetch_url` untuk referensi URL
- **`skills/documents/skill-authoring.md`**: tambah section **Prinsip untuk Model Kecil**
  (tabel what-works vs what-doesn't, 5 aturan utama) dan **Checklist Review Sebelum Commit** (9 item)
- **`skills/routing/bgp-diagnostics.md`** dan **`ospf-diagnostics.md`**: diperbarui signifikan
  dengan contoh output tool dan interpretasi eksplisit
- **`skills/security/security-audit.md`**: diperbarui dengan prosedur brute force detection
- **`tools/base.py`**: refactor SSH helpers; tambah `get_unique_router_entries()`
- **`tui.py`**: refactor UI layer, pemisahan concern TUI vs agent logic

### Fixed
- `config_agent` system prompt sekarang punya skill quick-reference table — agent tidak bingung
  saat supervisor menginjeksi skill tertentu dari 7 pilihan

---

## [v1.2.0] - 2026-05-08 (branch: refactor_agent_skill_tool)

### Added
- **Agent Definition System** (Ultralight Orchestration): 6 file `agents/definitions/*.md` sebagai single source of truth untuk tiap agent — tools, skills, LLM params, dan system prompt semuanya ada di satu file
- **`agents/loader.py`** (`AgentLoader` + `AgentDefinition`): memuat dan memvalidasi definition files saat startup; mengecek `agent.tools ⊆ TOOL_MAP`, `agent.skills ⊆ SkillLibrary`, dan `skill.tools ⊆ agent.tools`
- **Per-agent LLM parameters** di frontmatter definition: `num_ctx`, `num_predict`, `context_window`, `timeout` — supervisor pakai 4096/256/6/60, document_agent pakai 24576/4096/20/600
- **Skill baru**: `skills/monitoring/network-traffic-analysis.md` (analisis bandwidth dan top talkers)
- **`document_agent`** ditambahkan ke graph topology dan tool matrix

### Changed
- **`agents/tools.py`**: hapus per-agent tool lists (`MONITOR_TOOLS`, `DIAGNOSE_TOOLS`, dll); ganti dengan `TOOL_MAP` flat dari semua 34 tools
- **`agents/nodes.py`**: semua hardcoded data (tool lists, role descriptions, alias map, LLM params) dihapus dan dibaca dari `AgentLoader`; `_make_llm()` menerima `num_ctx`, `num_predict`, `timeout` sebagai parameter
- **7 skill direname** ke konvensi `[domain]-[capability-noun]`:
  - `config-backup-procedure` → `config-backup`
  - `diagnose-dhcp-client` → `dhcp-client-diagnostics`
  - `utbk-client-monitor` → `utbk-session-monitoring`
  - `write-report` → `document-writing`
  - `router-unreachable` → `network-reachability`
  - `network-report` → `network-status-report`
  - `ospf-neighbor-down` → `ospf-diagnostics`
- **4 skill tool lists diperbarui** untuk menutup gap coverage: `network-health-check` (+`get_interface_stats`), `config-backup` (+`backup_router_config`), `document-writing` (+`write_skill`, `get_report_section`, `get_report_toc`), `monitor_agent` (+`network-traffic-analysis`)

### Fixed
- 3 tool mismatch di `agents/tools.py`: `search_device` dan `run_command` ditambahkan ke monitor; `get_router_config` ditambahkan ke diagnose
- Supervisor body tidak lagi hardcode daftar agent (kini dinamis dari `AgentLoader`)
- `defn.model` kini benar-benar digunakan di setiap node (sebelumnya semua pakai `OLLAMA_MODEL` env var)

### Documentation
- `docs/ARCHITECTURE.md` v2.0: tambah Section 6 (Agent Definition System), perbarui directory structure, tool matrix, dan skill listing
- `docs/SKILL_AUTHORING_GUIDE.md` v1.1: tambah konvensi penamaan skill, perbarui contoh dan file listing
- `docs/RESEARCH_SKILL_TOOL_ARCHITECTURE.md`: riset referensi framework (Evonic, OpenAI Agents SDK, GStack, Ultralight Orchestration, GetStream)

---

## [v1.1.0] - 2026-05-04 (branch: netops)

### Added
- **Document Agent** ("budi"): specialist ke-5 untuk menulis laporan ke file, mengelola template, dan mengkurasi hasil agent lain menjadi dokumen terstruktur
- **4 document tools** di `tools/document.py`: `list_templates`, `read_template`, `write_document`, `create_template`
- **Skill `write-report`** di `skills/documents/`: prosedur lengkap menulis laporan ke `laporan/` menggunakan template
- **Template `security-assessment.md`**: blank template penilaian keamanan web dengan `{{PLACEHOLDER}}` di `skills/documents/templates/`
- **`AGENT_ALIAS`** dict: display names untuk semua agent (bambang/eko/agus/joko/satria/budi); log agent kini menampilkan nama alias
- **`context_window` parameter** di `_make_specialist_node()`: document_agent pakai window 20 messages (specialist lain default 10)
- Skip subdirektori `templates/` di `SkillLibrary._load_all()` — file template tidak dimuat sebagai skill
- Dokumentasi LangGraph: `docs/LANGGRAPH_FUNDAMENTALS.md`, `docs/AGENT_COMMUNICATION_PATTERNS.md`, `docs/PERSISTENCE_AND_MEMORY.md`

### Changed
- Total tool atomic: 28 → 32
- Total skill contoh: 9 → 10
- Supervisor prompt diperbarui: tambah `document_agent` ke routing options dan penjelasan alur multi-domain ke dokumentasi

---

## [v1.0.0] - 2026-04-27 (branch: netops)

Rilis major pertama NetOps AI — platform operasional jaringan kampus berbasis multi-agent LangGraph. Transformasi dari tool monitoring DHCP monolitik menjadi sistem multi-agent yang dapat dikonfigurasi operator.

### Added
- **Multi-agent LangGraph**: Supervisor + 4 specialist agents (monitor, diagnose, config, security) via `agents/nodes.py` dan `agents/graph.py`
- **Skill System**: `SkillLibrary` di `skills/library.py` dengan hot reload via `watchfiles`; 9 skill contoh tersedia di `skills/`
- **28 tool atomic** di `tools/` (dipecah dari `agent.py` monolitik):
  - `tools/traffic.py`: `get_interface_traffic`, `get_traffic_summary`, `get_top_talkers`, `get_queue_stats`, `get_traffic_all`
  - `tools/config_backup.py`: `backup_router_config`, `list_backups`, `diff_config`
  - `tools/base.py`: SSH helper terpusat untuk semua tool
- **Human-in-the-loop approval**: `interrupt()` gate di `config_node` untuk `backup_router_config`; TUI menampilkan approval modal Y/N
- **`AgentActivityScreen`** (menu 7): monitoring komunikasi antar agent real-time (routing, tool calls, tool results, approval)
- **Public API** di `agent.py`: `create_agent()`, `stream_agent_response()`, `submit_approval()`, `get_available_skills()`, `get_agent_status()`
- Dokumentasi lengkap: `docs/PRD.md`, `docs/ARCHITECTURE.md`, `docs/IMPLEMENTATION_PLAN.md`, `docs/SKILL_AUTHORING_GUIDE.md`

### Changed
- `agent.py` ditulis ulang dari ~2600 baris monolitik menjadi 178 baris public API + orchestration murni
- `tui.py` direfactor: semua LLM/agent logic dipindah ke `agent.py`; tui.py menjadi zero LLM (1592 baris, -229 dari sebelumnya)
- Title TUI: "NetOps AI — Campus Network Operations"
- Default model: `qwen3:32b` (sebelumnya `qwen3.6:35b-a3b-q8_0`)
- Nama tool distandarisasi: `read_report` → `get_report`, `audit_all_routers` → `audit_dhcp`, `get_all_leases_for_router` → `get_router_leases`, `run_command_all_routers` → `run_command_all`

### Fixed
- StructuredTool unhashable: deduplication tool map menggunakan `dict.setdefault()` bukan `set()`
- LangGraph routing function: `route_from_supervisor(state: dict)` — type hint `dict` bukan forward ref `"NetworkOpsState"` untuk menghindari `NameError` saat `get_type_hints()` dipanggil

### Security
- Credentials SSH tidak pernah masuk ke agent log atau output
- `backup_router_config` memerlukan persetujuan eksplisit operator sebelum dieksekusi
- File backup di `backups/` dikecualikan dari git

---

## [v0.8.0] - 2026-04-25

### Added
- Menambahkan tool `run_diagnostic()` untuk `traceroute`, `ping`, dan `flood-ping` dengan timeout 60 detik.
- Menambahkan adaptasi otomatis command untuk RouterOS v6 dan v7 pada jalur diagnostik.

### Changed
- Memperbarui system prompt dengan panduan penggunaan `run_diagnostic` dibanding `run_command` untuk kasus troubleshooting jaringan.

### Fixed
- Memperbaiki masalah timeout traceroute (sebelumnya 15 detik tidak cukup pada beberapa lintasan jaringan).

### Security
- Tidak ada perubahan security spesifik pada versi ini.

## [v0.7.0] - 2026-04-24

### Added
- Menambahkan tool `run_command()` untuk eksekusi command MikroTik read-only secara fleksibel.
- Menambahkan tool `run_command_all_routers()` untuk eksekusi command paralel ke semua router.

### Changed
- Menaikkan `recursion_limit` agent dari 15 menjadi 50 untuk mendukung audit paralel 17 router.
- Memperbarui instruksi agent agar menggunakan konteks `routing-static` alih-alih `ip-route` pada analisis tertentu.

### Fixed
- Tidak ada perbaikan bug mayor yang didokumentasikan terpisah pada versi ini.

### Security
- Menambahkan blocklist kata/perintah destruktif pada jalur `run_command`.

## [v0.6.0] - 2026-04-23

### Added
- Menambahkan tool `get_router_log()` untuk membaca log sistem router.
- Menambahkan tool `get_router_config()` untuk mengambil 20+ section konfigurasi MikroTik.
- Menambahkan tool `get_routing_full()` untuk inspeksi protokol routing secara terpadu.
- Menambahkan section inspeksi `ip-neighbor`, `ip-arp`, dan `ip-neighbor-detail`.

### Changed
- Klarifikasi istilah "neighbor" pada system prompt agar membedakan konteks LLDP/CDP vs OSPF.

### Fixed
- Tidak ada perbaikan bug mayor yang didokumentasikan terpisah pada versi ini.

### Security
- Tidak ada perubahan security spesifik pada versi ini.

## [v0.5.0] - 2026-04-22

### Added
- Menambahkan tools pembacaan laporan: `list_reports`, `get_report_toc`, `read_report`, dan `read_report_section`.

### Changed
- Menaikkan batas truncation laporan di `tui.py` dari 4000 menjadi 12000 karakter.

### Fixed
- Memperbaiki error `INVALIDCHATHISTORY` di `tui.py` dengan mekanisme auto-reset dan retry.
- Memperbaiki validasi nama router agar case-insensitive di `_validate_router()`.

### Security
- Tidak ada perubahan security spesifik pada versi ini.

## [v0.4.0] - 2026-04-21

### Added
- Menambahkan dukungan `.env` untuk `OLLAMA_BASE_URL` dan `OLLAMA_MODEL` pada `agent.py` dan `generate_reports.py`.
- Menambahkan `_load_dotenv()` manual tanpa dependency `python-dotenv`.
- Menambahkan tool `get_current_time()` dengan zona waktu WIB (UTC+7).
- Menambahkan system prompt dinamis dengan injeksi waktu saat agent dibuat.

### Changed
- Memindahkan konfigurasi endpoint/model Ollama dari nilai statis menjadi konfigurasi eksternal berbasis `.env`.

### Fixed
- Tidak ada perbaikan bug mayor yang didokumentasikan terpisah pada versi ini.

### Security
- Mengurangi risiko hardcoded konfigurasi AI dengan pemisahan konfigurasi ke file environment lokal.

## [v0.3.0] - 2026-04-20

### Added
- Menambahkan `agent.py` berbasis LangGraph ReAct.
- Menambahkan tool awal agent: `list_routers`, `check_reachability`, `get_system_info`, `get_dhcp_leases`, `get_all_leases_for_router`, `audit_all_routers`, `search_device`.
- Menambahkan `generate_reports.py` untuk pembuatan laporan markdown harian dengan analisis AI.

### Changed
- Memperluas alur operasional dari koleksi data mentah menjadi analisis berbasis agent dan laporan otomatis.

### Fixed
- Tidak ada perbaikan bug mayor yang didokumentasikan terpisah pada versi ini.

### Security
- Tidak ada perubahan security spesifik pada versi ini.

## [v0.2.0] - 2026-04-19

### Added
- Menambahkan `tui.py` berbasis curses.
- Menambahkan 6 layar operasional: Dashboard, Jadwal, Collect, Laporan, Log, AI Chat.
- Menambahkan auto-refresh dashboard.
- Menambahkan integrasi Ollama HTTP sebagai fallback AI Chat.

### Changed
- Mengubah mode operasi dari CLI-only menjadi kombinasi CLI + terminal UI.

### Fixed
- Tidak ada perbaikan bug mayor yang didokumentasikan terpisah pada versi ini.

### Security
- Tidak ada perubahan security spesifik pada versi ini.

## [v0.1.0] - 2026-04-18

### Added
- Rilis awal proyek monitoring DHCP lease.
- Menambahkan `mikrotik_agent.py` sebagai SSH collector dan parser DHCP.
- Menambahkan dukungan RouterOS v6 dan v7.
- Menambahkan output file ke `output/*.txt`.
- Menambahkan CLI flags: `--config`, `--dry-run`, `--detail`, `--no-save`.

### Changed
- Tidak ada perubahan pada versi awal.

### Fixed
- Tidak ada perbaikan pada versi awal.

### Security
- Menetapkan praktik non-commit untuk konfigurasi sensitif (`config.yaml`) sebagai baseline operasional.
