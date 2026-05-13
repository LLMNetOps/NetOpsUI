---
name: mtu-mismatch-diagnostics
domain: monitoring
triggers:
  - MTU mismatch
  - MTU tidak cocok
  - duplex mismatch
  - packet drop karena MTU
  - interface error MTU
  - congestion karena MTU
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
- Packet drop tinggi di interface tertentu
- Duplex mismatch antara dua perangkat
- Error TX/RX yang tidak wajar
- Latensi tinggi di link tertentu
- Pesan "fragmentation needed" di log

## Prosedur

### Langkah 1: Ambil statistik interface
Jalankan `get_interface_stats(router_name)` untuk semua router yang dicurigai.

Periksa kolom berikut di output:
- `TX error` dan `RX error` — jika > 0, kemungkinan MTU/duplex mismatch
- `TX drop` dan `RX drop` — jika tinggi, cek MTU
- `status` — pastikan interface UP
- `speed` dan `duplex` — cek apakah match antara kedua sisi

**Contoh output yang bermasalah:**
```
  Interface    TX error  RX error  TX drop  RX drop  Status  Speed  Duplex
  ether1      1523      1489      0        0        up      1000   full
  ether2       0         0         0        0        up      1000   half
```
→ Duplex mismatch: satu sisi full, satu sisi half.

### Langkah 2: Cek traffic summary
Jalankan `get_traffic_summary(router_name)` untuk melihat pola drop.

Cari interface dengan:
- `TX drop` atau `RX drop` > 0
- `TX error` atau `RX error` > 0

**Contoh output:**
```
  Interface    TX bytes  RX bytes  TX pkts  RX pkts  TX drop  RX drop  TX err  RX err
  ether1    1.2T      890G      900M     700M       0        0        1523    1489
  ether2    1.1T      890G      850M     700M       0        0        0       0
```
→ ether1 punya error, ether2 tidak. Kemungkinan mismatch.

### Langkah 3: Cek konfigurasi MTU
Jalankan `run_command` dengan perintah berikut (sesuaikan versi RouterOS):

- RouterOS v7: `/ip/interface/print where name=<interface>`
- RouterOS v6: `/interface print where name=<interface>`

Cari kolom `MTU` di output.

**Contoh output:**
```
NAME     MTU  TYPE
ether1  1500  ethernet
ether2  9000  ethernet
```
→ ether1 MTU=1500, ether2 MTU=9000. Jika ada VLAN/jump router di tengah, pastikan semua interface di path punya MTU yang konsisten.

### Langkah 4: Cek log untuk fragmentation
Jalankan `get_router_log(router_name, topic="error", lines=50)`.

Cari kata kunci:
- `fragmentation needed`
- `too big`
- `MTU exceeded`
- `blackhole`

**Contoh log:**
```
2026-04-25 10:23:45 error: IP: packet from 10.0.0.5 to 192.168.1.100: fragmentation needed and DF bit set
```
→ Konfirmasi MTU mismatch.

### Langkah 5: Verifikasi dengan ping + DF bit
Jalankan `run_command` dengan perintah RouterOS:
```
/ping <target> do-not-fragment=yes size=1472
```
- `do-not-fragment=yes` = set DF (Don't Fragment) bit
- `size=1472` = payload 1472 bytes; total frame = 1472 + 20 IP header + 8 ICMP header = 1500 bytes (tepat di batas MTU ethernet standar)

Jika ping gagal atau terpotong, berarti MTU path < 1500.

### Langkah 6: Rekomendasi perbaikan

**Jika duplex mismatch:**
- Pastikan kedua sisi punya `duplex=full`
- Sampaikan ke operator untuk dieksekusi via `run_command_write` (butuh approval):
  ```
  /interface set <interface> duplex=full speed=1000
  ```

**Jika MTU mismatch:**
- Set MTU yang konsisten di semua interface di path
- Sampaikan ke operator untuk dieksekusi via `run_command_write` (butuh approval):
  - Untuk link Gigabit dengan jumbo frame: `/interface set <interface> mtu=9000`
  - Untuk link normal: `/interface set <interface> mtu=1500`

**Jika fragmentation needed:**
- Cek apakah ada firewall rule yang set DF bit
- Atau kurangi MTU di interface yang bermasalah

> **Catatan:** Semua perintah write di atas memerlukan approval operator. Jangan eksekusi langsung — sampaikan rekomendasi dan tunggu konfirmasi.

## Output yang Diharapkan
Laporan harus berisi:
1. Tabel interface dengan kolom: Interface, TX error, RX error, TX drop, RX drop, Status, Speed, Duplex
2. Tabel konfigurasi MTU per interface
3. Daftar log error yang relevan
4. Hasil ping test dengan DF bit
5. Rekomendasi perbaikan dengan perintah RouterOS

## Catatan
- MTU default ethernet = 1500
- Jumbo frame = 9000 (biasanya untuk link internal datacenter)
- Pastikan semua router di path punya MTU yang sama
- Duplex mismatch menyebabkan error tinggi dan packet loss
- VDSL/DSL biasanya harus MTU=1492 (untuk PPPoE)
