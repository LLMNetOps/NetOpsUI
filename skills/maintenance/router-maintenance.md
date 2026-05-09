---
name: router-maintenance
domain: maintenance
triggers:
  - upgrade firmware
  - update RouterOS
  - jadwal maintenance
  - reboot router
  - restart router terjadwal
  - pemeliharaan rutin
  - update paket RouterOS
  - cek versi RouterOS
  - maintenance window
tools:
  - get_system_info
  - run_command
  - backup_router_config
  - check_reachability
  - get_router_log
  - list_routers
approval_required: true
enabled: true
---

# Prosedur Maintenance Router MikroTik

## Konteks
Gunakan skill ini untuk melaksanakan maintenance rutin router kampus: pengecekan
versi firmware, upgrade RouterOS, dan prosedur reboot terjadwal. Semua operasi
maintenance memerlukan persetujuan operator dan sebaiknya dilakukan di luar jam
sibuk (rekomendasi: 23:00-05:00 atau akhir pekan).

**PENTING:** Maintenance yang menyebabkan downtime HARUS dikomunikasikan ke pengguna
dan koordinator TI sebelum dilaksanakan.

## Prosedur Cek Versi dan Kondisi Router

### Langkah 1: Audit Versi RouterOS
Gunakan `get_system_info(router_name)` untuk semua router. Kumpulkan informasi:
- Versi RouterOS yang berjalan
- Versi arsitektur (arm, arm64, mipsbe, x86)
- Uptime saat ini

**Panduan usia versi RouterOS:**
| Versi | Estimasi Rilis | Usia (per 2026) | Prioritas Upgrade |
|-------|---------------|-----------------|-------------------|
| 6.x   | s/d 2022      | > 3 tahun       | TINGGI — EOL mendekat |
| 7.10-7.11 | 2023     | > 2 tahun       | SEDANG |
| 7.12-7.14 | 2023-2024 | 1-2 tahun     | RENDAH |
| 7.15+ | 2024+        | < 1 tahun       | Opsional — tunggu stabil |

Router dengan versi 6.x atau yang sudah > 2 tahun → rekomendasikan jadwal upgrade.

### Langkah 2: Cek Paket yang Tersedia
```
/system/package/print
```
Paket yang perlu diperhatikan: `routeros`, `wireless`, `bgp`, `ospf`, `dhcp`.
Pastikan semua paket yang di-install sesuai kebutuhan (tidak ada paket tidak perlu).

### Langkah 3: Cek Resource Sebelum Maintenance
```
get_system_info(router_name)
```
- Pastikan storage mencukupi untuk file upgrade (minimal 10 MB free)
- Catat uptime sebelum maintenance untuk referensi

## Prosedur Upgrade RouterOS

### Pra-syarat
- Window maintenance sudah dikomunikasikan (minimal 24 jam sebelumnya)
- Backup konfigurasi terbaru sudah ada
- Akses konsol fisik atau out-of-band tersedia jika upgrade gagal
- Versi target sudah diverifikasi kompatibel dengan hardware

### Langkah 1: Backup
Jalankan `backup_router_config(router_name)`. Catat nama file backup.

### Langkah 2: Upload File Upgrade
Via Winbox/FTP atau command:
```
/tool/fetch url=https://download.mikrotik.com/routeros/<ver>/routeros-<arch>-<ver>.npk
```
Verifikasi file berhasil didownload:
```
/file/print where name~".npk"
```

### Langkah 3: Jadwalkan Upgrade
Untuk upgrade yang memerlukan reboot:
```
/system/package/update/install
```
Atau jadwalkan reboot di window maintenance:
```
/system/scheduler/add name=upgrade-reboot start-time=23:00:00
  interval=1d on-event="/system/reboot"
```

### Langkah 4: Monitor Pasca Upgrade
Setelah router reboot (biasanya 2-5 menit), verifikasi:
- `check_reachability(router_name)` — router accessible kembali
- `get_system_info(router_name)` — versi sudah terupdate
- `get_bgp_sessions(router_name)` — BGP established kembali (untuk gateway router)
- `get_ospf_neighbors(router_name)` — OSPF Full kembali

Tunggu minimal 5 menit setelah router online sebelum menyatakan upgrade berhasil.

### Langkah 5: Verifikasi Fungsionalitas
```
get_router_log(router_name, lines=30)
```
Pastikan tidak ada error setelah startup. Jika ada error baru → investigasi sebelum
lanjut upgrade router berikutnya.

## Prosedur Reboot Terjadwal

### Reboot Segera (dengan persetujuan)
```
/system/reboot
```

### Jadwalkan Reboot di Waktu Tertentu
```
/system/scheduler/add name=scheduled-reboot
  start-date=2026-05-10 start-time=23:00:00
  interval=0 on-event="/system/reboot"
  comment="Maintenance reboot 10 Mei 2026"
```

### Verifikasi Scheduler
```
/system/scheduler/print
```
Hapus scheduler setelah reboot berhasil untuk menghindari reboot berulang:
```
/system/scheduler/remove [find name=scheduled-reboot]
```

## Prosedur Maintenance Preventif (Bulanan)

Jalankan secara rutin setiap bulan untuk semua router:

1. **Cek resource**: CPU trend, memory usage
2. **Cek log error**: `get_router_log(router_name, lines=50)` — catat error berulang
3. **Cek interface errors**: counter rx-error dan tx-error — reset setelah dicatat
4. **Verifikasi backup**: pastikan ada backup config < 7 hari
5. **Cek versi**: bandingkan dengan versi terbaru, jadwalkan upgrade jika perlu
6. **Cek storage**: `df` atau `/file/print` — pastikan tidak mendekati penuh
7. **Cek user aktif**: `/user/active/print` — pastikan tidak ada sesi mencurigakan

## Output yang Diharapkan
- Status versi RouterOS semua router (current vs latest)
- Daftar router yang memerlukan upgrade (berdasarkan usia versi)
- Konfirmasi upgrade/reboot berhasil dengan versi baru
- Log pasca maintenance (bersih / ada anomali)

## Catatan
- Upgrade router produksi SELALU di window maintenance, TIDAK pernah jam sibuk
- Urutan upgrade: test di router non-kritis dulu, baru gateway/border router
- Jika upgrade gagal dan router tidak bisa diakses → akses konsol fisik untuk recovery
- Simpan catatan maintenance (tanggal, versi sebelum/sesudah, nama teknisi) ke laporan
- Router yang menjalankan BGP IDREN: koordinasi dengan NOC IDREN sebelum maintenance
