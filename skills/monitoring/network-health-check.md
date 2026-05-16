---
name: network-health-check
domain: monitoring
triggers:
  - cek kesehatan jaringan
  - status jaringan kampus
  - health check semua router
  - overview jaringan
  - ringkasan kondisi jaringan
  - semua router baik-baik saja
  - jaringan normal
  - cek kondisi semua router
tools:
  - check_reachability
  - get_system_info
  - get_interface_stats
  - audit_dhcp
  - get_bgp_sessions
  - get_ospf_neighbors
  - get_router_log
  - list_routers
  - run_command_all
approval_required: false
enabled: true
---

# Network Health Check — Pemeriksaan Menyeluruh Jaringan

## Konteks
Gunakan skill ini untuk mendapatkan gambaran kondisi jaringan kampus secara keseluruhan.
Cocok untuk pemeriksaan rutin pagi hari, sebelum event besar (ujian, wisuda), atau saat
ada laporan umum "jaringan bermasalah" tanpa detail spesifik.

## Prosedur

### Langkah 1: Cek Reachability Semua Router
Panggil `list_routers()` terlebih dahulu untuk mendapat daftar router yang valid.
Gunakan `check_reachability` pada setiap router dalam daftar tersebut.

Kategorikan hasil:
- Router tidak reachable sama sekali → ✗ KRITIS — eskalasi segera
- Router reachable tapi lambat (latency > 100ms) → ⚠ investigasi

**→ LANGKAH 1 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_system_info untuk setiap router yang reachable.**

### Langkah 2: Cek Resource Router yang Aktif
Gunakan `get_system_info` untuk router yang reachable. Nilai yang perlu diperhatikan:
- **`cpu-load:`** → CPU usage dalam %. Lebih dari 80%: router dalam kondisi berat
- **`free-memory:` dan `total-memory:`** → hitung `(total-free)/total × 100%` untuk Memory%. Lebih dari 90%: risiko crash
- **`uptime:`** → Kurang dari 10 menit: router baru restart — cari penyebab di log

**→ LANGKAH 2 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_interface_stats untuk setiap router aktif.**

### Langkah 3: Cek Error Interface
Gunakan `get_interface_stats(router_name)` untuk router aktif. Identifikasi:
- **Rx/Tx errors > 0** → ada masalah fisik atau duplex mismatch
- **Drops tinggi** → antrian penuh, indikasi congestion atau overload
- **Interface yang harusnya up tapi down** → koneksi fisik putus atau port mati

**→ LANGKAH 3 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL get_bgp_sessions untuk router gateway (GATE-*, BORDER-*).**

### Langkah 4: Cek Status Routing (Gateway/Border Router)
Untuk router yang berperan sebagai gateway atau edge (GATE-*, BORDER-*):

**BGP:** `get_bgp_sessions(router_name)`
- Session DOWN → koneksi ke provider/peer terputus — dampak ke reachability Internet
- Prefix count turun signifikan → routing tidak lengkap

**OSPF:** `get_ospf_neighbors(router_name)`
- Neighbor tidak Full (Init/2-Way/Exstart) → koneksi internal bermasalah
- State-changes tinggi (SC > 20) → riwayat instabilitas

**→ LANGKAH 4 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL audit_dhcp.**

### Langkah 5: Audit DHCP
Jalankan `audit_dhcp`. Identifikasi:
- Pool utilisasi > 85% → segera tambah range atau investigasi exhaustion
- Router dengan DHCP yang gagal dihubungi

**→ LANGKAH 5 SELESAI. JANGAN TULIS APAPUN. LANGSUNG PANGGIL run_command_all untuk cek NTP.**

### Langkah 6: Cek Sinkronisasi Waktu
Jalankan `run_command_all` dengan perintah `/system/clock/print`.

**→ LANGKAH 6 SELESAI. JANGAN TULIS APAPUN. Jika ada router bermasalah, PANGGIL get_router_log untuk router tersebut. Jika tidak ada, LANGSUNG tulis laporan.**

