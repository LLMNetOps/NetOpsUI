---
name: ospf-diagnostics
domain: routing
triggers:
  - OSPF neighbor down
  - adjacency hilang
  - routing OSPF bermasalah
  - OSPF tidak full
  - OSPF state bukan full
  - routing berubah tiba-tiba
  - subnet tidak reachable
tools:
  - get_routing_full
  - get_router_config
  - get_router_log
  - check_reachability
  - run_command
approval_required: false
enabled: true
---

# Diagnosa OSPF Neighbor Down

## Konteks
Gunakan skill ini saat ada laporan OSPF adjacency tidak terbentuk atau neighbor yang
sebelumnya Full tiba-tiba turun ke state lain. Tanda-tanda: beberapa subnet tidak
terjangkau, routing berubah mendadak, atau alert OSPF dari sistem monitoring.

## Prosedur

### Langkah 1: Cek State Neighbor Saat Ini
Gunakan `get_routing_full` pada router yang dilaporkan bermasalah. Perhatikan bagian
OSPF neighbor — catat semua neighbor yang tidak dalam state `Full`. State yang mungkin:
- `Full` → normal
- `2-Way` → neighbor terlihat tapi adjacency tidak terbentuk (umumnya DROTHER)
- `ExStart/Exchange/Loading` → sedang proses naik tapi lambat
- `Init` atau `Down` → masalah serius

### Langkah 2: Verifikasi Konektivitas Layer 3
Ping dari router yang bermasalah ke IP interface neighbor-nya menggunakan `check_reachability`
atau `run_command` dengan `/ping <ip>`.
- Tidak reachable → masalah di layer fisik, VLAN, atau IP routing dasar
- Reachable tapi OSPF tidak Full → masalah konfigurasi OSPF

### Langkah 3: Periksa Konfigurasi OSPF
Ambil konfigurasi OSPF kedua router (yang bermasalah dan neighbor-nya) menggunakan
`get_router_config`. Bandingkan:
- **Area ID** harus identik di kedua sisi
- **Hello interval** dan **dead interval** harus cocok (default: 10s / 40s)
- **Network type** harus sama (broadcast atau point-to-point)
- **Authentication** — key, type (MD5/simple), dan password harus identik

### Langkah 4: Baca Log Router
Ambil log dengan `get_router_log` menggunakan filter topic `ospf` atau `routing`. Cari:
- `neighbor changed state` → kapan terakhir adjacency jatuh dan dari state apa
- `authentication failure` → mismatch key
- `dead timer expired` → hello packet tidak diterima dalam waktu dead interval
- `mtu mismatch` → MTU interface tidak cocok

### Langkah 5: Periksa Interface
Jalankan `run_command` dengan `/interface/print where running=yes` untuk memastikan
interface yang menghubungkan kedua router memang aktif. Interface down = OSPF tidak bisa naik.

## Output yang Diharapkan
Ringkasan yang mencakup:
- Daftar OSPF neighbor yang bermasalah beserta state terakhir dan durasi down
- Penyebab yang paling mungkin berdasarkan log dan config check
- Rekomendasi langkah perbaikan yang konkret (misal: sesuaikan timer, fix authentication)

## Catatan
- RouterOS v7: `/routing/ospf/neighbor/print`
- RouterOS v6: `routing ospf neighbor print`
- OSPF flap berulang (naik-turun berulang) biasanya disebabkan link tidak stabil atau
  CPU tinggi di salah satu router yang menyebabkan hello packet terlambat
- OSPF tidak bisa naik jika ada firewall yang memblokir protokol OSPF (protocol 89)
