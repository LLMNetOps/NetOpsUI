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
Gunakan `check_reachability` pada setiap router yang terdaftar. Identifikasi router yang
tidak merespons — ini adalah prioritas investigasi pertama.

Kategorikan hasil:
- Router tidak reachable sama sekali → ✗ KRITIS — eskalasi segera
- Router reachable tapi lambat (latency > 100ms) → ⚠ investigasi

### Langkah 2: Cek Resource Router yang Aktif
Untuk router yang reachable, gunakan `get_system_info` untuk memeriksa:
- **CPU > 80%** → router dalam kondisi berat, perlu investigasi traffic atau script loop
- **Memory > 90%** → risiko crash, perlu perhatian segera
- **Uptime < 10 menit** → router baru restart — cari penyebabnya di log
- **Uptime < 1 jam** → restart dalam 1 jam terakhir — catat sebagai anomali

### Langkah 3: Cek Error Interface
Gunakan `get_interface_stats(router_name)` untuk router aktif. Identifikasi:
- **Rx/Tx errors > 0** → ada masalah fisik atau duplex mismatch
- **Drops tinggi** → antrian penuh, indikasi congestion atau overload
- **Interface yang harusnya up tapi down** → koneksi fisik putus atau port mati

Interface yang perlu diperhatikan: uplink WAN, inter-router link, link ke distribution switch.

### Langkah 4: Cek Status Routing (Gateway/Border Router)
Untuk router yang berperan sebagai gateway atau edge (GATE-*, BORDER-*):

**BGP:**
```
get_bgp_sessions(router_name)
```
- Session DOWN → koneksi ke provider/peer terputus — dampak ke reachability Internet
- Prefix count turun signifikan dibanding biasanya → routing tidak lengkap

**OSPF:**
```
get_ospf_neighbors(router_name)
```
- Neighbor tidak Full (Init/2-Way/Exstart) → koneksi internal bermasalah
- State-changes tinggi (SC > 20) → riwayat instabilitas — monitor lebih lanjut

### Langkah 5: Audit DHCP
Jalankan `audit_dhcp` untuk mendapatkan status DHCP di seluruh jaringan. Identifikasi:
- Pool dengan utilisasi > 85% → segera tambah range atau investigasi exhaustion
- Router dengan DHCP yang gagal dihubungi
- Perubahan signifikan jumlah client dibanding baseline normal

### Langkah 6: Cek Sinkronisasi Waktu
Jalankan `run_command_all` dengan perintah `/system/clock/print` untuk memastikan semua
router memiliki waktu yang sinkron. Jam yang tidak sinkron bisa menyebabkan masalah
autentikasi dan logging.

### Langkah 7: Cek Log Anomali Singkat
Untuk router yang menunjukkan tanda masalah (CPU tinggi, interface error, restart),
jalankan `get_router_log(router_name, lines=20)` untuk melihat event terbaru.

Cari:
- `critical` atau `error` — masalah aktif
- `interface changed state` — link flapping
- `BGP` atau `OSPF` state change — routing instability
- `login failure` berulang — kemungkinan serangan

## Output yang Diharapkan
Laporan ringkas berformat:

```
NETWORK HEALTH — [tanggal jam]
═══════════════════════════════════════════════
Reachability : X/Y router up (Z down: nama-router)
CPU          : semua normal | ⚠ ROUTER-A: 87%
Memory       : semua normal | ⚠ ROUTER-B: 91%
Interface    : semua normal | ⚠ ROUTER-C: eth1 4 rx-errors
BGP          : semua established | ✗ GATE-X: 1 session DOWN
OSPF         : semua Full | ⚠ GATE-X: 1 neighbor Init
DHCP         : X client aktif, Y pool > 80% utilisasi
NTP          : semua sinkron | ⚠ Z router tidak sinkron

Status Overall: ✓ NORMAL / ⚠ PERLU PERHATIAN / ✗ ADA MASALAH
```

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
