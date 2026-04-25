# MikroTik DHCP Lease Monitoring - UTBK 2026

Sistem monitoring DHCP lease berbasis Python untuk operasional ujian UTBK 2026 di lingkungan universitas. Proyek ini mengambil data lease dari **17 router MikroTik** secara paralel, menyajikannya ke terminal/TUI, lalu menghasilkan laporan harian dengan analisis AI.

Fokus utama proyek:
- Visibilitas cepat kondisi lease DHCP lintas fakultas/gedung.
- Pemantauan terpusat selama sesi ujian UTBK.
- Audit dan diagnosa jaringan melalui AI agent berbasis LangGraph + Ollama.

## Fitur Utama

- Koleksi DHCP lease dari 17 router secara paralel (`ThreadPoolExecutor`).
- Kompatibel dengan RouterOS v6 dan v7.
- Parsing status lease: `bound`, `waiting`, `disabled`.
- Curses TUI dengan 6 layar operasional: Dashboard, Jadwal, Collect, Laporan, Log, AI Chat.
- Auto-refresh dashboard setiap 5 detik.
- Integrasi AI agent (`agent.py`) dengan 18 tools operasional jaringan.
- Fallback AI chat ke Ollama HTTP saat alur LangGraph tidak tersedia.
- Generasi laporan markdown harian dari data mentah di `output/`.
- Dukungan mode uji parser via `--dry-run`.

## Arsitektur Komponen

### Ringkasan Alur

```text
[MikroTik Routers x17]
          |
          v
 [mikrotik_agent.py] --(raw txt)--> [output/*.txt]
          |                               |
          |                               v
          |                    [generate_reports.py]
          |                               |
          |                        [laporan/*.md]
          |
          v
      [tui.py] <-------------------- baca laporan
          |
          v
 [agent.py (LangGraph ReAct + Ollama)]
```

### Detail Komponen

| Komponen | Peran | Output/Integrasi |
|---|---|---|
| `mikrotik_agent.py` | Kolektor SSH paralel, parser lease DHCP, dukungan ROS v6/v7 | Tabel terminal + `output/*.txt` |
| `tui.py` | Antarmuka curses 6 layar, auto-refresh 5 detik, orkestrasi subprocess | Menjalankan `mikrotik_agent.py`, baca `laporan/*.md`, AI Chat |
| `agent.py` | LangGraph ReAct agent (MemorySaver, `recursion_limit=50`) + 18 tools | Analisis/audit jaringan via Ollama |
| `generate_reports.py` | Agregasi semua raw output dan generate laporan harian markdown + analisis AI | `laporan/*.md` |
| `schedule_utbk.sh` | Otomasi penjadwalan pengambilan data | Eksekusi periodik collector/report |

## Prerequisites

