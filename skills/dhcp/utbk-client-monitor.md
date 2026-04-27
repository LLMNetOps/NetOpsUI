---
name: utbk-client-monitor
domain: dhcp
triggers:
  - monitor UTBK
  - cek client ujian
  - berapa peserta aktif
  - peserta UTBK tidak connect
  - client utbk-os
  - status ujian UTBK
  - monitoring sesi ujian
tools:
  - audit_dhcp
  - get_router_leases
  - get_dhcp_leases
  - search_device
  - get_router_log
approval_required: false
enabled: true
---

# Monitor Client UTBK Selama Sesi Ujian

## Konteks
Gunakan skill ini selama sesi ujian UTBK berlangsung untuk memantau jumlah client ujian
yang terhubung. Client UTBK menggunakan hostname `utbk-os` di DHCP lease. Skill ini
membantu operator mendeteksi client yang putus atau tidak mendapat IP selama ujian.

## Prosedur

### Langkah 1: Hitung Client UTBK Global
Jalankan `audit_dhcp` dan perhatikan kolom `UTBK`. Kolom ini menunjukkan jumlah lease
aktif dengan hostname `utbk-os` per router/server. Jumlahkan untuk total peserta terhubung.

### Langkah 2: Bandingkan dengan Jumlah Peserta Terdaftar
Jika operator menyebutkan jumlah peserta yang seharusnya hadir, bandingkan dengan jumlah
`utbk-os` yang aktif. Selisih berarti ada peserta yang bermasalah.

### Langkah 3: Identifikasi Peserta Bermasalah
Untuk router dengan jumlah UTBK lebih rendah dari yang diharapkan:
- Panggil `get_router_leases` atau `get_dhcp_leases` untuk melihat detail
- Cari lease dengan status `waiting` atau `disabled` yang mungkin milik peserta
- Gunakan `search_device` jika ada MAC address atau IP yang dilaporkan bermasalah

### Langkah 4: Cek Log DHCP
Jika ada peserta yang tidak bisa connect, ambil log router terkait dengan `get_router_log`
dan filter topic `dhcp`. Cari pesan yang berkaitan dengan waktu sesi ujian.

## Output yang Diharapkan
Laporan status real-time yang mencakup:
- Total client `utbk-os` aktif per router dan total keseluruhan
- Persentase keberhasilan (misal: 487/500 peserta = 97.4% terhubung)
- Detail peserta yang bermasalah jika ada (router, server, status lease)
- Rekomendasi tindakan jika ada masalah

## Catatan
- Jalankan setiap 15-30 menit selama sesi ujian berlangsung
- Selama ujian, pastikan tidak ada perubahan konfigurasi DHCP di router terkait
- Jika banyak peserta putus serentak → kemungkinan masalah upstream (switch, uplink)
  bukan DHCP
