---
name: network-traffic-analysis
domain: monitoring
triggers:
  - analisis traffic jaringan
  - cek traffic router
  - bandwidth usage
  - siapa yang pakai bandwidth terbanyak
  - top talkers
  - traffic spike
  - utilisasi bandwidth
  - queue drop
  - cek antrian router
  - traffic semua router
  - interface traffic
  - traffic realtime
tools:
  - list_routers
  - get_interface_traffic
  - get_traffic_summary
  - get_top_talkers
  - get_queue_stats
  - get_traffic_all
  - get_top_interfaces_all
  - get_current_time
approval_required: false
enabled: true
---

# Analisis Traffic Jaringan

## Konteks
Gunakan skill ini untuk memantau dan menganalisis utilisasi bandwidth jaringan kampus.
Cocok untuk investigasi traffic spike, identifikasi top talkers, analisis queue drop,
dan laporan utilisasi bandwidth harian atau mingguan.

## Panduan Penggunaan Tool

### Top N Interface Lintas Semua Router
**GUNAKAN INI untuk permintaan "top 10/20 interface dengan traffic tertinggi".**
```
get_top_interfaces_all(limit=10)
```
Tool ini query semua router secara paralel, parse data interface, dan return tabel
interface terurut dari RX tertinggi lintas seluruh kampus. Satu tool call sudah cukup.

Output contoh:
```
Top 10 Interface — seluruh kampus (18 router)
Berhasil: 14 router  |  Gagal: 4 router
────────────────────────────────────────────────────────────────────────
#    Router                 Interface                    RX        Keterangan
────────────────────────────────────────────────────────────────────────
1    GATE-IDREN-UB          ether1-idren              14.8 GB  upstream IDREN
2    ROUTER-REKTORAT        sfp1-backbone              8.2 GB
...
```

### Gambaran Umum Semua Router
Gunakan `get_traffic_all` untuk snapshot ringkas semua router (output per-router max 200 char).
Cocok untuk deteksi anomali cepat, BUKAN untuk ranking interface.

### Per Router Spesifik
- `get_interface_traffic(router_name)` — semua interface satu router, diurutkan RX tertinggi
- `get_traffic_summary(router_name)` — ringkasan TX/RX semua interface (raw format)
- `get_top_talkers(router_name)` — IP dengan konsumsi bandwidth tertinggi
- `get_queue_stats(router_name)` — statistik queue: drop count, bytes

### Identifikasi Anomali Traffic
1. Jalankan `get_top_interfaces_all(limit=10)` untuk lihat interface tersibuk
2. Router dengan interface RX sangat tinggi → investigasi lebih lanjut dengan `get_traffic_summary`
3. `get_top_talkers` untuk identifikasi sumber traffic per router
4. `get_queue_stats` untuk cek apakah ada congestion (drop count tinggi)

## Interpretasi Hasil

- **TX/RX rate tinggi** tapi queue drop = 0 → kapasitas masih cukup, traffic normal tinggi
- **Queue drop > 0** → congestion, perlu evaluasi bandwidth atau QoS policy
- **Top talker dari IP internal** → investigasi aktivitas pengguna
- **Top talker dari IP eksternal** → kemungkinan download massal atau serangan


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
| Traffic anomali — perlu QoS atau rate-limit | Serahkan interface + rekomendasi | config_agent |
| Perlu laporan traffic | Serahkan data analisis | document_agent |
| Tidak ada anomali | Tidak perlu handoff | END |
