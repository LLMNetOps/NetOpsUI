---
name: network-reachability
domain: monitoring
triggers:
  - router tidak bisa dihubungi
  - router down
  - ping gagal
  - router tidak merespons
  - SSH timeout
  - tidak bisa akses router
  - router mati
  - router offline
tools:
  - check_reachability
  - check_ssh_access
  - get_system_info
  - run_command
  - get_router_log
approval_required: false
enabled: true
---

# Investigasi Router Tidak Dapat Dihubungi

## Konteks
Gunakan skill ini saat sebuah router tidak merespons ping atau SSH. Bisa disebabkan oleh
router mati, link putus, IP berubah, atau firewall yang memblokir akses manajemen.

## Prosedur

### Langkah 1: Konfirmasi Status Reachability
Gunakan `check_reachability` pada router yang dilaporkan. Catat apakah ping benar-benar
gagal atau hanya lambat (high latency).

**Jika ping berhasil (ICMP ok) tetapi SSH gagal:** Ini berbeda dari "router down".
Gunakan `check_ssh_access` untuk diagnosa SSH:
- ICMP ✓, TCP:22 ✓, SSH banner ✗ → **SSH ACL**: router membatasi SSH dari sumber IP ini.
  Solusi: tambahkan IP sumber ke `/ip/ssh` allowed-addresses di router tersebut.
- ICMP ✓, TCP:22 timeout → **Firewall DROP**: port 22 diblokir dari sumber ini.
- ICMP ✓, TCP:22 refused → **SSH nonaktif** atau firewall REJECT.

### Langkah 2: Cek Router Tetangga
Jika ada router tetangga (uplink atau same-segment), cek reachability router tetangga:
- Tetangga reachable → masalah mungkin di router itu sendiri (crash, reboot, config)
- Tetangga tidak reachable → kemungkinan masalah link atau gedung tanpa listrik

### Langkah 3: Cek dari Router Terdekat
Jika ada router lain yang terhubung langsung, gunakan `run_command` untuk ping dari
router tersebut ke IP router yang bermasalah:
```
/ping <ip-router-bermasalah> count=5
```
Ini membantu membedakan masalah di jalur manajemen vs jalur data.

### Langkah 4: Estimasi Waktu Down
Jika ada router lain yang berbagi log atau ada laporan sebelumnya, coba cek terakhir
kali router ini terlihat aktif. Gunakan `get_router_log` pada router tetangga dan cari
pesan yang menyebut router bermasalah.

### Langkah 5: Tindakan yang Direkomendasikan
Berikan panduan langkah fisik yang perlu dilakukan oleh teknisi:
- Cek lampu status di router (power, interface)
- Cek kabel power dan kabel uplink
- Jika router RB (RouterBoard), cek apakah ada suara beep saat boot
- Coba akses via console port jika available

## Output yang Diharapkan
Laporan investigasi yang mencakup:
- Konfirmasi status reachability (down sejak kapan jika diketahui)
- Router tetangga yang masih aktif dan hasilnya
- Kemungkinan penyebab (hardware failure, link putus, power, config)
- Panduan tindakan fisik untuk teknisi lapangan

## Catatan
- Jika router tidak reachable tapi layanan di belakangnya masih jalan (user bisa internet),
  kemungkinan hanya akses manajemen yang terblokir — bukan darurat penuh
- Catat waktu down untuk keperluan SLA dan laporan insiden
- Eskalasikan ke vendor/NOC jika router tetap tidak reachable > 30 menit tanpa penyebab jelas
