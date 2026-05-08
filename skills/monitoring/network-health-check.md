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
tools:
  - check_reachability
  - get_system_info
  - get_interface_stats
  - audit_dhcp
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

### Langkah 2: Cek Resource Router yang Aktif
Untuk router yang reachable, gunakan `get_system_info` untuk memeriksa:
- CPU usage > 80% → router dalam kondisi berat, perlu investigasi
- Memory usage > 90% → risiko crash, perlu perhatian segera
- Uptime < 10 menit → router baru restart, perlu dicari penyebabnya

### Langkah 3: Audit DHCP
Jalankan `audit_dhcp` untuk mendapatkan status DHCP di seluruh jaringan. Identifikasi:
- Pool yang utilisasinya > 85%
- Router dengan DHCP yang gagal dihubungi
- Perubahan signifikan jumlah client dibanding baseline normal

### Langkah 4: Cek Sinkronisasi Waktu
Jalankan `run_command_all` dengan perintah `/system/clock/print` untuk memastikan semua
router memiliki waktu yang sinkron. Jam yang tidak sinkron bisa menyebabkan masalah
autentikasi dan logging.

## Output yang Diharapkan
Laporan ringkas berformat:

```
NETWORK HEALTH — [tanggal jam]
═══════════════════════════════════
Reachability : X/Y router up (Z down: nama-router)
CPU          : semua normal | ⚠ ROUTER-A: 87%
Memory       : semua normal | ⚠ ROUTER-B: 91%
DHCP         : X client aktif total, Y pool > 80% utilisasi
NTP          : semua sinkron | ⚠ Z router tidak sinkron

Status       : ✓ NORMAL / ⚠ PERLU PERHATIAN / ✗ ADA MASALAH
```

## Catatan
- Health check menyeluruh bisa memakan waktu 2-5 menit karena berjalan paralel
- Lakukan health check sebelum melaporkan status jaringan ke atasan atau NOC pusat
- Jika router tidak reachable, lanjutkan ke skill `router-unreachable` untuk investigasi
  lebih dalam
