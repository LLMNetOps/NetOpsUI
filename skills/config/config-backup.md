---
name: config-backup
domain: config
triggers:
  - backup konfigurasi
  - simpan config router
  - backup config
  - export konfigurasi
  - backup sebelum perubahan
  - config backup
  - simpan konfigurasi
  - rollback config
  - kembalikan konfigurasi
  - restore config
tools:
  - backup_router_config
  - list_backups
  - diff_config
  - run_command
approval_required: true
enabled: true
---

# Prosedur Backup dan Rollback Konfigurasi Router

## Konteks
Gunakan skill ini sebelum melakukan perubahan konfigurasi di router, atau sebagai
backup rutin mingguan. Backup config diperlukan untuk pemulihan cepat jika terjadi
kesalahan konfigurasi.

**PENTING:** Operasi backup dan rollback memerlukan persetujuan operator (approval_required: true)
karena melibatkan akses write ke router dan penyimpanan data konfigurasi.

## Prosedur Backup

### Langkah 1: Verifikasi Router Target
Konfirmasi nama router yang akan di-backup. Pastikan router reachable sebelum mulai.

### Langkah 2: Cek Backup Terakhir
Gunakan `list_backups` untuk melihat apakah sudah ada backup sebelumnya:
- Jika ada backup < 24 jam → tanyakan ke operator apakah tetap perlu backup baru
- Jika ada backup sebelumnya → bisa dibandingkan dengan `diff_config` setelah backup

### Langkah 3: Minta Persetujuan Operator
Sistem akan meminta persetujuan operator. Operator perlu mengkonfirmasi:
- Router yang akan di-backup
- Alasan backup (rutin / sebelum perubahan / pasca insiden)

### Langkah 4: Eksekusi Backup
Setelah disetujui, jalankan `backup_router_config` untuk:
- Export konfigurasi lengkap dari router menggunakan `/export`
- Simpan ke direktori `backups/` dengan timestamp otomatis
- Verifikasi file backup tersimpan dan tidak kosong

### Langkah 5: Verifikasi Backup
Gunakan `list_backups` untuk konfirmasi file backup baru tersimpan.
Jika ada backup sebelumnya, gunakan `diff_config` untuk melihat perubahan sejak backup terakhir.
Setelah backup selesai, LANGSUNG lanjutkan ke tugas berikutnya tanpa menunggu konfirmasi —
sistem approval sudah menangani persetujuan operator per operasi.

## Prosedur Perubahan Konfigurasi yang Aman

Ikuti urutan ini SETIAP KALI melakukan perubahan konfigurasi:

```
1. Backup  →  2. Ubah  →  3. Verifikasi  →  4. Rollback (jika gagal)
```

### Langkah 1: Backup Sebelum Perubahan
Jalankan `backup_router_config` sebelum membuat perubahan apapun.
Catat nama file backup yang dihasilkan — dibutuhkan jika rollback diperlukan.

### Langkah 2: Eksekusi Perubahan
Buat perubahan di router menggunakan `run_command_write`. Setiap perintah write
akan meminta approval operator secara otomatis via sistem — tidak perlu menunggu
konfirmasi manual. Setelah approval dan eksekusi, langsung lanjut ke perubahan berikutnya.

### Langkah 3: Verifikasi Hasil
Segera setelah perubahan:
- Cek reachability router masih OK
- Verifikasi layanan yang diubah berjalan dengan benar
- Cek log singkat: `get_router_log(router_name, lines=10)` — pastikan tidak ada error baru

### Langkah 4: Rollback Jika Bermasalah
Jika perubahan menyebabkan masalah, lakukan rollback segera (lihat bagian Rollback di bawah).

## Prosedur Rollback

Gunakan jika perubahan config menyebabkan masalah dan perlu dikembalikan.

### Langkah 1: Identifikasi Backup yang Akan Dipakai
Gunakan `list_backups(router_name)` untuk melihat daftar backup tersedia.
Pilih backup sebelum perubahan yang bermasalah (berdasarkan timestamp).

### Langkah 2: Tampilkan Diff untuk Konfirmasi
Gunakan `diff_config` untuk menunjukkan perbedaan antara config saat ini dan
backup yang akan di-restore. Presentasikan ke operator untuk konfirmasi.

### Langkah 3: Eksekusi Rollback
**PERHATIAN**: Rollback akan menimpa konfigurasi aktif. Pastikan operator sudah
konfirmasi sebelum melanjutkan.

Gunakan `run_command` dengan perintah import di RouterOS:
```
/import file=<nama-file-backup>
```

### Langkah 4: Verifikasi Pasca Rollback
- Cek reachability router kembali
- Pastikan masalah yang ditimbulkan perubahan sebelumnya sudah hilang
- Jalankan `diff_config` antara config saat ini dan backup — harus kembali sama

## Output yang Diharapkan
Konfirmasi backup yang mencakup:
- Nama file backup yang tersimpan (dengan path dan ukuran)
- Timestamp backup
- Ringkasan diff jika ada backup sebelumnya (berapa baris berubah)
- Status rollback jika dilakukan (berhasil/gagal)

## Catatan
- File backup disimpan di `backups/<router-name>/<timestamp>.rsc` (RouterOS script)
- Backup tidak mengandung password dalam plaintext kecuali menggunakan `export sensitive`
  — yang tidak diizinkan oleh sistem
- Backup rutin: sebelum perubahan config, setiap Senin pagi, setelah update firmware
- Jika router tidak dapat diakses setelah perubahan, rollback harus dilakukan secara
  fisik/out-of-band — informasikan ke operator untuk akses konsol
