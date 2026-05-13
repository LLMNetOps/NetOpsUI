---
name: dhcp-pool-audit
domain: dhcp
triggers:
  - audit DHCP
  - cek semua pool
  - pool DHCP hampir penuh
  - ringkasan DHCP semua router
  - berapa banyak client aktif
  - DHCP capacity
  - utilisasi pool
tools:
  - audit_dhcp
  - get_router_leases
  - list_routers
approval_required: false
enabled: true
---

# Audit DHCP Pool Semua Router

## Konteks
Gunakan skill ini saat operator ingin melihat gambaran besar kapasitas dan utilisasi DHCP
di seluruh jaringan kampus. Cocok untuk laporan harian, persiapan ujian besar (UTBK, UTS),
atau saat ada laporan banyak client tidak dapat IP secara bersamaan.

## Prosedur

### Langkah 1: Ambil Data Audit Global
Jalankan `audit_dhcp` untuk mendapatkan ringkasan dari semua router sekaligus.
Fungsi ini berjalan paralel, biasanya selesai dalam 30-90 detik.

### Langkah 2: Identifikasi Router Bermasalah
Dari hasil audit, prioritaskan perhatian pada:
- Router dengan status `✗ GAGAL` → tidak dapat dihubungi, perlu cek reachability terpisah
- Pool dengan utilisasi > 80% (bound / total > 0.8) → risiko penuh saat peak load
- Pool dengan banyak `waiting` → bisa jadi ada masalah lease expiry atau client yang sering
  reconnect

### Langkah 3: Detail Router Bermasalah
Jika ada router dengan anomali, panggil `get_router_leases` untuk mendapatkan detail
per DHCP server di router tersebut.

### Langkah 4: Hitung Metrik
Dari data audit:
- Total client aktif (bound) di seluruh jaringan
- Persentase utilisasi tiap pool
- Jumlah router yang tidak responsif

## Output yang Diharapkan
Tabel ringkasan yang mencakup:
- Semua router dan pool dengan jumlah bound/waiting/disabled
- Flag ⚠ untuk pool yang utilisasinya > 80%
- Flag ✗ untuk router yang gagal dihubungi
- Total agregat di seluruh jaringan

Tambahkan rekomendasi jika ada pool yang mendekati kapasitas.

## Catatan
- Jalankan audit saat periode tenang (bukan jam sibuk) untuk mendapat baseline
- Bandingkan hasil dengan laporan sebelumnya menggunakan `list_reports` + `get_report`
  untuk melihat tren
- UTBK session biasanya menggunakan hostname `utbk-os` — kolom UTBK di audit
  menunjukkan jumlah client ujian yang terhubung
