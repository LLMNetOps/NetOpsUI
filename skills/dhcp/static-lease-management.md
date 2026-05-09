---
name: static-lease-management
domain: dhcp
triggers:
  - IP reservation
  - static lease
  - reservasi IP
  - bind MAC address
  - server dapat IP berubah-ubah
  - printer selalu ganti IP
  - IP tetap untuk perangkat
  - tambah static lease
  - hapus static lease
  - cek static lease
tools:
  - run_command
  - get_dhcp_leases
  - get_router_leases
  - backup_router_config
approval_required: true
enabled: true
---

# Manajemen Static Lease DHCP

## Konteks
Gunakan skill ini untuk mengelola IP reservation (static lease) di DHCP server MikroTik.
Static lease memastikan perangkat tertentu selalu mendapatkan IP yang sama berdasarkan
MAC address. Digunakan untuk: server, printer jaringan, access point, CCTV, dan perangkat
infrastruktur lainnya.

**Perubahan DHCP memerlukan persetujuan operator.**

## Prosedur Melihat Static Lease

### Cek Semua Static Lease
```
/ip/dhcp-server/lease/print where type=static
```

### Cek Static Lease per Server DHCP
Gunakan `get_dhcp_leases(router_name)` atau:
```
/ip/dhcp-server/lease/print where server=<dhcp-server-name>
```

### Cari Perangkat Berdasarkan IP atau MAC
```
/ip/dhcp-server/lease/print where address=192.168.1.100
/ip/dhcp-server/lease/print where mac-address=AA:BB:CC:DD:EE:FF
```

## Prosedur Menambah Static Lease

### Langkah 1: Identifikasi Informasi Perangkat
Kumpulkan dari operator:
- MAC address perangkat (format: AA:BB:CC:DD:EE:FF)
- IP yang diinginkan (harus dalam range pool DHCP, tapi di luar dynamic range)
- Nama/keterangan perangkat (untuk comment)
- Di DHCP server mana (router dan nama server)

### Langkah 2: Verifikasi IP Belum Dipakai
```
/ip/dhcp-server/lease/print where address=<ip-yang-diinginkan>
```
Jika sudah ada lease lain → cari IP lain atau hapus lease lama dulu.

Cek juga tidak ada IP static di `/ip/address` yang konflik:
```
/ip/address/print where address~"<ip-yang-diinginkan>"
```

### Langkah 3: Backup Config
Jalankan backup sebelum perubahan DHCP.

### Langkah 4: Tambah Static Lease
```
/ip/dhcp-server/lease/add
  mac-address=AA:BB:CC:DD:EE:FF
  address=192.168.1.100
  server=<dhcp-server-name>
  comment="PRINTER-FILKOM-LT2"
```

Atau jika perangkat sudah punya dynamic lease dan ingin dijadikan static:
```
/ip/dhcp-server/lease/make-static [find mac-address=AA:BB:CC:DD:EE:FF]
```
Kemudian update comment-nya.

### Langkah 5: Verifikasi
```
/ip/dhcp-server/lease/print where mac-address=AA:BB:CC:DD:EE:FF
```
Pastikan `type=static` dan `address` sesuai.

### Langkah 6: Test Perangkat
Minta perangkat melakukan DHCP renew (disconnect-reconnect Wi-Fi, atau `ipconfig /release && ipconfig /renew`).
Verifikasi perangkat mendapat IP yang benar:
```
/ip/dhcp-server/lease/print where mac-address=AA:BB:CC:DD:EE:FF
```
Kolom `status=bound` → perangkat sudah aktif dengan IP tersebut.

## Prosedur Mengubah Static Lease

```
/ip/dhcp-server/lease/set [find mac-address=AA:BB:CC:DD:EE:FF] address=192.168.1.101
```

Setelah mengubah, perangkat perlu renew DHCP untuk mendapat IP baru.

## Prosedur Menghapus Static Lease

```
/ip/dhcp-server/lease/remove [find mac-address=AA:BB:CC:DD:EE:FF]
```

Atau berdasarkan IP:
```
/ip/dhcp-server/lease/remove [find address=192.168.1.100]
```

Setelah dihapus, perangkat akan mendapat IP dinamis dari pool saat berikutnya request DHCP.

## Troubleshooting

### Perangkat Tidak Mendapat IP yang Benar
1. Verifikasi MAC address benar (cek di sisi perangkat: `ipconfig /all` di Windows,
   `ip link show` di Linux)
2. Pastikan static lease aktif (`/ip/dhcp-server/lease/print where mac-address=...`)
3. Cek apakah perangkat masih punya lease lama yang bound:
   ```
   /ip/dhcp-server/lease/print where mac-address=<mac>
   ```
   Jika ada dua entry (lama + baru) → hapus yang lama

### IP Sudah Dipakai Perangkat Lain (Conflict)
```
/ip/dhcp-server/lease/print where address=<ip>
```
Identifikasi siapa yang pakai IP tersebut sekarang. Jika lease dinamis, bisa dihapus
setelah koordinasi. Jika static lain → pilih IP berbeda.

### DHCP Server Tidak Ditemukan
```
/ip/dhcp-server/print
```
Catat nama server yang tersedia di router tersebut.

## Output yang Diharapkan
- Konfirmasi static lease berhasil dibuat/diubah/dihapus
- Output print lease yang baru untuk verifikasi
- Status perangkat setelah renew (bound/waiting)

## Catatan
- MAC address bersifat unik per perangkat — satu MAC = satu static lease
- IP untuk static lease sebaiknya di luar range pool dinamis untuk menghindari konflik.
  Contoh: jika pool 192.168.1.100-192.168.1.200, gunakan 192.168.1.10-192.168.1.99 untuk static
- Dokumentasikan semua static lease: siapa yang minta, perangkat apa, lokasi fisik
- Static lease DHCP tidak sama dengan IP static yang dikonfigurasi langsung di perangkat —
  keduanya bisa dikombinasikan tapi harus konsisten
