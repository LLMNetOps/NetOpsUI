---
name: security-audit
domain: security
triggers:
  - audit keamanan
  - cek user router
  - security audit
  - cek NTP
  - ada user tidak dikenal
  - audit akun router
  - cek konfigurasi keamanan
  - hardening router
tools:
  - audit_security
  - get_router_log
  - run_command
  - run_command_all
approval_required: false
enabled: true
---

# Security Audit Router

## Konteks
Gunakan skill ini untuk memeriksa postur keamanan router jaringan kampus. Mencakup:
cek akun pengguna, status NTP, dan keberadaan konfigurasi default yang tidak aman.
Jalankan secara rutin (mingguan) atau setelah ada insiden keamanan.

## Prosedur

### Langkah 1: Audit Menyeluruh
Jalankan `audit_security` tanpa argumen (default: semua router). Fungsi ini memeriksa:
- Daftar user yang ada di tiap router
- Status sinkronisasi NTP
- Keberadaan akun `admin` default (risiko keamanan)

### Langkah 2: Analisis Temuan User
Dari hasil audit, perhatikan:
- Router yang masih memiliki akun `admin` default → wajib diganti namanya atau dihapus
- Jumlah user yang tidak wajar (> 3) → verifikasi apakah semua user dikenal dan sah
- Untuk router tertentu, gunakan `run_command` dengan `/user/print` untuk melihat detail
  level akses (full, read, write, policy) dan alamat IP yang diizinkan

### Langkah 3: Analisis NTP
Router yang tidak sinkron NTP berisiko:
- Log timestamp tidak akurat → menyulitkan forensik
- Sertifikat SSL/TLS bisa ditolak jika waktu terlalu jauh berbeda
- Autentikasi berbasis waktu (Kerberos, dll) bisa gagal

Untuk router dengan NTP tidak sinkron, gunakan `run_command` dengan
`/system/ntp/client/print` untuk melihat server NTP yang dikonfigurasi dan statusnya.

### Langkah 4: Cek Log Login
Ambil log dengan `get_router_log` menggunakan filter topic `system`. Cari:
- `logged in` dari IP yang tidak dikenal → kemungkinan akses tidak sah
- `login failure` berulang → kemungkinan brute force
- `user added` atau `user removed` → perubahan akun yang mungkin tidak sah

### Langkah 5: Cek Firewall
Jika ada kekhawatiran tentang akses manajemen, gunakan `run_command` atau `run_command_all`
dengan `/ip/firewall/filter/print where chain=input` untuk melihat aturan yang mengontrol
akses ke router.

## Output yang Diharapkan
Laporan audit yang mencakup:
- Status setiap router: NTP synced/not, jumlah user, ada/tidak default admin
- Daftar temuan dengan tingkat risiko (⚠ medium, ✗ high)
- Rekomendasi tindakan spesifik per router

Format temuan:
```
[ROUTER-NAME]
  ⚠ Akun 'admin' default masih ada — ganti nama atau hapus
  ✗ NTP tidak sinkron (server: 0.id.pool.ntp.org) — cek koneksi ke NTP server
  ⚠ 4 user aktif — verifikasi: admin, netops, monitoring, backup-user
```

## Catatan
- Perubahan konfigurasi (rename user, set NTP server) memerlukan akses write —
  sampaikan rekomendasi ke operator untuk dikerjakan secara manual atau via skill config
- Audit security sebaiknya dilakukan dari jaringan manajemen yang terisolasi
- Simpan hasil audit ke laporan untuk perbandingan historis
