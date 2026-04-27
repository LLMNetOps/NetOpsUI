---
name: config-backup-procedure
domain: config
triggers:
  - backup konfigurasi
  - simpan config router
  - backup config
  - export konfigurasi
  - backup sebelum perubahan
  - config backup
  - simpan konfigurasi
tools:
  - list_backups
  - diff_config
approval_required: true
enabled: true
---

# Prosedur Backup Konfigurasi Router

## Konteks
Gunakan skill ini sebelum melakukan perubahan konfigurasi di router, atau sebagai
backup rutin mingguan. Backup config diperlukan untuk pemulihan cepat jika terjadi
kesalahan konfigurasi.

**PENTING:** Operasi backup memerlukan persetujuan operator (approval_required: true)
karena melibatkan akses write ke router dan penyimpanan data konfigurasi.

## Prosedur

### Langkah 1: Verifikasi Router Target
Konfirmasi nama router yang akan di-backup dengan operator. Gunakan `list_routers`
untuk memastikan nama router valid dan router dalam kondisi reachable.

### Langkah 2: Cek Backup Terakhir
Gunakan `list_backups` untuk melihat apakah sudah ada backup sebelumnya:
- Jika ada backup < 24 jam → tanyakan ke operator apakah tetap perlu backup baru
- Jika ada backup sebelumnya → akan bisa dibandingkan dengan `diff_config` setelah backup

### Langkah 3: Minta Persetujuan Operator
Sebelum menjalankan backup, sistem akan meminta persetujuan operator melalui panel
approval di TUI. Operator perlu mengkonfirmasi:
- Router yang akan di-backup
- Alasan backup (rutin / sebelum perubahan / pasca insiden)
- Konfirmasi tidak ada sesi aktif yang akan terganggu

### Langkah 4: Eksekusi Backup
Setelah disetujui, jalankan `backup_router_config` untuk:
- Export konfigurasi lengkap dari router menggunakan `/export`
- Simpan ke direktori `backups/` dengan timestamp otomatis
- Verifikasi file backup tersimpan dan tidak kosong

### Langkah 5: Verifikasi Backup
Gunakan `list_backups` untuk konfirmasi file backup baru tersimpan.
Jika ada backup sebelumnya, gunakan `diff_config` untuk melihat perubahan.

## Output yang Diharapkan
Konfirmasi backup yang mencakup:
- Nama file backup yang tersimpan (dengan path dan ukuran)
- Timestamp backup
- Ringkasan diff jika ada backup sebelumnya (berapa baris berubah)
- Lokasi penyimpanan

## Catatan
- File backup disimpan di `backups/<router-name>/<timestamp>.rsc` (RouterOS script)
- Backup tidak mengandung password dalam plaintext kecuali menggunakan `export sensitive`
  — yang tidak diizinkan oleh sistem
- Backup rutin sebaiknya dilakukan: sebelum perubahan config, setiap Senin pagi,
  dan setelah pembaruan firmware
- File backup di-gitignore — tidak masuk ke version control repository
