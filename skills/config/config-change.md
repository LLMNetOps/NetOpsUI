---
name: config-change
domain: config
triggers:
  - ubah konfigurasi router
  - ganti IP router
  - ubah password
  - rename interface
  - nonaktifkan layanan
  - aktifkan fitur
  - ubah NTP server
  - set konfigurasi
  - konfigurasi router
  - perubahan config
tools:
  - backup_router_config
  - run_command
  - check_reachability
  - get_router_log
  - list_backups
approval_required: true
enabled: true
---

# Prosedur Perubahan Konfigurasi Router yang Aman

## Konteks
Gunakan skill ini untuk membuat perubahan konfigurasi terencana di router kampus.
Prosedur ini memastikan setiap perubahan dilakukan dengan backup terlebih dahulu
dan dapat di-rollback jika terjadi masalah.

**PENTING:** Perubahan konfigurasi memerlukan persetujuan operator. Operasi yang
berisiko tinggi (ubah IP manajemen, ubah routing, disable interface) wajib dikerjakan
di luar jam sibuk dan dengan teknisi standby.

## Klasifikasi Risiko Perubahan

| Level | Jenis Perubahan | Persyaratan |
|-------|----------------|-------------|
| LOW | Ubah comment, tambah user, ubah NTP | Backup + verifikasi |
| MEDIUM | Ubah firewall rule, tambah static route | Backup + window maintenance |
| HIGH | Ubah IP manajemen, ubah routing protocol | Backup + konsol akses + approval |
| CRITICAL | Ubah BGP policy, ganti firmware | NOC approval + downtime window |

## Prosedur Perubahan

### Langkah 0: Penilaian Risiko
Sebelum mulai, tanyakan ke operator:
1. Apa yang akan diubah dan di router mana?
2. Jam berapa dilakukan (hindari jam sibuk: 08:00-16:00)?
3. Apakah ada teknisi yang bisa akses konsol/fisik jika router tidak bisa diakses?
4. Apa dampak jika perubahan gagal?

Jika perubahan HIGH/CRITICAL dan tidak ada akses konsol standby → tunda dulu.

### Langkah 1: Backup Konfigurasi
Jalankan `backup_router_config(router_name)` sebelum perubahan apapun.
Catat nama file backup — dibutuhkan jika perlu rollback.

Konfirmasi ke operator: "Backup tersimpan di `backups/<router>/<timestamp>.rsc`. Lanjut?"

### Langkah 2: Dokumentasikan Rencana Perubahan
Sebelum eksekusi, jelaskan ke operator secara eksplisit:
- Perintah yang akan dijalankan (spesifik)
- Apa yang akan berubah
- Bagaimana cara verifikasi bahwa perubahan berhasil
- Bagaimana cara rollback jika gagal

Contoh:
```
Rencana: Ganti NTP server GATE-X
Perintah: /system/ntp/client/set servers=ntp.ugm.ac.id
Verifikasi: /system/ntp/client/print → cek synced=yes
Rollback: /system/ntp/client/set servers=<server-lama>
```

### Langkah 3: Eksekusi Perubahan
Gunakan `run_command(router_name, "<perintah>")`.

**Prinsip eksekusi aman:**
- Ubah satu hal sekaligus, bukan batch banyak perubahan sekaligus
- Tunggu konfirmasi setiap perubahan sebelum lanjut ke berikutnya
- Jika perintah menyebabkan timeout/disconnect → jangan panik, tunggu 30 detik

**Perubahan yang bisa memutus koneksi sementara:**
- Ubah IP interface manajemen
- Restart layanan SSH
- Ubah firewall rule yang memblokir source IP kita

Untuk perubahan ini, gunakan `/system/scheduler` untuk jadwalkan rollback otomatis:
```
/system/scheduler/add name=rollback-safety interval=5m
  on-event="/ip/address/set ..."
```
Hapus scheduler ini setelah konfirmasi perubahan berhasil.

### Langkah 4: Verifikasi Segera
Dalam 60 detik setelah perubahan:
1. Cek reachability router dengan `check_reachability(router_name)`
2. Verifikasi perubahan diterapkan dengan benar:
   ```
   /ip/address/print   ← jika ubah IP
   /system/ntp/client/print   ← jika ubah NTP
   /ip/firewall/filter/print   ← jika ubah firewall
   ```
3. Cek log singkat untuk error: `get_router_log(router_name, lines=10)`

### Langkah 5: Konfirmasi atau Rollback
**Jika berhasil:** Konfirmasi ke operator, hapus rollback scheduler jika ada.

**Jika gagal atau ada masalah baru:**
1. Jangan tunggu lama — rollback segera
2. Gunakan `run_command` untuk mengembalikan konfigurasi ke nilai sebelumnya
3. Atau import backup: `/import file=<nama-backup>`
4. Verifikasi pasca rollback: cek reachability dan fungsionalitas kembali normal

## Perubahan yang Umum Dilakukan

### Ganti Password User
```
/user/set <nama-user> password=<password-baru>
```
Lakukan satu router dulu, verifikasi login berhasil sebelum lanjut ke router lain.

### Tambah/Hapus User
```
/user/add name=netops2 group=full address=10.0.0.0/8 password=<pass>
/user/remove <nama-user>
```

### Disable Layanan Tidak Dipakai
```
/ip/service/disable [find name=telnet]
/ip/service/disable [find name=ftp]
```

### Update NTP Server
```
/system/ntp/client/set servers=ntp.kampus.ac.id
```

### Tambah/Ubah DNS
```
/ip/dns/set servers=8.8.8.8,8.8.4.4
```

## Output yang Diharapkan
- Konfirmasi perubahan berhasil diterapkan
- Output verifikasi (print perintah terkait)
- Nama file backup yang dibuat sebelum perubahan
- Status: berhasil / rollback dilakukan

## Catatan
- Simpan semua perubahan ke log perubahan untuk audit trail
- Perubahan yang mempengaruhi BGP/OSPF harus dikoordinasikan dengan NOC
- Jika router tidak bisa diakses setelah perubahan → informasikan ke operator untuk
  akses fisik/konsol segera — jangan tunda
