---
name: static-route-management
domain: routing
triggers:
  - tambah static route
  - hapus static route
  - cek routing table
  - routing tidak lewat jalur yang benar
  - tambahkan rute ke subnet
  - route tidak ada
  - nexthop salah
  - static route
tools:
  - run_command
  - get_routing_full
  - check_reachability
  - backup_router_config
approval_required: true
enabled: true
---

# Manajemen Static Route MikroTik

## Konteks
Gunakan skill ini untuk mengelola static route di router MikroTik kampus:
menambah, menghapus, memverifikasi static route, dan melakukan troubleshooting
ketika trafik tidak lewat jalur yang diinginkan.

**PENTING:** Perubahan routing memerlukan persetujuan operator. Kesalahan static
route bisa menyebabkan network outage atau routing loop.

## Prosedur Verifikasi Routing Table

### Cek Routing Table Aktif
```
/ip/route/print where active=yes
```
Atau gunakan `get_routing_full(router_name)` untuk view lengkap termasuk routing yang
dihasilkan oleh BGP/OSPF.

### Cek Route ke Destination Tertentu
```
/ip/route/print where dst-address~"10.34."
```
Atau cek nexthop aktif untuk subnet tertentu:
```
/ip/route/check 10.34.0.0
```

### Interpretasi Output Route
```
# Flags: X - disabled, A - active, D - dynamic, C - connect, S - static
# Dst-Address    Pref-Src     Gateway      Distance
  A S 0.0.0.0/0               203.0.113.1  1
  A C 10.34.0.0/16  10.34.0.1              0
  A D 192.168.1.0/24          10.34.0.254  20    ← dari OSPF/BGP
```
- `A S` = active static route — sedang dipakai
- `S` saja (tanpa A) = static route tapi tidak aktif (gateway unreachable atau ada route lain lebih baik)
- `D` = dynamic route (dari routing protocol)

## Prosedur Menambah Static Route

### Langkah 1: Backup Config
Jalankan backup sebelum perubahan routing. Catat nama file backup.

### Langkah 2: Verifikasi Nexthop
Pastikan gateway yang akan dipakai bisa dijangkau:
```
/ping 10.1.0.1 count=3
```
Static route dengan gateway yang unreachable tidak akan aktif.

### Langkah 3: Cek Apakah Route Sudah Ada
```
/ip/route/print where dst-address="10.34.5.0/24"
```
Jika sudah ada — jangan dobel. Identifikasi apakah perlu update atau memang beda jalur.

### Langkah 4: Tambah Route
```
/ip/route/add dst-address=10.34.5.0/24 gateway=10.1.0.1 comment="ke-FILKOM-via-core"
```

Parameter penting:
- `distance` — default 1 untuk static. Naikkan (misal 10) jika ini backup route
- `comment` — wajib isi untuk dokumentasi: tujuan dan alasan
- `routing-table` — isi jika menggunakan VRF/policy routing

### Langkah 5: Verifikasi Route Aktif
```
/ip/route/print where dst-address="10.34.5.0/24"
```
Pastikan flag `A` (active) muncul. Jika tidak aktif → cek gateway reachability.

### Langkah 6: Test Reachability
Gunakan `check_reachability` atau `run_command` dengan ping ke host di subnet tujuan
untuk memastikan routing berfungsi end-to-end.

## Prosedur Menghapus Static Route

### Langkah 1: Identifikasi Route yang Akan Dihapus
```
/ip/route/print where dst-address="10.34.5.0/24"
```
Catat nomor index route (angka di kolom pertama).

### Langkah 2: Konfirmasi dengan Operator
Jelaskan: route apa yang akan dihapus, apa dampaknya (subnet mana yang tidak bisa diakses).

### Langkah 3: Hapus Route
```
/ip/route/remove numbers=<index>
```

### Langkah 4: Verifikasi
Pastikan tidak ada route aktif ke subnet tersebut lagi (kecuali jika ada route dinamis
dari BGP/OSPF yang menggantikan):
```
/ip/route/print where dst-address="10.34.5.0/24"
```

## Troubleshooting: Trafik Tidak Lewat Jalur yang Benar

### Identifikasi Route yang Dipakai
```
/ip/route/print where active=yes dst-address~"<subnet>"
```

**Route yang dipakai = route dengan distance terkecil + active.**

Jika ada konflik antara static route dan route dinamis:
- Static route default distance=1
- BGP eBGP default distance=20
- OSPF default distance=110
- Static dengan distance lebih kecil → mengalahkan protokol dinamis

### Cek Routing untuk Source Address Tertentu
```
/tool/traceroute address=8.8.8.8 src-address=10.34.0.10
```

### Matikan Sementara Static Route (Tanpa Menghapus)
```
/ip/route/disable numbers=<index>
```
Berguna untuk testing — biarkan routing dinamis mengambil alih sementara.

## Output yang Diharapkan
- Konfirmasi route berhasil ditambah/dihapus
- Tabel routing aktif untuk subnet yang diubah
- Hasil ping/reachability test setelah perubahan
- Nomor backup file sebelum perubahan

## Catatan
- Selalu backup sebelum mengubah routing di gateway utama
- Static route tanpa comment tidak akan diterima — wajib isi alasan
- Untuk routing policy (load balancing, failover): gunakan `routing-table` dan rule
  di `/routing/rule` — lebih kompleks, konsultasikan ke NOC pusat
- Perubahan routing di GATE-IDREN atau router border — wajib koordinasi dengan NOC IDREN
