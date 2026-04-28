---
name: network-report
domain: monitoring
triggers:
  - buat laporan jaringan
  - laporan harian jaringan
  - laporan kondisi jaringan
  - rangkum kondisi jaringan
  - laporan status jaringan
  - buat ringkasan jaringan
  - network report
  - daily report
  - rekap jaringan
  - buat laporan operasional
tools:
  - list_routers
  - check_reachability
  - get_system_info
  - audit_dhcp
  - get_router_log
  - run_command_all
  - get_current_time
approval_required: false
enabled: true
---

# Membuat Laporan Operasional Jaringan

## Konteks
Gunakan skill ini saat operator meminta laporan atau ringkasan kondisi jaringan kampus.
Laporan ini menggabungkan data live dari semua router dan disajikan dalam format yang
dapat langsung dibagikan ke tim atau atasan.

Laporan mencakup: reachability, resource utilization, status DHCP, anomali log, dan
rekomendasi tindakan.

## Prosedur

### Langkah 1: Catat Waktu Laporan
Gunakan `get_current_time` untuk mendapatkan timestamp WIB yang akan dipakai sebagai
header laporan.

### Langkah 2: Kumpulkan Data Reachability
Jalankan `check_reachability` untuk setiap router. Kelompokkan hasilnya:
- Router UP (reachable): catat RTT
- Router DOWN (unreachable): tandai sebagai prioritas investigasi

### Langkah 3: Cek Resource Router yang Up
Untuk router yang reachable, jalankan `get_system_info` dan catat:
- CPU usage — tandai jika > 80%
- Memory usage — tandai jika > 85%
- Uptime — tandai jika < 10 menit (kemungkinan baru reboot)
- Versi RouterOS — catat untuk informasi

### Langkah 4: Audit DHCP
Jalankan `audit_dhcp` untuk mendapat gambaran DHCP seluruh jaringan:
- Total client aktif (bound)
- Pool yang utilisasinya tinggi (> 80%)
- Server yang gagal diakses

### Langkah 5: Cek Sinkronisasi NTP
Jalankan `run_command_all` dengan perintah `/system/clock/print`.
Identifikasi router yang jamnya tidak sinkron atau berbeda jauh dari WIB (UTC+7).

### Langkah 6: Cek Log Anomali
Jalankan `get_router_log` pada router utama (backbone/core) dengan filter topic
`critical` atau tanpa filter. Cari:
- Interface yang flap (naik-turun)
- Pesan `critical` atau `error`
- Login/logout yang tidak biasa

## Format Output

Susun laporan dalam format berikut. Gunakan simbol ✓ (normal), ⚠ (perhatian), ✗ (kritis).

```
═══════════════════════════════════════════════════════
  LAPORAN OPERASIONAL JARINGAN KAMPUS
  [Hari, Tanggal] — [Jam] WIB
═══════════════════════════════════════════════════════

## RINGKASAN EKSEKUTIF
[1-2 kalimat status keseluruhan jaringan. Sebutkan jumlah router up/down
dan apakah ada masalah signifikan yang perlu perhatian segera.]

---

## 1. REACHABILITY
Router UP   : X / Y (daftar nama)
Router DOWN : Z (nama router — tandai ✗)

---

## 2. RESOURCE UTILIZATION
[Tabel atau list per router:]
  ROUTER-A  CPU:  8%  RAM: 45%  Uptime: 14d  ✓
  ROUTER-B  CPU: 87%  RAM: 72%  Uptime:  3d  ⚠ CPU tinggi
  ROUTER-C  (tidak dapat diakses)              ✗

---

## 3. STATUS DHCP
Total client aktif : X client
Total waiting      : Y
Pool utilisasi tinggi:
  - ROUTER/server (Z%) ⚠

Router DHCP gagal diakses: (nama jika ada)

---

## 4. SINKRONISASI WAKTU (NTP)
  X router sinkron  ✓
  Y router tidak sinkron atau gagal dicek  ⚠

---

## 5. ANOMALI LOG
[Daftar pesan penting dari log. Jika tidak ada anomali, tulis "Tidak ditemukan anomali signifikan."]
  - ROUTER-X: interface ether2 flap pukul 01:23
  - ROUTER-Y: login gagal 3x dari 192.168.1.100

---

## 6. REKOMENDASI
[Tindakan konkret berurutan dari prioritas tertinggi:]
1. [Tindakan kritis — jika ada router down atau resource kritis]
2. [Tindakan preventif — pool hampir penuh, CPU tinggi, dll]
3. [Tindakan rutin — jika kondisi normal]

---
Status Keseluruhan : ✓ NORMAL / ⚠ PERLU PERHATIAN / ✗ KRITIS
═══════════════════════════════════════════════════════
```

## Catatan
- Laporan ini adalah snapshot kondisi saat dijalankan, bukan data historis
- Jika ada router DOWN, prioritaskan menginvestigasi dengan skill `router-unreachable`
  sebelum atau sesudah menyusun laporan
- Untuk laporan yang sangat lengkap (traffic stats per interface), operator bisa
  meminta tambahan dengan query lanjutan
- Jika diminta laporan dalam format tertentu (PDF, tabel, dll) — sampaikan bahwa
  output saat ini adalah teks/Markdown yang bisa disalin
