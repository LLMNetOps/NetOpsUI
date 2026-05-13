---
name: capacity-planning
domain: monitoring
triggers:
  - bandwidth hampir penuh
  - kapasitas jaringan
  - utilisasi link tinggi
  - perlu upgrade bandwidth
  - IP pool mau habis
  - DHCP pool penuh
  - capacity planning
  - analisis kapasitas
  - tren penggunaan jaringan
  - berapa bandwidth yang dipakai
tools:
  - get_traffic_summary
  - get_interface_stats
  - audit_dhcp
  - get_system_info
  - run_command
  - list_routers
approval_required: false
enabled: true
---

# Capacity Planning Jaringan Kampus

## Konteks
Gunakan skill ini untuk menganalisis kapasitas jaringan kampus: utilisasi bandwidth,
ketersediaan pool DHCP, dan resource router. Tujuannya untuk mengidentifikasi titik
bottleneck sebelum terjadi masalah dan mendukung perencanaan pengembangan infrastruktur.

## Prosedur Analisis Bandwidth

### Langkah 1: Snapshot Traffic Saat Ini
Gunakan `get_traffic_summary(router_name)` untuk semua router aktif.
Atau per router dengan:
```
/interface/print stats
/interface/monitor-traffic [interface] once
```

### Langkah 2: Identifikasi Interface Kritis
Interface yang perlu diperhatikan:
- **WAN / Uplink** — koneksi ke provider Internet dan IDREN
- **Inter-router link** — antar gedung/fakultas
- **Distribution uplink** — router ke switch distribusi

### Langkah 3: Hitung Utilisasi
```
Utilisasi (%) = (throughput_aktual / kapasitas_link) × 100
```

**Threshold:**
| Utilisasi | Status | Tindakan |
|-----------|--------|---------|
| < 50% | Normal | Monitor rutin |
| 50-70% | Perhatian | Monitor lebih sering, analisis tren |
| 70-85% | ⚠ Mendekati penuh | Rencanakan upgrade dalam 3-6 bulan |
| > 85% | ✗ Kritis | Eskalasi segera — degradasi layanan aktif |

### Langkah 4: Analisis Pola Penggunaan
Bandingkan traffic di:
- **Jam sibuk** (08:00-16:00 hari kerja): baseline normal
- **Malam hari**: jika tinggi → mungkin ada aktivitas mencurigakan atau backup
- **Akhir pekan**: jika lebih rendah dari hari kerja → pola normal kampus

Untuk tren historis, gunakan data dari SNMP/monitoring system (jika tersedia).

### Langkah 5: Identifikasi Top Talker (Jika Ada Akses)
Jika ada torch atau traffic monitoring:
```
/tool/torch interface=<ether1> ip=0.0.0.0/0
```
Identifikasi IP atau protocol yang mendominasi bandwidth.

## Prosedur Analisis DHCP Pool

### Langkah 1: Audit Semua Pool
Jalankan `audit_dhcp()` untuk mendapatkan utilisasi semua pool DHCP di seluruh router.

### Langkah 2: Hitung Utilisasi Per Pool
```
Utilisasi (%) = (leases_aktif / total_range) × 100
```

**Threshold:**
| Utilisasi Pool | Status | Tindakan |
|---------------|--------|---------|
| < 60% | Normal | — |
| 60-80% | Perhatian | Monitor, siapkan rencana ekspansi |
| 80-90% | ⚠ Mendekati penuh | Ekspansi pool dalam waktu dekat |
| > 90% | ✗ Kritis | Ekspansi segera — client baru tidak bisa dapat IP |

### Langkah 3: Analisis Pool yang Kritis
Untuk pool > 80% utilisasi:
```
/ip/dhcp-server/lease/print count-only where server=<server-name>
```

Cek:
- Berapa lease aktif vs expired vs static
- Apakah ada lease dengan MAC yang tidak aktif (ghost lease)
- Berapa lama lease time (apakah terlalu panjang sehingga pool lambat dilepas)

### Langkah 4: Opsi Ekspansi Pool
**Pilihan 1: Perluas range pool yang ada**
```
/ip/pool/set <pool-name> ranges=192.168.1.100-192.168.1.250
```
(dari sebelumnya 192.168.1.100-192.168.1.200)

**Pilihan 2: Tambah range ke pool yang ada**
Hanya jika IP di luar range saat ini tersedia di subnet yang sama.

**Pilihan 3: Buat subnet baru (VLAN baru)**
Jika subnet sudah penuh — memerlukan perencanaan lebih besar (koordinasi dengan TI pusat).

**Pilihan 4: Kurangi lease time**
```
/ip/dhcp-server/set <server-name> lease-time=1h
```
(dari default 3d atau 1d) — IP lebih cepat dilepas saat perangkat disconnect.

## Prosedur Analisis Resource Router

### Langkah 1: Cek CPU dan Memory Trend
Gunakan `get_system_info` untuk semua router. Catat:
- CPU usage rata-rata
- Memory usage saat ini
- Uptime (untuk konteks — router baru restart lebih rendah memory usage-nya)

### Langkah 2: Identifikasi Router yang Overloaded
Router dengan CPU > 70% secara konsisten:
- Cek proses yang berjalan: `/system/resource/cpu/print`
- Cek jumlah connection tracking: `/ip/firewall/connection/print count-only`
- Cek apakah ada script yang berjalan intensif: `/system/script/print`

### Langkah 3: Proyeksi Pertumbuhan
Berdasarkan data yang dikumpulkan, buat proyeksi:
- Jika bandwidth naik 20% per semester → kapan akan mencapai 80%?
- Jika DHCP pool bertambah 10 client/bulan → kapan pool habis?

## Output yang Diharapkan
Laporan kapasitas yang mencakup:

```
CAPACITY REPORT — [tanggal]
═══════════════════════════════════════
BANDWIDTH UTILIZATION
  GATE-IDREN (uplink 1G):   ██████░░░░ 60% — normal
  GATE-ARENA (uplink 1G):   ████████░░ 80% — ⚠ perlu perhatian
  FIBER-FILKOM (100M):       █░░░░░░░░░ 10% — under-utilized

DHCP POOL
  FILKOM-STAFF   : 45/50 (90%)  — ✗ KRITIS, ekspansi segera
  FILKOM-STUDENT : 120/200 (60%) — normal
  PERPUSTAKAAN   : 30/100 (30%) — normal

ROUTER RESOURCE
  GATE-IDREN: CPU 45%, RAM 62% — normal
  DIST-FILKOM: CPU 72%, RAM 80% — ⚠ overloaded

Rekomendasi Prioritas:
  1. [KRITIS] Ekspansi DHCP pool FILKOM-STAFF (habis dalam < 2 minggu)
  2. [PERLU PERHATIAN] Monitor GATE-ARENA — 80% utilisasi WAN
  3. [RENDAH] Review proses di DIST-FILKOM — CPU 72% konsisten
```

## Catatan
- Analisis kapasitas sebaiknya dilakukan setiap 3 bulan (awal semester)
- Lakukan assessment sebelum event besar: penerimaan mahasiswa baru, UTBK, wisuda
- Ekspansi yang memerlukan subnet baru atau perubahan routing → koordinasi dengan NOC pusat
- Data historis SNMP/Grafana lebih akurat dari snapshot manual untuk analisis tren