### Langkah 7: Cek Log Anomali (Hanya Router Bermasalah)
Untuk router yang menunjukkan masalah (CPU tinggi, interface error, restart baru):
`get_router_log(router_name, lines=20)`

**→ LANGKAH 7 SELESAI. SEMUA DATA TERKUMPUL. SEKARANG TULIS LAPORAN.**

---

## ATURAN KRITIS — WAJIB DIPATUHI

1. **DILARANG mencetak teks dari bagian "Output yang Diharapkan"** sebelum semua tool selesai dipanggil.
2. **HANYA tulis baris untuk router yang namanya muncul dalam hasil `list_routers()`** — jumlah baris = jumlah router aktual. DILARANG menambahkan nama router yang tidak ada di daftar tersebut.
3. **SEMUA nilai wajib dari tool result aktual:** CPU dari `cpu-load:`, Memory dari `(total-memory - free-memory) / total-memory × 100`, Latency dari check_reachability. Jika tool GAGAL (SSH error, timeout): tulis "Error" — bukan N/A atau asumsi.
4. DILARANG mengulangi, mengarang, atau mengisi placeholder dengan data dari pengetahuan training.

---

## INSTRUKSI: Tulis output di bawah ini HANYA setelah Langkah 1–7 selesai semua.

## Output yang Diharapkan

**NETWORK HEALTH — [hasil get_current_time()]**
**Status:** ✅ [jumlah] normal · ⚠️ [jumlah] perhatian · 🚨 [jumlah] kritis

## Reachability

| Router | Status | Latency |
|--------|--------|---------|
| [nama dari list_routers()] | [✅/🚨 dari check_reachability] | [RTT ms atau timeout] |

## Resource

| Router | CPU | Memory | Uptime | Status |
|--------|-----|--------|--------|--------|
| [nama dari list_routers()] | [cpu-load% dari get_system_info] | [memory% dari get_system_info] | [uptime dari get_system_info] | [✅/⚠️/🚨] |

## Protokol Routing

| Router | BGP | OSPF | Status |
|--------|-----|------|--------|
| [hanya router GATE-* atau BORDER-*] | [X/Y established dari get_bgp_sessions] | [Full/Down dari get_ospf_neighbors] | [✅/⚠️/🚨] |

## Action Items

1. 🚨 **SEGERA** — [tindakan mendesak]
2. ⚠️ **PERLU** — [tindakan penting]

*Jika tidak ada masalah: "✅ Tidak ada action item."*

## Catatan
- Health check menyeluruh bisa memakan waktu 2-5 menit karena berjalan paralel
- Lakukan health check sebelum melaporkan status jaringan ke atasan atau NOC pusat
- Jika router tidak reachable → skill `network-reachability` untuk investigasi lebih dalam
- Jika BGP/OSPF bermasalah → skill `bgp-diagnostics` atau `ospf-diagnostics`
- Jika interface error → skill `link-diagnostics`
- Jika DHCP hampir penuh → skill `dhcp-pool-audit`


## Validasi Mandiri

Sebelum lapor ke operator, pastikan:
- [ ] Data dikumpulkan dari semua sumber relevan
- [ ] Temuan dikonfirmasi dengan minimal 2 data point (bukan hanya 1 tool)
- [ ] Anomali: bandingkan dengan baseline atau history sebelum simpulkan masalah
- [ ] Jika ada kegagalan tool (SSH timeout, error): coba router/interface alternatif dulu

Jika validasi belum lengkap → coba sumber alternatif, baru lapor jika memang tidak bisa resolve.

## Handoff

| Kondisi | Aksi | Agent Tujuan |
|---------|------|--------------|
| Interface down atau packet loss tinggi | Serahkan detail interface + router | diagnose_agent |
| Konfigurasi perlu diperbaiki | Serahkan perintah + approval | config_agent |
| Semua sehat | Tidak perlu handoff | END |
