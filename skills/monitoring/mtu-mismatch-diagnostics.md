---
name: mtu-mismatch-diagnostics
domain: monitoring
triggers:
  - MTU mismatch
  - MTU tidak cocok
  - packet drop MTU
  - interface MTU error
  - fragmentation needed
  - DF flag drop
  - ICMP fragment needed
tools:
  - get_interface_stats
  - get_traffic_summary
  - get_router_log
  - run_command
enabled: true
approval_required: false
---

## Konteks
Skill ini digunakan saat muncul gejala:
- Packet drop di interface tertentu
- Error "fragmentation needed and DF set"
- ICMP type 3 code 4 (port unreachable/fragmentation needed)
- Latensi tinggi karena fragmentation
- Log menunjukkan MTU issue

## Prosedur

### Langkah 1: Ambil Statistik Interface
Jalankan `get_interface_stats(router_name)` untuk semua router.

Cari baris dengan:
- `TX errors > 0` atau `RX errors > 0`
- `TX drop > 0` atau `RX drop > 0`
- `status` = `down` atau `error-down`

**Interpretasi:**
- `TX errors` = error transmit (biasanya duplex mismatch atau MTU issue)
- `RX errors` = error receive (biasanya kabel rusak atau MTU issue)
- `TX drop` = packet dropped saat transmit (bisa MTU mismatch)
- `RX drop` = packet dropped saat receive

### Langkah 2: Cek Traffic Summary
Jalankan `get_traffic_summary(router_name)` untuk melihat:
- Total TX/RX bytes dan packets
- Jumlah drops dan errors per interface

**Interpretasi:**
- Jika `drops` tinggi tapi `errors` rendah → kemungkinan MTU mismatch
- Jika `errors` tinggi → kemungkinan kabel rusak atau duplex mismatch

### Langkah 3: Cek Log Router
Jalankan `get_router_log(router_name, topic="interface", lines=50)` atau `topic="error", lines=50`.

Cari pesan:
- `ICMP: need to fragment`
- `ICMP: fragmentation needed and DF set`
- `MTU: mismatch detected`
- `interface error`
- `packet dropped due to MTU`

**Interpretasi:**
- Pesan `ICMP: need to fragment` = ada packet dengan DF flag yang tidak bisa di-fragment
- Pesan `fragmentation needed and DF set` = klasik MTU mismatch
- Pesan `ICMP: fragmentation needed` = target menolak fragmentasi

### Langkah 4: Cek Konfigurasi MTU
Jalankan `run_command_all(command="/interface/print show")` untuk melihat MTU semua interface.

Cari perbedaan MTU:
- Interface yang terhubung ke peer dengan MTU berbeda
- Interface dengan MTU default (1500) yang terhubung ke peer dengan MTU lebih kecil
- Interface dengan MTU custom yang tidak sinkron dengan peer

**Perintah cek MTU detail:**
```
/interface/print show
/ip/firewall/mangle print where action=mark-connection
```

### Langkah 5: Cek Firewall Mangle DF Flag
Jalankan `run_command_all(command="/ip/firewall/mangle print where action=mark-connection")`.

Cari rule dengan `mtu-discovery=yes` atau `df=yes`.

**Interpretasi:**
- `mtu-discovery=yes` = router akan mengirim ICMP untuk negosiasi MTU
- `df=yes` = set DF flag pada packet
- Jika ada packet dengan DF flag dan MTU mismatch → packet akan dropped

### Langkah 6: Identifikasi Peer dengan MTU Berbeda
Dari hasil Langkah 4, identifikasi interface yang terhubung ke peer lain.

Cek dokumentasi atau hubungi admin peer untuk MTU mereka.

**Contoh:**
- Interface eth1 MTU=1500 terhubung ke peer dengan MTU=9000 → mismatch
- Interface VLAN MTU=1500 terhubung ke peer dengan MTU=1400 → mismatch

### Langkah 7: Verifikasi dengan Ping Test
Jalankan `run_command(command="/tool/finger print")` atau gunakan ping test manual.

**Perintah ping test MTU:**
```
/ping/remote address=<peer-ip> size=1472 df=yes
/ping/remote address=<peer-ip> size=1480 df=yes
```

Jika ping size=1472 berhasil tapi size=1480 gagal → MTU max = 1472

## Output yang Diharapkan

Laporan harus berisi:

### Tabel 1: Statistik Interface dengan Error
| Router | Interface | TX Errors | RX Errors | TX Drop | RX Drop | Status |
|--------|-----------|-----------|-----------|---------|---------|--------|

### Tabel 2: MTU per Interface
| Router | Interface | MTU | MTU-P2P | Status |
|--------|-----------|-----|---------|--------|

### Tabel 3: Log MTU Events
| Router | Timestamp | Message | Severity |
|--------|-----------|---------|----------|

### Ringkasan
- Jumlah interface dengan errors
- Jumlah interface dengan drops
- Interface yang teridentifikasi MTU mismatch
- Peer yang perlu disesuaikan MTU-nya

### Rekomendasi
1. Sesuaikan MTU di kedua sisi peer
2. Matikan DF flag jika tidak diperlukan
3. Aktifkan `mtu-discovery=yes` untuk negosiasi otomatis
4. Tambahkan firewall mangle untuk handle fragmentation

## Catatan

### RouterOS v6 vs v7
- v6: `/interface/ethernet set [find] mtu=1500`
- v7: `/interface/ethernet set [find] mtu=1500` (sama)
- v7.15+: ada `mtu-discovery` di `/ip/firewall/mangle`

### MTU Standar
- Ethernet default: 1500 bytes
- Jumbo frame: 9000 bytes (harus sinkron kedua sisi)
- PPPoE overhead: -8 bytes
- VLAN tag: -4 bytes
- IP header: 20 bytes (IPv4) atau 40 bytes (IPv6)
- TCP/UDP header: 20-60 bytes

### Edge Cases
- Interface bridge: MTU harus sama semua member
- VLAN interface: MTU harus diperhitungkan VLAN tag
- PPPoE: kurangi 8 bytes dari MTU fisik
- Wireguard: kurangi overhead Wireguard dari MTU

### Perintah Perbaikan
```
# Set MTU sama di kedua sisi
/interface/ethernet set [find name=eth1] mtu=1500
/interface/vlan set [find name=vlan1] mtu=1500

# Matikan DF flag (opsional)
/ip/firewall/mangle remove [find df=yes]

# Aktifkan MTU discovery
/ip/firewall/mangle add chain=forward action=mark-connection mtu-discovery=yes
```