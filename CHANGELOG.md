# Changelog

Semua perubahan penting pada proyek ini akan didokumentasikan di file ini.

Format mengikuti [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
dan proyek ini menggunakan [Semantic Versioning](https://semver.org/lang/id/).

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
