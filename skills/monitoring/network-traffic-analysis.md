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

### Gambaran Umum Semua Router
Gunakan `get_traffic_all` untuk mendapat snapshot traffic dari semua router sekaligus.
Efisien untuk laporan harian atau deteksi anomali cepat.

### Per Router
- `get_traffic_summary` — ringkasan TX/RX semua interface di satu router
- `get_interface_traffic` — traffic realtime per interface spesifik
- `get_top_talkers` — IP dengan konsumsi bandwidth tertinggi (via firewall connections)
- `get_queue_stats` — statistik queue: byte count, packet count, drop count

### Identifikasi Anomali Traffic
1. Jalankan `get_traffic_all` untuk baseline semua router
2. Router dengan TX/RX rate abnormal tinggi → investigasi lebih lanjut
3. `get_top_talkers` untuk identifikasi sumber traffic
4. `get_queue_stats` untuk cek apakah ada congestion (drop count tinggi)

## Interpretasi Hasil

- **TX/RX rate tinggi** tapi queue drop = 0 → kapasitas masih cukup, traffic normal tinggi
- **Queue drop > 0** → congestion, perlu evaluasi bandwidth atau QoS policy
- **Top talker dari IP internal** → investigasi aktivitas pengguna
- **Top talker dari IP eksternal** → kemungkinan download massal atau serangan
