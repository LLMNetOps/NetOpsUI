---
name: link-diagnostics
domain: monitoring
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
  - get_bgp_sessions
  - get_ospf_neighbors
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
- `<interface> changed state to down` → kapan pertama kali down

**Hitung frekuensi dari data aktual:**
Hitung total event flapping, tentukan rentang waktu dari timestamp pertama ke terakhir dalam log.
Frekuensi = total_event / jumlah_hari. JANGAN estimasi atau perkirakan — hitung dari data.

**Interpretasi flapping:**
- Flap > 5x/jam → masalah serius (kabel, SFP, port switch)
- Flap saat jam sibuk → kemungkinan congestion menyebabkan reset
- Flap terjadi bersamaan dengan BGP/OSPF state change → root cause link, bukan protocol

### Langkah 3b: Cek BGP/OSPF jika interface adalah uplink routing

**WAJIB** jika nama interface mengandung kata `BGP`, `OSPF`, `uplink`, `backbone`, atau `peer`:

```
get_bgp_sessions(router_name)      # jika BGP
get_ospf_neighbors(router_name)    # jika OSPF
```

Verifikasi:
- Apakah flapping interface menyebabkan session drop?
- Peer siapa yang terdampak? (nama peer harus dari hasil tool — JANGAN tebak)
- Berapa lama session down setiap kali flap?

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

**Status:** ✅ normal · ⚠️ error counter · 🚨 interface down / flapping

## Interface Status

| Interface | Status | rx-error | tx-error | rx-fcs | Flapping | Status |
|-----------|--------|----------|----------|--------|----------|--------|
| ether1 | Up | 0 | 0 | 0 | Tidak | ✅ Normal |
| ether2 | Down | 245 | 12 | 89 | 8x/jam | 🚨 Kritis |

*(Narasi wajib: jelaskan kondisi interface yang bermasalah — rx-fcs error mengindikasikan masalah fisik pada kabel atau konektor, flapping berarti link tidak stabil dan dapat mengganggu routing protocol BGP/OSPF yang bergantung pada interface tersebut, sebutkan dampak konkret ke layanan jaringan. 2–3 kalimat.)*

## Root Cause

[Penjelasan berdasarkan data counter + log — BUKAN asumsi]

## Action Items

1. 🚨 **SEGERA** — [tindakan fisik/konfigurasi mendesak]
2. ⚠️ **PERLU** — [monitoring lanjutan]

*Jika normal: "✅ Tidak ada anomali interface."*

## Catatan
- Error counter terus naik saat monitoring → masalah aktif, bukan historis
- Gunakan `run_command` dengan `/interface/reset-counters <interface>` untuk reset counter
  setelah perbaikan — konfirmasi dulu ke operator
- Masalah fisik (kabel, SFP, port switch) tidak bisa diperbaiki via remote —
  koordinasikan dengan teknisi lapangan
- Untuk interface yang flapping terus: pertimbangkan disable sementara untuk mencegah
  dampak ke routing protocol (BGP/OSPF) yang bergantung pada interface tersebut

## LARANGAN KERAS

- **JANGAN sebutkan nama peer, device, hostname, atau IP** yang tidak ada dalam hasil tool call.
  Jika belum tahu nama peer BGP → jalankan `get_bgp_sessions` dulu. Jika tool gagal → tulis
  "peer tidak dapat dikonfirmasi" bukan nama yang tidak ada datanya.
- **JANGAN estimasi frekuensi** — hitung dari timestamp aktual dalam log.
- **JANGAN tulis rekomendasi handoff dalam prose** — jika kondisi handoff terpenuhi, eksekusi
  dengan return ke supervisor, bukan hanya tulis "serahkan ke X".


## Validasi Mandiri

Sebelum lapor ke operator, pastikan:
- [ ] Data dikumpulkan dari semua sumber relevan
- [ ] Temuan dikonfirmasi dengan minimal 2 data point (bukan hanya 1 tool)
- [ ] Anomali: bandingkan dengan baseline atau history sebelum simpulkan masalah
- [ ] Jika ada kegagalan tool (SSH timeout, error): coba router/interface alternatif dulu

Jika validasi belum lengkap → coba sumber alternatif, baru lapor jika memang tidak bisa resolve.

## Handoff

Handoff harus **dieksekusi** — bukan ditulis dalam teks output. Jika kondisi terpenuhi,
akhiri response dengan satu baris terakhir: `HANDOFF: <nama_agent>` agar supervisor
membaca sinyal ini dan route ke agent yang tepat.

| Kondisi | HANDOFF target |
|---------|---------------|
| Flapping aktif + butuh koordinasi fisik / ganti hardware | `diagnose_agent` |
| Perlu disable interface atau konfigurasi perubahan | `config_agent` |
| Link normal, tidak ada anomali | END (tidak perlu handoff) |