- Python `3.10+`
- Linux/macOS terminal (untuk mode curses TUI)
- Akses jaringan ke router MikroTik melalui SSH
- Ollama (lokal atau endpoint remote)
- Kredensial router dan daftar DHCP server yang valid

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit OLLAMA_BASE_URL dan OLLAMA_MODEL
# buat config.yaml manual (tidak ada template karena berisi password)
```

## Konfigurasi

### 1. `.env` (Tidak Di-commit)

Contoh:

```env
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.6:35b-a3b-q8_0
```

Keterangan:
- `OLLAMA_BASE_URL`: URL endpoint Ollama.
- `OLLAMA_MODEL`: Nama model default untuk AI agent dan report generator.

### 2. `config.yaml` (Tidak Di-commit)

Berisi:
- SSH credentials: `username`, `password`, `timeout`, `port`.
- Daftar 17 router UTBK berikut DHCP server per router.
- `ros_version` per router (`6` atau `7`).

Contoh struktur minimum:

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

Pastikan virtual environment aktif:

```bash
source .venv/bin/activate
```

### A. Jalankan TUI Operasional

```bash
python tui.py
```

Layar TUI:
- `Dashboard`: status ringkas lease lintas router.
- `Jadwal`: informasi jadwal pengumpulan/monitoring.
- `Collect`: trigger koleksi data via `mikrotik_agent.py`.
- `Laporan`: baca file markdown di `laporan/`.
- `Log`: catatan aktivitas/eksekusi.
- `AI Chat`: interaksi agent (`agent.py`) dengan fallback Ollama HTTP.

### B. Koleksi Data DHCP Saja

```bash
python mikrotik_agent.py
```

Opsi CLI penting:

```bash
python mikrotik_agent.py --config config.yaml
python mikrotik_agent.py --detail
python mikrotik_agent.py --no-save
python mikrotik_agent.py --dry-run FILE
```

### C. Generate Laporan Harian

```bash
python generate_reports.py
```

### D. Uji Parser dari File Lokal

```bash
python mikrotik_agent.py --dry-run output/dhcp-lease-sample.txt
```

## Daftar Tools AI Agent (`agent.py`)

| No | Tool | Fungsi Singkat |
|---|---|---|
| 1 | `list_routers` | Daftar router dan DHCP server |
| 2 | `check_reachability` | Uji konektivitas/ping router |
| 3 | `get_system_info` | Info CPU/RAM/uptime via SSH |
| 4 | `get_dhcp_leases` | Ambil lease dari satu DHCP server |
| 5 | `get_all_leases_for_router` | Agregasi lease semua server per router |
| 6 | `get_router_config` | Ambil 20+ section konfigurasi router |
| 7 | `get_routing_full` | Cek protokol routing secara menyeluruh |
| 8 | `get_router_log` | Baca log sistem router |
| 9 | `audit_all_routers` | Audit DHCP paralel semua router |
| 10 | `search_device` | Cari IP/MAC lintas router |
| 11 | `get_current_time` | Waktu lokal WIB (UTC+7) |
| 12 | `list_reports` | Daftar file laporan |
| 13 | `get_report_toc` | Ambil daftar isi laporan |
| 14 | `read_report` | Baca isi laporan (limit 8000 karakter) |
| 15 | `read_report_section` | Baca section spesifik laporan |
| 16 | `run_command` | Perintah read-only MikroTik dengan blocklist |
| 17 | `run_diagnostic` | Traceroute/ping dengan timeout 60 detik |
| 18 | `run_command_all_routers` | Eksekusi command paralel ke semua router |

## Requirements

`requirements.txt`:

```txt
paramiko>=3.0
pyyaml>=6.0
tabulate>=0.9
requests>=2.28
langchain-ollama>=0.3.0
langchain-core>=0.3.0
langgraph>=0.2.0
```

## Struktur Direktori

```text
mikrotik-cek-lease/
|-- agent.py             # LangGraph ReAct AI agent (18 tools)
|-- tui.py               # Curses TUI (6 screens)
|-- mikrotik_agent.py    # SSH collector + parser
|-- generate_reports.py  # Laporan markdown harian
|-- schedule_utbk.sh     # Shell scheduler
|-- config.yaml          # Router credentials (TIDAK di-commit)
|-- .env                 # Ollama config (TIDAK di-commit)
|-- .env.example         # Template .env
|-- requirements.txt     # Python dependencies
|-- output/              # Raw DHCP data (TIDAK di-commit)
`-- laporan/             # Generated reports (TIDAK di-commit)
```

## Security Notes

- Jangan commit `config.yaml`, `.env`, isi `output/`, dan `laporan/` yang sensitif.
- Gunakan kredensial SSH minimum privilege khusus monitoring.
- Tool `run_command` dibatasi blocklist kata destruktif, tetapi tetap perlakukan sebagai fitur sensitif.
- Validasi endpoint `OLLAMA_BASE_URL` bila menggunakan host non-lokal.
- Simpan backup konfigurasi router di lokasi terpisah dan terenkripsi.

## Known Limitations

- Pembacaan `OLLAMA_BASE_URL` dan `OLLAMA_MODEL` di jalur TUI masih memiliki bagian hardcoded (known issue).
- `read_report` dibatasi 8000 karakter per panggilan tool (untuk menjaga ukuran konteks AI).
- Kinerja sangat bergantung pada stabilitas SSH dan latensi antar-segmen jaringan kampus.
- Parsing lease bergantung pada format output RouterOS; perubahan versi mayor dapat memerlukan penyesuaian parser.

## Konteks Operasional UTBK 2026

Proyek ini dirancang untuk fase operasional April 2026 dalam mendukung monitoring jaringan ujian UTBK. Prioritas desain saat ini adalah keandalan koleksi data, visibilitas cepat melalui TUI, dan dukungan troubleshooting berbasis AI untuk tim jaringan lapangan.
