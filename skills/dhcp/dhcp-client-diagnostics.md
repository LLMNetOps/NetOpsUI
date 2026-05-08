---
name: dhcp-client-diagnostics
domain: dhcp
triggers:
  - client tidak dapat IP
  - DHCP tidak berfungsi
  - no IP address
  - lease gagal
  - perangkat tidak dapat alamat
  - tidak bisa connect DHCP
  - komputer tidak dapat IP
  - laptop tidak dapat IP
tools:
  - search_device
  - get_dhcp_leases
  - get_router_leases
  - get_router_log
  - run_diagnostic
approval_required: false
enabled: true
---

# Diagnosa Client Tidak Mendapat IP dari DHCP

## Konteks
Gunakan skill ini saat ada laporan perangkat (PC, laptop, printer) tidak mendapat IP address
dari DHCP server. Biasanya dipicu oleh keluhan operator seperti "komputer Lab3 tidak bisa
connect", "IP address tidak muncul di perangkat", atau "DHCP error".

## Prosedur

### Langkah 1: Identifikasi Perangkat
Jika diketahui MAC address atau IP lama, gunakan `search_device` untuk menemukan perangkat
di router dan DHCP server mana yang menanganinya. Jika tidak ada info MAC/IP, tanyakan
ke operator: lokasi fisik perangkat (lab, gedung) → gunakan untuk menentukan router terkait.

### Langkah 2: Cek Status Lease
Ambil data lease dari DHCP server yang bertanggung jawab dengan `get_dhcp_leases`.
Interpretasi status:
- `bound` → lease aktif, client seharusnya punya IP — kemungkinan masalah di sisi client
- `waiting` → client sedang mencoba tapi lease belum terbentuk atau sudah expired
- `disabled` → entri di-disable secara manual — perlu di-enable kembali
- tidak ada entri → MAC belum pernah terdaftar, atau pool IP penuh

### Langkah 3: Cek Kapasitas Pool
Dari data lease, hitung jumlah lease aktif vs total. Jika hampir penuh (> 90%):
- Cari lease `waiting` yang sudah lama (MAC tidak aktif) yang aman untuk dibersihkan
- Rekomendasikan perluasan range pool jika memang kurang

### Langkah 4: Baca Log Router
Ambil log router dengan `get_router_log` menggunakan filter topic `dhcp`. Cari pesan error:
- `no leases available` → pool IP habis
- `rejected` → ada firewall atau filter yang memblokir
- `deassigned` → lease dicabut paksa
- `offer` tanpa diikuti `bound` → client menerima offer tapi tidak membalas (masalah client)

### Langkah 5: Verifikasi Konektivitas
Jika ada IP yang seharusnya diberikan, jalankan `run_diagnostic` (ping) dari router ke IP
tersebut. Jika ada reply → kemungkinan IP conflict dengan perangkat lain yang menggunakan
IP statis.

## Output yang Diharapkan
Berikan ringkasan diagnosis yang mencakup:
1. Status lease client saat ini (bound/waiting/disabled/tidak ada)
2. Penyebab masalah yang teridentifikasi secara spesifik
3. Rekomendasi tindakan konkret yang bisa dilakukan operator

Contoh output yang baik:
"Client MAC dc:a6:32:1b:2c:3d tidak mendapat IP di pool `dhcp-lab3-tik`. Pool saat ini
penuh (254/254 entry aktif). Terdapat 12 lease `waiting` berumur > 7 hari yang aman
dihapus. Setelah dibersihkan, client akan mendapat IP secara otomatis."

## Catatan
- RouterOS tidak membedakan "lease expired tapi client masih aktif" dengan "client sudah
  tidak aktif" — keduanya tampil sebagai `waiting`
- Jangan hapus entri `waiting` yang baru (< 1 jam) karena client mungkin sedang rebooting
- Pada ROS v6, perintah DHCP menggunakan format tanpa leading slash
