---
name: bgp-diagnostics
domain: routing
triggers:
  - BGP down
  - BGP tidak established
  - internet mati
  - uplink putus
  - BGP session drop
  - prefix hilang dari tabel routing
  - internet tidak bisa diakses
tools:
  - get_routing_full
  - get_router_config
  - get_router_log
  - check_reachability
  - run_command
  - get_system_info
approval_required: false
enabled: true
---

# Diagnosa BGP Session Down

## Konteks
Gunakan skill ini saat BGP session ke ISP atau peer putus, ditandai dengan internet tidak
bisa diakses dari kampus, atau ada alert BGP dari sistem monitoring. BGP biasanya hanya
ada di router edge/border, bukan di router gedung.

## Prosedur

### Langkah 1: Identifikasi Router Edge
Dari daftar router (`list_routers`), identifikasi router dengan role `edge` atau `border`.
BGP session biasanya ada di router ini. Jika tidak yakin, tanya operator.

### Langkah 2: Cek Status BGP Session
Gunakan `get_routing_full` pada router edge. Perhatikan bagian BGP peers:
- `Established` → session aktif, tapi mungkin ada masalah prefix
- `Active` → mencoba connect tapi gagal
- `Idle` → tidak mencoba sama sekali (mungkin di-shutdown atau timer cooldown)
- `Connect` → proses TCP sedang berlangsung

### Langkah 3: Verifikasi Konektivitas ke Peer
Ping ke IP BGP peer (ISP) menggunakan `check_reachability` atau `run_command`:
- Tidak reachable → masalah link fisik atau upstream ISP
- Reachable tapi BGP tidak Established → masalah konfigurasi BGP atau firewall

### Langkah 4: Cek Konfigurasi BGP
Ambil config BGP dengan `get_router_config`. Verifikasi:
- **AS Number** — local dan remote AS harus sesuai perjanjian dengan ISP
- **Neighbor IP** — harus IP interface ISP yang benar
- **Authentication password** — harus cocok dengan ISP (jika digunakan)
- **TTL** — eBGP biasanya TTL=1 (direct peer), jika multihop perlu TTL lebih tinggi

### Langkah 5: Analisis Log
Ambil log dengan `get_router_log` filter topic `bgp` atau `routing`. Cari:
- `session closed` → kapan terakhir session jatuh
- `notification sent/received` → error code dari BGP NOTIFICATION (misal: hold timer expired)
- `authentication error` → password mismatch
- `open message error` → AS number atau router-id mismatch

### Langkah 6: Cek Resource Router
Gunakan `get_system_info` untuk cek CPU dan memory. CPU sangat tinggi (> 90%) bisa
menyebabkan BGP keepalive terlambat dan session timeout.

## Output yang Diharapkan
Laporan yang mencakup:
- Status BGP session saat ini (Established/Active/Idle) dan durasi down
- Hasil cek konektivitas ke peer
- Penyebab paling mungkin berdasarkan log (hold timer, authentication, config mismatch)
- Rekomendasi spesifik (misal: "Konfirmasi ulang BGP password dengan tim ISP")

## Catatan
- RouterOS v7: `/routing/bgp/session/print`
- RouterOS v6: `routing bgp peer print`
- BGP hold timer default 90 detik — jika keepalive tidak terkirim dalam 90 detik, session
  jatuh. Penyebab umum: CPU overload atau link intermittent
- Jangan restart BGP session tanpa konfirmasi dari NOC — bisa ada dampak ke routing campus
