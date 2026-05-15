---
name: link-diagnostics
domain: interface
triggers:
  - interface error
  - interface down
  - link flapping
  - banyak packet loss
  - interface bermasalah
  - link putus-putus
  - ethernet error
  - port mati
  - drop packet
  - sfp error
  - cek interface
tools:
  - get_interface_stats
  - get_router_log
  - run_command
  - check_reachability
approval_required: false
enabled: true
---

# Diagnostik Interface dan Link Fisik

## Konteks
Gunakan skill ini ketika ada laporan packet loss, interface yang tidak stabil (flapping),
error counter yang tinggi, atau interface yang seharusnya up tapi down.
Mencakup interface Ethernet, SFP/fiber, dan bridge interface di MikroTik RouterOS.

## Prosedur

### Langkah 1: Lihat Status Interface Semua
Gunakan `get_interface_stats(router_name)` untuk mendapatkan overview semua interface.
Identifikasi:
- Interface dengan status `down` yang seharusnya `up`
- Interface dengan error counter > 0
- Interface dengan drops tinggi

### Langkah 2: Cek Counter Interface Secara Detail
Untuk interface yang mencurigakan, gunakan `run_command`:
```
/interface/print stats where name=<ether1>
```

Kolom yang penting:
| Kolom | Artinya | Threshold Perhatian |
|-------|---------|---------------------|
| rx-error | Frame error dari pihak remote | > 0 |
| tx-error | Error saat kirim | > 0 |
| rx-drop | Frame dibuang karena buffer penuh | > 100/menit |
| tx-drop | Tidak bisa kirim, buffer penuh | > 100/menit |
| rx-fcs-error | Frame Check Sequence error | > 0 (masalah fisik) |
| rx-align-error | Alignment error (biasanya duplex mismatch) | > 0 |

**Interpretasi:**
- `rx-fcs-error` tinggi → kabel bermasalah atau konektor longgar
- `rx-align-error` tinggi → duplex mismatch (satu sisi full, sisi lain half duplex)
- `rx-drop` / `tx-drop` tinggi → congestion atau interface speed terlalu rendah
- `rx-error` + `tx-error` keduanya tinggi → kemungkinan masalah fisik

### Langkah 3: Cek Log Interface
```
get_router_log(router_name, topic="interface", lines=50)
```
Cari pola:
- `<interface> link up` / `link down` bergantian → flapping aktif
- Berapa kali terjadi dan dalam rentang waktu berapa → hitung frekuensi flapping
- `<interface> changed state to down` → kapan pertama kali down

**Interpretasi flapping:**
- Flap > 5x/jam → masalah serius (kabel, SFP, port switch)
- Flap saat jam sibuk → kemungkinan congestion menyebabkan reset
- Flap terjadi bersamaan dengan BGP/OSPF state change → root cause link, bukan protocol

### Langkah 4: Cek Konfigurasi Interface
```
/interface/ethernet/print where name=<ether1>
```

Verifikasi:
- `auto-negotiate: yes` → biarkan auto negotiate (direkomendasikan untuk gigabit)
- `speed` dan `full-duplex` → jika di-set manual, harus cocok dengan perangkat di ujung lain
- `disabled: no` → pastikan tidak sengaja di-disable
- `running: yes` → link aktif secara fisik

### Langkah 5: Cek Utilisasi Interface
```
/interface/monitor-traffic <interface> once
```
Atau gunakan `get_traffic_summary(router_name)` untuk melihat semua interface.

Bandingkan throughput aktual dengan kapasitas link:
- Link 1G dengan throughput > 800 Mbps → near saturation → pertimbangkan upgrade
- Link 100M di jaringan yang seharusnya gigabit → auto-negotiate turun → cek kabel

### Langkah 6: Diagnostik SFP/Fiber
Untuk interface SFP:
```
/interface/ethernet/monitor <sfp1> once
```
Perhatikan:
- `sfp-rx-power` — daya terima cahaya (normal: -3 dBm sampai -20 dBm, tergantung jenis SFP)
- `sfp-tx-power` — daya kirim
- `sfp-temperature` — suhu modul (normal < 70°C)
- Nilai `null` atau di luar rentang → SFP rusak atau konektor kotor

## Penyebab Umum dan Solusi

| Gejala | Kemungkinan Penyebab | Tindakan |
|--------|---------------------|---------|
| Flapping terus | Kabel rusak / SFP kotor | Ganti kabel atau bersihkan SFP |
| FCS error tinggi | Kabel tidak terpasang sempurna | Cek dan pasang ulang konektor |
| Duplex mismatch | Config manual tidak cocok | Set `auto-negotiate=yes` di kedua sisi |
| Drops tinggi, speed OK | Congestion | Pertimbangkan QoS atau upgrade link |
| Link down permanen | Port switch mati / kabel putus | Cek fisik, ganti port |
| SFP rx-power rendah | Fiber kotor atau bengkok | Bersihkan konektor, cek rute fiber |

## Output yang Diharapkan
- Tabel counter interface dengan flagging error/drop yang tinggi
- Timeline flapping dari log (kapan, berapa kali, pola)
- Diagnosis root cause dengan evidence dari counter + log
- Rekomendasi tindakan (cek fisik, ganti kabel, konfigurasi duplex)

## Catatan
- Error counter terus naik saat monitoring → masalah aktif, bukan historis
- Gunakan `run_command` dengan `/interface/reset-counters <interface>` untuk reset counter
  setelah perbaikan — konfirmasi dulu ke operator
- Masalah fisik (kabel, SFP, port switch) tidak bisa diperbaiki via remote —
  koordinasikan dengan teknisi lapangan
- Untuk interface yang flapping terus: pertimbangkan disable sementara untuk mencegah
  dampak ke routing protocol (BGP/OSPF) yang bergantung pada interface tersebut


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
| Link down atau error rate tinggi | Serahkan interface + perintah troubleshoot | config_agent |
| Perlu diagnosa mendalam (layer 1/2) | Serahkan data ke diagnose | diagnose_agent |
| Link normal | Tidak perlu handoff | END |
